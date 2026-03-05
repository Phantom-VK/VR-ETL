from __future__ import annotations

import json
import sys
import asyncio
from typing import List, Optional

from fastapi import HTTPException

from src.backend.graph.app import build_chat_graph
from src.backend.graph.tools import MATH_TOOL, run_math_tool
from src.backend.llm import call_llm_stream, call_llm_tools
from src.config import settings
from src.utils.exception import VRETLException
from src.utils.logger import logger

# Compile LangGraph once at module load
_CHAT_GRAPH = build_chat_graph()


def handle_pageindex_combined_stream(
    query: str,
    doc_id: str | None = None,
    search_temperature: float | None = None,
    answer_temperature: float | None = None,
    enable_citations: bool = False,
    answer_model: str | None = None,
):
    """
    Use PageIndex to pick nodes, then stream reasoning + answer.
    use_math boolean is extracted from the graph node inside this function, it is not an input to this function.
    Branch A (use_math=True):
        1. Call LLM with math tool to extract the expression.
        2. Execute the expression via run_math_tool() (Python evaluator — exact result).
        3. Inject the verified numeric result into the final prompt.
        4. Stream the final answer that cites the pre-computed result.

    Branch B (use_math=False):
        1. Skip tool phase entirely.
        2. Stream a pure reasoning answer directly from context.
    """
    try:
        # LangGraph retrieval
        graph_input = {
            "query": query,
            "doc_id": doc_id,
            "search_temperature": search_temperature,
            "answer_temperature": answer_temperature,
            "enable_citations": enable_citations,
        }
        logger.info(
            "handle_pageindex_combined_stream | query='%s' doc_id=%s "
            "temps(search=%.2f answer=%.2f) citations=%s",
            query,
            doc_id,
            search_temperature if search_temperature is not None else -1,
            answer_temperature if answer_temperature is not None else -1,
            enable_citations,
        )

        graph_state = _CHAT_GRAPH.invoke(graph_input)
        thinking    = graph_state.get("thinking", "")
        node_list   = graph_state.get("node_list", []) or []
        nodes       = graph_state.get("nodes",     []) or []
        context     = graph_state.get("context",   "") or ""
        citations   = graph_state.get("citations", []) or []


        use_math = bool(graph_state.get("require_math", False))

        logger.info(
            "Graph done | node_count=%d context_chars=%d use_math=%s",
            len(nodes), len(context), use_math,
        )

        # Base prompt (shared by both branches)
        base_prompt = (
            "Answer the question based only on the context provided below.\n\n"
            f"Question: {query}\n\n"
            f"Context:\n{context}\n\n"
            "Rules:\n"
            "- Be clear and concise.\n"
            "- Cite page numbers as <page=PAGE_NUMBER> wherever you use evidence.\n"
            "- Do NOT invent information outside the context.\n"
            "- If answers contains numerical outputs, convert them to proper units."
        )

        # math tool path
        tool_result: Optional[str] = None
        tool_args:   Optional[dict] = None

        if use_math:
            # Ask the LLM to identify the math expression that needs computing.
            # We use a lightweight non-streaming call with the tool schema.
            logger.info("Math branch: calling LLM with evaluate_math tool")
            try:
                tool_call = call_llm_tools(
                    prompt=base_prompt,
                    tools=MATH_TOOL,
                    model=settings.chat_model or settings.reasoning_model,
                    temperature=0.1,   # low temp — we want deterministic tool extraction
                )

                if (
                    tool_call.get("tool_name") == "evaluate_math"
                    and tool_call.get("arguments")
                ):
                    try:
                        tool_args = json.loads(tool_call["arguments"])
                    except json.JSONDecodeError as e:
                        logger.warning("Math tool returned invalid JSON args: %s", e)
                        tool_args = None
                        tool_result = None
                    if tool_args:
                        expression = tool_args.get("expression")
                        precision  = tool_args.get("precision", 4)

                        if expression:
                            tool_result = run_math_tool(expression, precision)
                            logger.info(
                                "Math tool OK | expr='%s' -> result='%s'",
                                expression, tool_result,
                            )
                        else:
                            logger.warning("Math tool called but expression was empty; skipping.")
                else:
                    logger.info("LLM did not invoke the math tool (expression not required).")

            except Exception as tool_exc:  # noqa: BLE001
                logger.error(
                    "Math tool step failed; continuing without it. err=%s", tool_exc, exc_info=True
                )

        # Build final prompt based on branch outcome
        if use_math and tool_result and tool_args:
            # Branch A — inject verified result. Instruct LLM to trust it.
            final_prompt = (
                f"{base_prompt}\n"
                "IMPORTANT — A Python math tool already computed the following for you.\n"
                "You MUST use this result directly. Do NOT recalculate.\n\n"
                f"  Expression : {tool_args.get('expression')}\n"
                f"  Result     : {tool_result}\n\n"
                "Integrate this numeric result naturally into your final answer "
                "and cite the relevant page numbers."
            )
            logger.info("Branch A: final prompt includes math tool result")

        elif use_math and not tool_result:
            # Branch A fallback — math was requested but tool produced nothing.
            # Ask LLM to reason carefully on its own (best-effort).
            final_prompt = (
                f"{base_prompt}\n"
                "Note: A math tool was attempted but could not compute a result. "
                "Please calculate as accurately as possible using the context, "
                "and double-check your arithmetic before answering."
            )
            logger.info("Branch A fallback: math tool produced no result; LLM will self-compute")

        else:
            # Branch B — pure reasoning, no math tool.
            final_prompt = base_prompt
            logger.info("Branch B: pure reasoning path, no math tool")

        # Stream the final answer
        model_to_use = answer_model or settings.reasoning_model or settings.chat_model
        if not model_to_use:
            raise HTTPException(status_code=500, detail="No LLM model configured. Set reasoning_model or chat_model.")
        ans_temp     = answer_temperature if answer_temperature is not None else 0.2

        async def async_stream():
            logger.info("Streaming answer | model=%s temp=%.2f", model_to_use, ans_temp)

            # node list and context preview for the frontend
            yield json.dumps({
                "type": "meta",
                "thinking":       thinking,
                "node_list":      node_list,
                "nodes":          nodes,
                "context_preview": context[:1000] + ("..." if len(context) > 1000 else ""),
                "citations":      citations,
            }) + "\n"

            # only emitted when math tool actually ran
            if use_math and tool_result and tool_args:
                yield json.dumps({
                    "type":   "tool",
                    "name":   "evaluate_math",
                    "args":   tool_args,
                    "result": tool_result,
                }) + "\n"

            # LLM answer stream (reason + answer chunks from call_llm_stream)
            loop = asyncio.get_event_loop()
            queue: asyncio.Queue = asyncio.Queue()

            def producer():
                try:
                    for evt in call_llm_stream(final_prompt, model=model_to_use, temperature=ans_temp):
                        loop.call_soon_threadsafe(queue.put_nowait, evt)
                finally:
                    loop.call_soon_threadsafe(queue.put_nowait, None)

            loop.run_in_executor(None, producer)
            while True:
                evt = await queue.get()
                if evt is None:
                    break
                yield json.dumps(evt) + "\n"

            yield json.dumps({"type": "done"}) + "\n"

        return async_stream()

    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("Combined PageIndex+DeepSeek stream failed")
        vr_exc = VRETLException(str(e), sys)
        raise HTTPException(status_code=500, detail=str(vr_exc))


__all__ = ["handle_pageindex_combined_stream"]

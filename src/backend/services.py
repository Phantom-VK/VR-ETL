from __future__ import annotations

import json
import sys
import asyncio
from typing import List, Optional

from fastapi import HTTPException

from src.backend.graph.app import build_chat_graph
from src.backend.graph.tools import MATH_TOOL, run_math_tool
from src.backend.llm import call_llm_stream_messages, call_llm_tools
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
            "enable_citations": True,
        }
        logger.info(
            "handle_pageindex_combined_stream | query='%s' doc_id=%s "
            "temps(search=%.2f answer=%.2f) citations=%s",
            query,
            doc_id,
            search_temperature if search_temperature is not None else -1,
            answer_temperature if answer_temperature is not None else -1,
            True,
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

        SYSTEM_PROMPT = (
            "You are a precise document Q&A assistant. "
            "Use ONLY the provided context. "
            "Cite page numbers as <page=PAGE_NUMBER> for every claim. "
            "Never invent facts. "
            "If a math tool result is provided, trust it and do not recalculate."
        )

        user_prompt = (
            "Context:\n"
            f"{context}\n\n"
            f"Question: {query}\n\n"
            "Rules:\n"
            "- Be clear and concise.\n"
            "- Cite page numbers as <page=PAGE_NUMBER> wherever you use evidence.\n"
            "- Do NOT invent information outside the context.\n"
            "- Convert numerical outputs to proper units."
        )

        base_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        # math tool path
        tool_result: Optional[str] = None
        tool_args:   Optional[dict] = None
        tool_call_message = None
        tool_result_message = None

        if use_math:
            # Ask the LLM to identify the math expression that needs computing.
            # We use a lightweight non-streaming call with the tool schema.
            logger.info("Math branch: calling LLM with evaluate_math tool")
            try:
                assistant_msg = call_llm_tools(
                    messages=base_messages,
                    tools=MATH_TOOL,
                    model=settings.chat_model or settings.reasoning_model,
                    temperature=0.1,
                    tool_choice="required",
                )
                assistant_msg_dict = assistant_msg.model_dump(exclude_none=True)
                tool_calls = assistant_msg.tool_calls or []
                if tool_calls:
                    tc = tool_calls[0]
                    try:
                        tool_args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError as e:
                        logger.warning("Math tool returned invalid JSON args: %s", e)
                        tool_args = None
                    if tool_args:
                        expression = tool_args.get("expression")
                        precision = tool_args.get("precision", 4)
                        if expression:
                            tool_result = run_math_tool(expression, precision)
                            logger.info("Math tool OK | expr='%s' -> result='%s'", expression, tool_result)
                        else:
                            logger.warning("Math tool called but expression was empty; skipping.")
                    tool_call_message = assistant_msg_dict
                    if tool_result is not None:
                        tool_result_message = {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": tool_result,
                        }
                else:
                    logger.info("LLM did not invoke the math tool (expression not required).")

            except Exception as tool_exc:  # noqa: BLE001
                logger.error(
                    "Math tool step failed; continuing without it. err=%s", tool_exc, exc_info=True
                )

        # Build final prompt based on branch outcome
        model_to_use = answer_model or settings.reasoning_model or settings.chat_model
        if not model_to_use:
            raise HTTPException(status_code=500, detail="No LLM model configured. Set reasoning_model or chat_model.")
        ans_temp     = answer_temperature if answer_temperature is not None else 0.2

        # Construct final messages for streaming
        final_messages = list(base_messages)
        if use_math and tool_result is not None and tool_args and tool_call_message and tool_result_message:
            final_messages.append(tool_call_message)
            final_messages.append(tool_result_message)
        elif use_math and tool_result is None:
            # math flagged but failed; add a helper user note
            final_messages.append(
                {
                    "role": "user",
                    "content": "A math tool was attempted but failed. Please compute carefully from context and double-check arithmetic.",
                }
            )

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
                    for evt in call_llm_stream_messages(final_messages, model=model_to_use, temperature=ans_temp):
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

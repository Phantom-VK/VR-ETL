from __future__ import annotations

import json
import sys
from typing import List

from fastapi import HTTPException

from src.backend.graph.app import build_chat_graph
from src.backend.llm import call_llm_stream
from src.config import settings
from src.utils.exception import VRETLException
from src.utils.logger import logger

# Compile LangGraph once
_CHAT_GRAPH = build_chat_graph()


def handle_pageindex_combined_stream(
    query: str,
    doc_id: str | None = None,
    search_temperature: float | None = None,
    answer_temperature: float | None = None,
    enable_citations: bool = False,
    answer_model: str | None = None,
):
    """Use PageIndex to pick nodes, then stream reasoning+answer from the reasoning model."""
    try:
        # 1) Run LangGraph retrieval
        graph_input = {
            "query": query,
            "doc_id": doc_id,
            "search_temperature": search_temperature,
            "answer_temperature": answer_temperature,
            "enable_citations": enable_citations,
        }
        logger.info(
            "Service handle_pageindex_combined_stream query='%s' doc_id=%s temps(search=%.2f, answer=%.2f) citations=%s",
            query,
            doc_id,
            search_temperature if search_temperature is not None else -1,
            answer_temperature if answer_temperature is not None else -1,
            enable_citations,
        )
        graph_state = _CHAT_GRAPH.invoke(graph_input)
        thinking = graph_state.get("thinking", "")
        node_list: List[str] = graph_state.get("node_list", []) or []
        nodes = graph_state.get("nodes", []) or []
        context = graph_state.get("context", "") or ""
        logger.info("Graph done node_count=%d context_chars=%d", len(nodes), len(context))

        # 3) Stream reasoning+answer from reasoning model
        answer_prompt = f"""
Answer the question based on the context:

Question: {query}
Context: {context}

Provide a clear, concise answer based only on the context provided.
Do the mathematical calculations accurately, recheck the answers.
Always mention page numbers as <page=PAGE_NUMBER> when citing evidence.
"""
        model_to_use = answer_model or settings.reasoning_model or settings.chat_model
        ans_temp = answer_temperature if answer_temperature is not None else 0.2

        def answer_stream():
            for evt in call_llm_stream(answer_prompt, model=model_to_use, temperature=ans_temp):
                yield evt

        async def async_stream():
            logger.info("Streaming answer model=%s temp=%.2f", model_to_use, ans_temp)
            yield json.dumps(
                {
                    "type": "meta",
                    "thinking": thinking,
                    "node_list": node_list,
                    "nodes": nodes,
                    "context_preview": context[:1000] + ("..." if len(context) > 1000 else ""),
                }
            ) + "\n"
            for evt in answer_stream():
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

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from fastapi import HTTPException

from src.backend.retrieval import search_tree_with_llm, create_node_mapping
from src.backend.answer import answer_question, build_context
from src.backend.llm import call_llm_stream
from src.backend.models import SearchNode, SearchResponse, AnswerResponse
from src.config import settings
from src.utils.logger import logger

DEFAULT_TREE_PATH = Path("data/processed/pageindex_tree.json")
DEFAULT_NODE_MAP_PATH = Path("data/processed/node_map.json")
_TREE_CACHE: Dict[Path, Tuple[float, Any]] = {}
_NODE_MAP_CACHE: Dict[Path, Tuple[float, Dict[str, Any]]] = {}


def _load_tree(tree_path: Path) -> Any:
    mtime = tree_path.stat().st_mtime if tree_path.exists() else None
    if not mtime:
        raise FileNotFoundError(f"Tree file not found at {tree_path}; run the ETL first.")
    cached = _TREE_CACHE.get(tree_path)
    if cached and cached[0] == mtime:
        return cached[1]
    with tree_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    tree = data.get("result", data)
    _TREE_CACHE[tree_path] = (mtime, tree)
    return tree

def _load_node_map(node_map_path: Path) -> Dict[str, Any] | None:
    if not node_map_path.exists():
        return None
    mtime = node_map_path.stat().st_mtime
    cached = _NODE_MAP_CACHE.get(node_map_path)
    if cached and cached[0] == mtime:
        return cached[1]
    try:
        with node_map_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        _NODE_MAP_CACHE[node_map_path] = (mtime, data)
        return data
    except Exception:
        logger.warning("Failed to load node_map from %s; falling back to rebuild", node_map_path)
        return None


async def _stream_reasoning_and_answer(prompt: str, model: str | None, temperature: float):
    """Split streamed tokens into reasoning (<think>...</think>) and answer tokens."""
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue[str | None] = asyncio.Queue()

    def worker():
        try:
            for chunk in call_llm_stream(prompt, model=model, temperature=temperature):
                asyncio.run_coroutine_threadsafe(queue.put(chunk), loop)
        finally:
            asyncio.run_coroutine_threadsafe(queue.put(None), loop)

    import threading

    threading.Thread(target=worker, daemon=True).start()

    buffer = ""
    in_think = False

    while True:
        token = await queue.get()
        if token is None:
            break
        buffer += token

        while True:
            if in_think:
                end = buffer.find("</think>")
                if end != -1:
                    reason_chunk = buffer[:end]
                    if reason_chunk:
                        yield {"type": "reason", "text": reason_chunk}
                    buffer = buffer[end + len("</think>"):]
                    in_think = False
                else:
                    if buffer:
                        yield {"type": "reason", "text": buffer}
                        buffer = ""
                    break
            else:
                start = buffer.find("<think>")
                if start != -1:
                    # emit any answer text before think
                    if start > 0:
                        ans_chunk = buffer[:start]
                        if ans_chunk:
                            yield {"type": "answer", "text": ans_chunk}
                    buffer = buffer[start + len("<think>"):]
                    in_think = True
                else:
                    if buffer:
                        yield {"type": "answer", "text": buffer}
                        buffer = ""
                    break



def handle_search(
    query: str,
    tree_path: Path | None,
    model: str | None,
    temperature: float | None,
    search_model: str | None = None,
    search_temperature: float | None = None,
) -> SearchResponse:
    path = tree_path or DEFAULT_TREE_PATH
    logger.info("Service search query=%s tree=%s", query, path)
    try:
        tree = _load_tree(path)
        # search always uses reasoning_model; optional override
        effective_model = search_model or settings.reasoning_model
        eff_temp = (
            search_temperature
            if search_temperature is not None
            else (temperature if temperature is not None else settings.reasoning_temperature)
        )
        logger.info("Search using model=%s temp=%.2f", effective_model, eff_temp)
        result = search_tree_with_llm(query, tree, model=effective_model, temperature=eff_temp)
        node_map = _load_node_map(DEFAULT_NODE_MAP_PATH) or create_node_mapping(tree)
        nodes: List[SearchNode] = [
            SearchNode(
                node_id=nid,
                title=node_map.get(nid, {}).get("title"),
                page_index=node_map.get(nid, {}).get("page_index"),
            )
            for nid in result.node_list
            if nid in node_map
        ]
        unknown = [nid for nid in result.node_list if nid not in node_map]
        if unknown:
            logger.warning("Unknown node_ids returned by LLM (skipped): %s", unknown)
        return SearchResponse(thinking=result.thinking, node_list=result.node_list, nodes=nodes)
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("Search failed")
        raise HTTPException(status_code=500, detail=str(e))


def handle_answer(
    query: str,
    tree_path: Path | None,
    model: str | None,
    temperature: float | None,
    search_model: str | None = None,
    answer_model: str | None = None,
    search_temperature: float | None = None,
    answer_temperature: float | None = None,
) -> AnswerResponse:
    path = tree_path or DEFAULT_TREE_PATH
    logger.info("Service answer query=%s tree=%s", query, path)
    try:
        tree = _load_tree(path)
        node_map = _load_node_map(DEFAULT_NODE_MAP_PATH) or create_node_mapping(tree)
        effective_search_model = search_model or settings.reasoning_model
        effective_answer_model = answer_model or settings.chat_model
        search_temp = (
            search_temperature
            if search_temperature is not None
            else (temperature if temperature is not None else settings.reasoning_temperature)
        )
        answer_temp = (
            answer_temperature
            if answer_temperature is not None
            else (temperature if temperature is not None else settings.chat_temperature)
        )
        logger.info("Answer search model=%s temp=%.2f; answer model=%s temp=%.2f", effective_search_model, search_temp, effective_answer_model, answer_temp)
        search_result, context, answer_text = answer_question(query, tree, model=effective_search_model, temperature=search_temp)
        nodes: List[SearchNode] = [
            SearchNode(
                node_id=nid,
                title=node_map.get(nid, {}).get("title"),
                page_index=node_map.get(nid, {}).get("page_index"),
            )
            for nid in search_result.node_list
            if nid in node_map
        ]
        unknown = [nid for nid in search_result.node_list if nid not in node_map]
        if unknown:
            logger.warning("Unknown node_ids returned by LLM (skipped): %s", unknown)
        preview = context[:1000] + ("..." if len(context) > 1000 else "")
        return AnswerResponse(
            thinking=search_result.thinking,
            node_list=search_result.node_list,
            nodes=nodes,
            context_preview=preview,
            answer=answer_text,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("Answer failed")
        raise HTTPException(status_code=500, detail=str(e))


def handle_answer_stream(
    query: str,
    tree_path: Path | None,
    model: str | None,
    temperature: float | None,
    search_model: str | None = None,
    answer_model: str | None = None,
    search_temperature: float | None = None,
    answer_temperature: float | None = None,
):
    path = tree_path or DEFAULT_TREE_PATH
    logger.info("Service answer_stream query=%s tree=%s", query, path)
    try:
        tree = _load_tree(path)
        node_map = _load_node_map(DEFAULT_NODE_MAP_PATH) or create_node_mapping(tree)
        effective_search_model = search_model or settings.reasoning_model
        effective_answer_model = answer_model or settings.chat_model
        search_temp = (
            search_temperature
            if search_temperature is not None
            else (temperature if temperature is not None else settings.reasoning_temperature)
        )
        answer_temp = (
            answer_temperature
            if answer_temperature is not None
            else (temperature if temperature is not None else settings.chat_temperature)
        )
        logger.info("Stream search model=%s temp=%.2f; answer model=%s temp=%.2f", effective_search_model, search_temp, effective_answer_model, answer_temp)
        search_result = search_tree_with_llm(query, tree, model=effective_search_model, temperature=search_temp)
        nodes: List[SearchNode] = [
            SearchNode(
                node_id=nid,
                title=node_map.get(nid, {}).get("title"),
                page_index=node_map.get(nid, {}).get("page_index"),
            )
            for nid in search_result.node_list
            if nid in node_map
        ]
        unknown = [nid for nid in search_result.node_list if nid not in node_map]
        if unknown:
            logger.warning("Unknown node_ids returned by LLM (skipped): %s", unknown)
        context = build_context(search_result.node_list, node_map)
        prompt = f"""
Answer the question based on the context:

Question: {query}
Context: {context}

Provide a clear, concise answer based only on the context provided.
"""

        meta = {
            "type": "meta",
            "thinking": search_result.thinking,
            "node_list": search_result.node_list,
            "nodes": [n.model_dump() for n in nodes],
            "context_preview": context[:1000] + ("..." if len(context) > 1000 else ""),
        }

        async def async_stream():
            yield json.dumps(meta) + "\n"
            async for evt in _stream_reasoning_and_answer(prompt, effective_answer_model, answer_temp):
                yield json.dumps(evt) + "\n"
            yield json.dumps({"type": "done"}) + "\n"

        return async_stream()
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("Answer stream failed")
        raise HTTPException(status_code=500, detail=str(e))


__all__ = ["handle_search", "handle_answer", "handle_answer_stream", "DEFAULT_TREE_PATH"]

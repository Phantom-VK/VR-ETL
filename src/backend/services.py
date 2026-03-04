from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List

from fastapi import HTTPException

from src.backend.retrieval import search_tree_with_llm, create_node_mapping
from src.backend.answer import answer_question, build_context
from src.backend.llm import call_llm_stream
from src.backend.models import SearchNode, SearchResponse, AnswerResponse
from src.utils.logger import logger

DEFAULT_TREE_PATH = Path("data/processed/pageindex_tree.json")
DEFAULT_NODE_MAP_PATH = Path("data/processed/node_map.json")


def _load_tree(tree_path: Path) -> Any:
    if not tree_path.exists():
        raise FileNotFoundError(f"Tree file not found at {tree_path}; run the ETL first.")
    with tree_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("result", data)

def _load_node_map(node_map_path: Path) -> Dict[str, Any] | None:
    if not node_map_path.exists():
        return None
    try:
        with node_map_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logger.warning("Failed to load node_map from %s; falling back to rebuild", node_map_path)
        return None


def handle_search(query: str, tree_path: Path | None, model: str | None, temperature: float) -> SearchResponse:
    path = tree_path or DEFAULT_TREE_PATH
    logger.info("Service search query=%s tree=%s", query, path)
    try:
        tree = _load_tree(path)
        result = search_tree_with_llm(query, tree, model=model, temperature=temperature)
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


def handle_answer(query: str, tree_path: Path | None, model: str | None, temperature: float) -> AnswerResponse:
    path = tree_path or DEFAULT_TREE_PATH
    logger.info("Service answer query=%s tree=%s", query, path)
    try:
        tree = _load_tree(path)
        node_map = _load_node_map(DEFAULT_NODE_MAP_PATH) or create_node_mapping(tree)
        search_result, context, answer_text = answer_question(query, tree, model=model, temperature=temperature)
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


def handle_answer_stream(query: str, tree_path: Path | None, model: str | None, temperature: float):
    path = tree_path or DEFAULT_TREE_PATH
    logger.info("Service answer_stream query=%s tree=%s", query, path)
    try:
        tree = _load_tree(path)
        node_map = _load_node_map(DEFAULT_NODE_MAP_PATH) or create_node_mapping(tree)
        search_result = search_tree_with_llm(query, tree, model=model, temperature=temperature)
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

        def generator():
            yield json.dumps(meta) + "\n"
            for chunk in call_llm_stream(prompt, model=model, temperature=temperature):
                yield json.dumps({"type": "token", "text": chunk}) + "\n"
            yield json.dumps({"type": "done"}) + "\n"

        return generator()
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("Answer stream failed")
        raise HTTPException(status_code=500, detail=str(e))


__all__ = ["handle_search", "handle_answer", "handle_answer_stream", "DEFAULT_TREE_PATH"]

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List

from fastapi import HTTPException

from src.backend.retrieval import search_tree_with_llm, create_node_mapping
from src.backend.answer import answer_question
from src.backend.models import SearchNode, SearchResponse, AnswerResponse
from src.utils.logger import logger

DEFAULT_TREE_PATH = Path("data/processed/pageindex_tree.json")


def _load_tree(tree_path: Path) -> Any:
    if not tree_path.exists():
        raise FileNotFoundError(f"Tree file not found at {tree_path}; run the ETL first.")
    with tree_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("result", data)


def handle_search(query: str, tree_path: Path | None, model: str | None, temperature: float) -> SearchResponse:
    path = tree_path or DEFAULT_TREE_PATH
    logger.info("Service search query=%s tree=%s", query, path)
    try:
        tree = _load_tree(path)
        result = search_tree_with_llm(query, tree, model=model, temperature=temperature)
        node_map = create_node_mapping(tree)
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
        search_result, context, answer_text = answer_question(query, tree, model=model, temperature=temperature)
        node_map = create_node_mapping(tree)
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


__all__ = ["handle_search", "handle_answer", "DEFAULT_TREE_PATH"]

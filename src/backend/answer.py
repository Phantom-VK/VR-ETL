"""Answer generation pipeline: search tree, build context, and call LLM."""
from __future__ import annotations

import sys
from typing import Any, Dict, Iterable, List, Tuple

from src.backend.llm import call_llm
from src.backend.retrieval import search_tree_with_llm, create_node_mapping, TreeSearchResult
from src.utils.logger import logger
from src.utils.exception import VRETLException


def build_context(node_ids: Iterable[str], node_map: Dict[str, Dict[str, Any]]) -> str:
    """Concatenate text fields from node_map for the given node_ids.

    Skips nodes without text or missing IDs. Preserves order of node_ids.
    """
    parts: List[str] = []
    for node_id in node_ids:
        node = node_map.get(node_id)
        if not node:
            logger.warning("Node id %s not found in node_map; skipping", node_id)
            continue
        text = node.get("text")
        if not text:
            logger.warning("Node id %s has no text; skipping", node_id)
            continue
        parts.append(text)
    return "\n\n".join(parts)


def answer_question(query: str, tree: Any, model: str | None = None, temperature: float = 0.0) -> Tuple[TreeSearchResult, str, str]:
    """Run tree search, build context, and generate an answer.

    Returns: (tree_search_result, context, answer_text)
    """
    try:
        logger.info("Answer pipeline started for query: %s", query)
        tree_result = search_tree_with_llm(query, tree, model=model, temperature=temperature)
        node_map = create_node_mapping(tree)
        logger.info("Building context from %d nodes", len(tree_result.node_list))
        context = build_context(tree_result.node_list, node_map)
        prompt = f"""
Answer the question based on the context:

Question: {query}
Context: {context}

Provide a clear, concise answer based only on the context provided.
"""
        answer = call_llm(prompt, model=model, temperature=temperature)
        logger.info("Answer generation complete; answer_chars=%d", len(answer))
        return tree_result, context, answer
    except Exception as exc:  # noqa: BLE001
        raise VRETLException(str(exc), sys) from exc


__all__ = ["build_context", "answer_question"]

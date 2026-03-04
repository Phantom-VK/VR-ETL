"""Reasoning-based retrieval utilities using PageIndex tree + LLM."""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any, Dict, List

from src.backend.llm import call_llm
from src.utils.logger import logger
from src.utils.exception import VRETLException


@dataclass
class TreeSearchResult:
    thinking: str
    node_list: List[str]


def strip_text(tree: Any) -> Any:
    """Remove 'text' fields recursively to keep prompts compact."""
    if isinstance(tree, dict):
        return {k: strip_text(v) for k, v in tree.items() if k != "text"}
    if isinstance(tree, list):
        return [strip_text(item) for item in tree]
    return tree


def create_node_mapping(tree: Any) -> Dict[str, Dict[str, Any]]:
    """Flatten tree into node_id -> node dict for quick lookup."""
    mapping: Dict[str, Dict[str, Any]] = {}

    def _walk(node: Dict[str, Any]):
        node_id = node.get("node_id")
        if node_id:
            mapping[node_id] = node
        for child in node.get("children", []):
            _walk(child)

    roots = tree if isinstance(tree, list) else [tree]
    for root in roots:
        _walk(root)
    return mapping


def search_tree_with_llm(query: str, tree: Any, model: str = "deepseek-reasoner", temperature: float = 0.0) -> TreeSearchResult:
    """Use the LLM to select relevant nodes from the PageIndex tree."""
    try:
        compact_tree = strip_text(tree)
        prompt = f"""
You are given a question and a tree structure of a document.
Each node contains a node id, node title, and a corresponding summary.
Your task is to find all nodes that are likely to contain the answer to the question.

Question: {query}

Document tree structure:
{json.dumps(compact_tree, indent=2)}

Please reply in the following JSON format:
{{
    "thinking": "<Your thinking process on which nodes are relevant to the question>",
    "node_list": ["node_id_1", "node_id_2", ..., "node_id_n"]
}}
Directly return the final JSON structure. Do not output anything else.
"""
        logger.info("Running LLM tree search for query: %s", query)
        response_text = call_llm(prompt, model=model, temperature=temperature)
        result_json = json.loads(response_text)
        thinking = result_json.get("thinking", "")
        node_list = result_json.get("node_list", [])
        return TreeSearchResult(thinking=thinking, node_list=node_list)
    except Exception as exc:  # noqa: BLE001
        raise VRETLException(str(exc), sys) from exc


def format_search_result(result: TreeSearchResult, node_map: Dict[str, Dict[str, Any]]) -> str:
    """Produce a human-readable string of the reasoning and selected nodes."""
    lines = ["Reasoning Process:", result.thinking, "", "Retrieved Nodes:"]
    for node_id in result.node_list:
        node = node_map.get(node_id, {})
        lines.append(
            f"Node ID: {node_id}\t Page: {node.get('page_index')}\t Title: {node.get('title')}"
        )
    return "\n".join(lines)


__all__ = [
    "TreeSearchResult",
    "search_tree_with_llm",
    "create_node_mapping",
    "format_search_result",
]

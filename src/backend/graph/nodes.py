from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from src.backend.graph.state import ChatState
from src.backend.pageindex_chat import load_doc_id, pageindex_chat_stream
from src.utils.logger import logger
from src.utils.exception import VRETLException

DEFAULT_NODE_MAP_PATH = Path("data/processed/node_map.json")
_NODE_MAP_CACHE: Dict[Path, Dict[str, Any]] = {}


def _load_node_map(node_map_path: Path = DEFAULT_NODE_MAP_PATH) -> Dict[str, Any] | None:
    """Load the node_map JSON with simple mtime caching."""
    if not node_map_path.exists():
        return None
    cached = _NODE_MAP_CACHE.get(node_map_path)
    mtime = node_map_path.stat().st_mtime
    if cached and cached.get("_mtime") == mtime:
        return cached["data"]
    with node_map_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    _NODE_MAP_CACHE[node_map_path] = {"_mtime": mtime, "data": data}
    return data


def _parse_pageindex_search_output(text: str) -> tuple[str, List[str], bool, List[str]]:
    """Extract thinking/node_list/require_math/citations JSON from PageIndex streamed text."""
    thinking = ""
    node_list: List[str] = []
    require_math = False
    citations: List[str] = []
    try:
        lines = [ln for ln in text.splitlines() if not ln.strip().startswith("```")]
        if lines and lines[0].startswith('{"doc_name"'):
            lines = lines[1:]
        cleaned = "\n".join(lines)
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            parsed = json.loads(cleaned[start : end + 1])
            thinking = parsed.get("thinking", "") or ""
            node_list = parsed.get("node_list", []) or []
            require_math = bool(parsed.get("require_math", False))
            citations = parsed.get("citations", []) or []
    except Exception as e:
        logger.warning(
            "Failed to parse PageIndex output. Raw(first 300)=%s err=%s",
            text[:300],
            e,
        )
        thinking = ""
        node_list = []
    return thinking, node_list, require_math, citations


def retrieve_node(state: ChatState) -> ChatState:
    """Use PageIndex to select nodes and assemble context from node_map."""
    try:
        query = state.get("query", "")
        search_temp = state.get("search_temperature") or 0.1
        enable_citations = state.get("enable_citations", False)
        resolved_doc_id = load_doc_id(state.get("doc_id"))
        node_map = _load_node_map() or {}

        logger.info(
            "retrieve_node: doc_id=%s search_temp=%.2f citations=%s",
            resolved_doc_id,
            search_temp if search_temp is not None else -1,
            enable_citations,
        )

        search_prompt = f"""
            You are given a question and have a tree structure of a document.
            Each node contains a node id, node title, and a corresponding summary.
            Your task is to find all nodes that are likely to contain the answer to the question.
            By analyzing the question and nodes, decide if math calculations are required for this query or not.
            Update the require_math boolean accordingly.
            
            Question: {query}
            
            Please reply in the following JSON format:
            {{
                "node_list": ["node_id_1", "node_id_2", ..., "node_id_n"],
                "require_math": <true|false>,
                "citations": ["<doc=file.pdf;page=1>", "..."]
            }}
            Only return node_id values that appear in the tree. Do not invent node_ids.
            If citations are available, include them; otherwise return an empty list.
            Directly return the final JSON structure. Do not output anything else.
        """

        search_chunks: List[str] = []
        for chunk in pageindex_chat_stream(
            messages=[{"role": "user", "content": search_prompt}],
            doc_id=resolved_doc_id,
            temperature=search_temp if search_temp is not None else 0.1,
        ):
            if isinstance(chunk, dict):
                delta = (chunk.get("choices") or [{}])[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    search_chunks.append(content)
            elif isinstance(chunk, str):
                search_chunks.append(chunk)

        full_search = "".join(search_chunks)
        logger.info("retrieve_node: raw_pageindex_output=%s", full_search[:800])
        thinking, node_list, require_math, citations = _parse_pageindex_search_output(full_search)
        logger.info(
            "retrieve_node: parsed nodes=%s thinking_len=%d require_math=%s citations=%d",
            node_list,
            len(thinking),
            require_math,
            len(citations),
        )

        nodes = []
        context_parts: List[str] = []
        for nid in node_list:
            node = node_map.get(nid, {})
            if not node:
                logger.warning("Node id %s not found in node_map; skipping", nid)
                continue
            page = node.get("page_index")
            nodes.append(
                {
                    "node_id": nid,
                    "title": node.get("title"),
                    "page_index": page,
                    "citation": f"<page={page}>" if page is not None else None,
                }
            )
            text = node.get("text")
            if text:
                prefix = f"[page {page}] " if page is not None else ""
                context_parts.append(prefix + text)
        context = "\n\n".join(context_parts)
        preview = context[:1000] + ("..." if len(context) > 1000 else "")

        logger.info("retrieve_node: built context chars=%d nodes_kept=%d", len(context), len(nodes))

        return {
            **state,
            "thinking": thinking,
            "node_list": node_list,
            "nodes": nodes,
            "context": context,
            "context_preview": preview,
            "require_math": require_math,
            "citations": citations,
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("retrieve_node failed")
        raise VRETLException(str(exc), sys) from exc


__all__ = ["retrieve_node"]

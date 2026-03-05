from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from fastapi import HTTPException

from src.backend.llm import call_llm_stream
from src.backend.pageindex_chat import pageindex_chat_stream, load_doc_id
from src.config import settings
from src.utils.logger import logger

DEFAULT_NODE_MAP_PATH = Path("data/processed/node_map.json")

_NODE_MAP_CACHE: Dict[Path, Dict[str, Any]] = {}


def _load_node_map(node_map_path: Path = DEFAULT_NODE_MAP_PATH) -> Dict[str, Any] | None:
    if not node_map_path.exists():
        return None
    cached = _NODE_MAP_CACHE.get(node_map_path)
    mtime = node_map_path.stat().st_mtime
    if cached and cached.get("_mtime") == mtime:
        return cached["data"]
    try:
        with node_map_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        _NODE_MAP_CACHE[node_map_path] = {"_mtime": mtime, "data": data}
        return data
    except Exception:
        logger.warning("Failed to load node_map; continuing without it")
        return None


def handle_pageindex_combined_stream(
    query: str,
    doc_id: str | None = None,
    stream_metadata: bool = False,
):
    """Use PageIndex to pick nodes, then stream reasoning+answer from the reasoning model."""
    try:
        node_map = _load_node_map() or {}
        resolved_doc_id = load_doc_id(doc_id)

        # 1) PageIndex search (no reasoning streamed to client)
        search_prompt = f"""
You are given a question and have a tree structure of a document.
Each node contains a node id, node title, and a corresponding summary.
Your task is to find all nodes that are likely to contain the answer to the question.

Question: {query}

Please reply in the following JSON format:
{{
    "thinking": "<Your thinking process on which nodes are relevant to the question>",
    "node_list": ["node_id_1", "node_id_2", ..., "node_id_n"]
}}
Only return node_id values that appear in the tree. Do not invent node_ids.
Directly return the final JSON structure. Do not output anything else.
"""

        search_text_chunks: list[str] = []
        meta_events: list[Dict[str, Any]] = []
        for chunk in pageindex_chat_stream(
            [{"role": "user", "content": search_prompt}],
            doc_id=resolved_doc_id,
            temperature=0.1,
            stream_metadata=stream_metadata,
        ):
            if isinstance(chunk, dict):
                meta = chunk.get("block_metadata", {})
                if meta and stream_metadata:
                    meta_events.append({"type": "metadata", "metadata": meta})
                delta = (chunk.get("choices") or [{}])[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    search_text_chunks.append(content)
            elif isinstance(chunk, str):
                search_text_chunks.append(chunk)

        full_search = "".join(search_text_chunks)
        thinking = ""
        node_list: List[str] = []
        try:
            parsed = None
            try:
                parsed = json.loads(full_search)
            except json.JSONDecodeError:
                start = full_search.find("{")
                end = full_search.rfind("}")
                if start != -1 and end != -1 and end > start:
                    parsed = json.loads(full_search[start : end + 1])
            if parsed:
                thinking = parsed.get("thinking", "")
                node_list = parsed.get("node_list", []) or []
        except Exception:
            thinking = ""
            node_list = []

        # 2) Build nodes/context locally
        nodes = []
        context_parts: List[str] = []
        for nid in node_list:
            node = node_map.get(nid, {})
            if not node:
                continue
            nodes.append(
                {
                    "node_id": nid,
                    "title": node.get("title"),
                    "page_index": node.get("page_index"),
                    "citation": f"page {node.get('page_index')}" if node.get("page_index") is not None else None,
                }
            )
            text = node.get("text")
            if text:
                context_parts.append(text)
        context = "\n\n".join(context_parts)

        # 3) Stream reasoning+answer from reasoning model
        answer_prompt = f"""
Answer the question based on the context:

Question: {query}
Context: {context}

Provide a clear, concise answer based only on the context provided.
"""
        model_to_use = settings.reasoning_model or settings.chat_model

        def answer_stream():
            buffer = ""
            in_think = False
            for tok in call_llm_stream(answer_prompt, model=model_to_use, temperature=0.2):
                buffer += tok
                while True:
                    if in_think:
                        end = buffer.find("</think>")
                        if end != -1:
                            chunk = buffer[:end]
                            if chunk:
                                yield {"type": "reason", "text": chunk}
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
                            if start > 0:
                                chunk = buffer[:start]
                                if chunk:
                                    yield {"type": "answer", "text": chunk}
                            buffer = buffer[start + len("<think>"):]
                            in_think = True
                        else:
                            if buffer:
                                yield {"type": "answer", "text": buffer}
                                buffer = ""
                            break

        async def async_stream():
            yield json.dumps(
                {
                    "type": "meta",
                    "thinking": thinking,
                    "node_list": node_list,
                    "nodes": nodes,
                    "context_preview": context[:1000] + ("..." if len(context) > 1000 else ""),
                }
            ) + "\n"
            for evt in meta_events:
                yield json.dumps(evt) + "\n"
            for evt in answer_stream():
                yield json.dumps(evt) + "\n"
            yield json.dumps({"type": "done"}) + "\n"

        return async_stream()
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("Combined PageIndex+DeepSeek stream failed")
        raise HTTPException(status_code=500, detail=str(e))


__all__ = ["handle_pageindex_combined_stream"]

from __future__ import annotations

from typing import List, Optional, TypedDict, Any, Dict


class ChatState(TypedDict, total=False):
    """State passed through the LangGraph pipeline."""

    # inputs
    query: str
    doc_id: Optional[str]
    search_temperature: Optional[float]
    answer_temperature: Optional[float]
    enable_citations: bool

    # retrieval outputs
    thinking: str
    node_list: List[str]
    nodes: List[Dict[str, Any]]
    context: str
    context_preview: str

    require_math: bool
    citations: List[str]


__all__ = ["ChatState"]

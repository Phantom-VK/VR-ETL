from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(..., description="User question")
    tree_path: Optional[Path] = Field(
        default=None, description="Path to PageIndex tree JSON (defaults to data/processed/pageindex_tree.json)"
    )
    model: Optional[str] = Field(default=None, description="Deprecated; use search_model/answer_model")
    search_model: Optional[str] = Field(default=None, description="Optional model for retrieval (else REASONING_MODEL)")
    answer_model: Optional[str] = Field(default=None, description="Optional model for final answer (else CHAT_MODEL)")
    temperature: Optional[float] = Field(default=None, description="Override both temps (else per-role defaults)")
    search_temperature: Optional[float] = Field(default=None, description="Override search temp (else REASONING_TEMPERATURE)")
    answer_temperature: Optional[float] = Field(default=None, description="Override answer temp (else CHAT_TEMPERATURE)")


class SearchNode(BaseModel):
    node_id: str
    title: Optional[str] = None
    page_index: Optional[int] = None


class SearchResponse(BaseModel):
    thinking: str
    node_list: List[str]
    nodes: List[SearchNode]


class AnswerResponse(SearchResponse):
    context_preview: str
    answer: str


__all__ = [
    "QueryRequest",
    "SearchNode",
    "SearchResponse",
    "AnswerResponse",
]

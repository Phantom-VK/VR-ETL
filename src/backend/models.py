from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(..., description="User question")
    tree_path: Optional[Path] = Field(
        default=None, description="Path to PageIndex tree JSON (defaults to data/processed/pageindex_tree.json)"
    )
    model: Optional[str] = Field(default=None, description="Override model name (else uses env MODEL_NAME)")
    search_model: Optional[str] = Field(default=None, description="Optional model for retrieval")
    answer_model: Optional[str] = Field(default=None, description="Optional model for final answer")
    temperature: Optional[float] = Field(default=None, description="Override temperature (else use env defaults)")


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

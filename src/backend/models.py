from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(..., description="User question")
    doc_id: Optional[str] = Field(default=None, description="Optional PageIndex doc_id (defaults from file)")
    enable_citations: bool = Field(default=False, description="Enable inline citations in PageIndex stream")


__all__ = ["ChatRequest"]

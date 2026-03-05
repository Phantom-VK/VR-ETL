from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(..., description="User question")
    doc_id: Optional[str] = Field(default=None, description="Optional PageIndex doc_id (defaults from file)")
    stream_metadata: bool = Field(default=False, description="Include PageIndex metadata events in stream")


__all__ = ["ChatRequest"]

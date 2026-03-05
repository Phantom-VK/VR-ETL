from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.backend.models import ChatRequest
from src.backend.services import handle_pageindex_combined_stream

router = APIRouter()


@router.post("/chat")
async def chat(req: ChatRequest):
    generator = handle_pageindex_combined_stream(
        query=req.query,
        doc_id=req.doc_id,
        enable_citations=req.enable_citations,
    )
    return StreamingResponse(generator, media_type="application/x-ndjson")


__all__ = ["router"]

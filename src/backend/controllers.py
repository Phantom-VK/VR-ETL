from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.backend.models import ChatRequest
from src.backend.services import handle_pageindex_combined_stream
from src.utils.logger import logger

router = APIRouter()


@router.post("/chat")
async def chat(req: ChatRequest):
    logger.info("POST /chat query_len=%d doc_id=%s", len(req.query or ""), req.doc_id)
    generator = handle_pageindex_combined_stream(
        query=req.query,
        doc_id=req.doc_id,
        search_temperature=req.search_temperature,
        answer_temperature=req.answer_temperature,
        enable_citations=True,
    )
    return StreamingResponse(generator, media_type="application/x-ndjson")


__all__ = ["router"]

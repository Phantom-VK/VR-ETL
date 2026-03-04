from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.backend.models import QueryRequest, AnswerResponse
from src.backend.services import handle_answer_stream

router = APIRouter()


@router.post("/chat")
async def chat(req: QueryRequest):
    generator = handle_answer_stream(
        req.query,
        req.tree_path,
        req.model,
        req.temperature,
        search_model=req.search_model,
        answer_model=req.answer_model,
    )
    return StreamingResponse(generator, media_type="application/x-ndjson")

__all__ = ["router"]

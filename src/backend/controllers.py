from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.backend.models import QueryRequest, SearchResponse, AnswerResponse
from src.backend.services import handle_search, handle_answer, handle_answer_stream

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
def search(req: QueryRequest):
    return handle_search(req.query, req.tree_path, req.search_model or req.model, req.temperature)


@router.post("/answer", response_model=AnswerResponse)
def answer(req: QueryRequest):
    return handle_answer(
        req.query,
        req.tree_path,
        req.model,
        req.temperature,
        search_model=req.search_model,
        answer_model=req.answer_model,
    )


@router.post("/answer/stream")
async def answer_stream(req: QueryRequest):
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

from __future__ import annotations

from fastapi import APIRouter

from src.backend.models import QueryRequest, SearchResponse, AnswerResponse
from src.backend.services import handle_search, handle_answer

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
def search(req: QueryRequest):
    return handle_search(req.query, req.tree_path, req.model, req.temperature)


@router.post("/answer", response_model=AnswerResponse)
def answer(req: QueryRequest):
    return handle_answer(req.query, req.tree_path, req.model, req.temperature)


__all__ = ["router"]

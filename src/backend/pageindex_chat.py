"""PageIndex Chat API helpers (streaming and non-streaming)."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict

from pageindex import PageIndexClient

from src.config import settings
from src.utils.logger import logger
from src.utils.exception import VRETLException

DEFAULT_DOC_ID_PATH = Path("data/processed/doc_id.txt")


def load_doc_id(doc_id: str | None) -> str:
    """Return explicit doc_id or read the default file."""
    if doc_id:
        return doc_id
    if not DEFAULT_DOC_ID_PATH.exists():
        raise FileNotFoundError(
            f"No doc_id provided and {DEFAULT_DOC_ID_PATH} not found; run ETL or pass doc_id explicitly."
        )
    return DEFAULT_DOC_ID_PATH.read_text().strip()


def pageindex_chat_stream(
    messages: list[Dict[str, str]],
    doc_id: str | None = None,
    temperature: float | None = None,
    enable_citations: bool = False,
):
    """Stream chat_completions from PageIndex."""
    settings.validate(require_pageindex=True, require_generic_llm=False)
    resolved_doc_id = load_doc_id(doc_id)
    try:
        client = PageIndexClient(api_key=settings.pageindex_api_key)
        logger.info(
            "Streaming PageIndex chat API doc_id=%s temp=%s citations=%s",
            resolved_doc_id,
            temperature,
            enable_citations,
        )
        for chunk in client.chat_completions(
            messages=messages,
            doc_id=resolved_doc_id,
            stream=True,
            enable_citations=enable_citations,
            temperature=temperature,
        ):
            yield chunk
    except Exception as exc:  # noqa: BLE001
        logger.exception("pageindex_chat_stream failed")
        raise VRETLException(str(exc), sys) from exc


__all__ = ["pageindex_chat_stream", "load_doc_id", "DEFAULT_DOC_ID_PATH"]

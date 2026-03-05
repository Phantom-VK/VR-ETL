"""Document submission component for PageIndex ETL."""
from __future__ import annotations

from dataclasses import dataclass
import sys
from pathlib import Path
from typing import Optional

from pageindex import PageIndexClient

from src.config import settings
from src.utils.logger import logger
from src.utils.exception import VRETLException


@dataclass
class DocumentSubmitter:
    """Submit a PDF to PageIndex and persist the returned doc_id."""

    pdf_path: Path
    doc_id_path: Path
    client: Optional[PageIndexClient] = None

    def run(self) -> str:
        """Submit the document and return the doc_id."""
        try:
            logger.info("Submitting PDF to PageIndex: %s", self.pdf_path)
            settings.validate(require_pageindex=True)
            if not self.pdf_path.exists():
                raise FileNotFoundError(f"PDF not found: {self.pdf_path}")

            client = self.client or PageIndexClient(api_key=settings.pageindex_api_key)
            response = client.submit_document(str(self.pdf_path))
            doc_id = response.get("doc_id")
            if not doc_id:
                raise RuntimeError(f"Unexpected response from PageIndex: {response}")

            self.doc_id_path.parent.mkdir(parents=True, exist_ok=True)
            self.doc_id_path.write_text(doc_id.strip())
            logger.info("Document submitted; doc_id saved to %s", self.doc_id_path)
            return doc_id
        except Exception as exc:  # noqa: BLE001
            raise VRETLException(str(exc), sys) from exc


__all__ = ["DocumentSubmitter"]

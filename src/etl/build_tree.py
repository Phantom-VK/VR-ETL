"""Fetch PageIndex tree once processing is complete."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any
import sys

from pageindex import PageIndexClient

from src.config import settings
from src.utils.logger import logger
from src.utils.exception import VRETLException


@dataclass
class TreeFetcher:
    """Poll for completion and retrieve the PageIndex tree."""

    doc_id_path: Path
    output_path: Path
    poll_interval: int = 5
    timeout: int = 600
    doc_id: Optional[str] = None
    client: Optional[PageIndexClient] = None

    def _load_doc_id(self) -> str:
        if self.doc_id:
            return self.doc_id
        if not self.doc_id_path.exists():
            raise FileNotFoundError(f"doc_id file not found at {self.doc_id_path}; run DocumentSubmitter first.")
        return self.doc_id_path.read_text().strip()

    def _wait_until_ready(self, client: PageIndexClient, doc_id: str) -> None:
        start = time.time()
        while True:
            if client.is_retrieval_ready(doc_id):
                return
            if time.time() - start > self.timeout:
                raise TimeoutError(f"PageIndex retrieval not ready after {self.timeout}s for doc_id {doc_id}")
            time.sleep(self.poll_interval)

    def run(self) -> Dict[str, Any]:
        """Wait until PageIndex finishes processing and save the tree JSON."""
        try:
            settings.validate(require_openai=False, require_pageindex=True)
            doc_id = self._load_doc_id()
            logger.info("Fetching tree for doc_id=%s", doc_id)
            client = self.client or PageIndexClient(api_key=settings.pageindex_api_key)

            self._wait_until_ready(client, doc_id)
            logger.info("Retrieval ready; downloading tree.")
            response = client.get_tree(doc_id, node_summary=True)

            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            self.output_path.write_text(json.dumps(response, ensure_ascii=False, indent=2))
            logger.info("Tree saved to %s", self.output_path)
            return response
        except Exception as exc:  # noqa: BLE001
            raise VRETLException(str(exc), sys) from exc


__all__ = ["TreeFetcher"]

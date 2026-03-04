"""High-level ETL pipeline that wraps PageIndex operations."""
from __future__ import annotations

from dataclasses import dataclass
import sys
from pathlib import Path
from typing import Any, Dict

from src.etl.submit_to_pageindex import DocumentSubmitter
from src.etl.build_tree import TreeFetcher
from src.etl.build_node_map import NodeMapBuilder
from src.utils.logger import logger
from src.utils.exception import VRETLException


@dataclass
class PageIndexETLPipeline:
    """
    Pipeline that wraps PageIndex operations.
    PDF ingestion -> PageIndex Tree Retrieval -> Node Map Generation

    Attributes:
        pdf_path: Path to PDF / knowledge source
        doc_id_path: Path to Document ID returned by PageIndex
        tree_path: Path to the json file, where generated tree will be stored
        node_map_path: Path to the json file, where generated node map will be stored
        poll_interval: Time interval after which, we will check if tree is ready or not
        timeout: Time to wait for page to finish
    """

    pdf_path: Path
    doc_id_path: Path
    tree_path: Path
    node_map_path: Path
    poll_interval: int = 5
    timeout: int = 600

    def run(self) -> Dict[str, Any]:
        """Execute the full ETL pipeline and return artifacts."""
        try:
            logger.info("Starting PageIndex ETL pipeline.")
            submitter = DocumentSubmitter(pdf_path=self.pdf_path, doc_id_path=self.doc_id_path)
            doc_id = submitter.run()

            tree_response = TreeFetcher(
                doc_id=doc_id,
                doc_id_path=self.doc_id_path,
                output_path=self.tree_path,
                poll_interval=self.poll_interval,
                timeout=self.timeout,
            ).run()

            node_map = NodeMapBuilder(tree_path=self.tree_path, output_path=self.node_map_path).run()
            logger.info("ETL pipeline completed successfully.")
            return {
                "doc_id": doc_id,
                "tree": tree_response,
                "node_map": node_map,
            }
        except Exception as exc:  # noqa: BLE001
            raise VRETLException(str(exc), sys) from exc


__all__ = ["PageIndexETLPipeline"]

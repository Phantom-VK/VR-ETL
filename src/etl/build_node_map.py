"""Flatten PageIndex tree into a fast node_id lookup map."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable
import sys

from src.utils.logger import logger
from src.utils.exception import VRETLException


@dataclass
class NodeMapBuilder:
    """Create a node_id → node metadata map from a stored PageIndex tree."""

    tree_path: Path
    output_path: Path

    def _load_tree(self) -> Any:
        if not self.tree_path.exists():
            raise FileNotFoundError(f"Tree file not found at {self.tree_path}; run TreeFetcher first.")
        with self.tree_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("result", data)

    @staticmethod
    def _iter_roots(tree: Any) -> Iterable[Dict[str, Any]]:
        if isinstance(tree, list):
            return tree
        return [tree]

    def _collect(self, node: Dict[str, Any], mapping: Dict[str, Any]) -> None:
        node_id = node.get("node_id")
        if node_id:
            mapping[node_id] = {
                "title": node.get("title"),
                "summary": node.get("summary"),
                "text": node.get("text"),
                "page_index": node.get("page_index"),
                "children": [child.get("node_id") for child in node.get("children", []) if child.get("node_id")],
            }
        for child in node.get("children", []):
            self._collect(child, mapping)

    def run(self) -> Dict[str, Any]:
        """Build and persist the node map, returning the mapping dict."""
        try:
            logger.info("Building node map from tree at %s", self.tree_path)
            tree = self._load_tree()
            mapping: Dict[str, Any] = {}
            for root in self._iter_roots(tree):
                self._collect(root, mapping)

            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            with self.output_path.open("w", encoding="utf-8") as f:
                json.dump(mapping, f, ensure_ascii=False, indent=2)
            logger.info("node_map saved to %s (nodes: %d)", self.output_path, len(mapping))
            return mapping
        except Exception as exc:  # noqa: BLE001
            raise VRETLException(str(exc), sys) from exc


__all__ = ["NodeMapBuilder"]

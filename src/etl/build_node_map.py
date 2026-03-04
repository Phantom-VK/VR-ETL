"""Flatten PageIndex tree into a fast node_id lookup map."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict
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

    def _collect_any(self, obj: Any, mapping: Dict[str, Any]) -> None:
        """Walk any JSON-like structure and capture every dict with a node_id."""
        if isinstance(obj, dict):
            node_id = obj.get("node_id")
            if node_id:
                children = []
                for child in obj.get("children", []) or []:
                    if isinstance(child, dict) and child.get("node_id"):
                        children.append(child.get("node_id"))
                existing = mapping.get(node_id, {})
                mapping[node_id] = {
                    **existing,
                    "title": obj.get("title") or existing.get("title"),
                    "summary": obj.get("summary") or existing.get("summary"),
                    "text": obj.get("text") or existing.get("text"),
                    "page_index": obj.get("page_index") if obj.get("page_index") is not None else existing.get("page_index"),
                    "children": children or existing.get("children", []),
                }
            for value in obj.values():
                self._collect_any(value, mapping)
        elif isinstance(obj, list):
            for item in obj:
                self._collect_any(item, mapping)

    def run(self) -> Dict[str, Any]:
        """Build and persist the node map, returning the mapping dict."""
        try:
            logger.info("Building node map from tree at %s", self.tree_path)
            tree = self._load_tree()
            mapping: Dict[str, Any] = {}
            self._collect_any(tree, mapping)

            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            with self.output_path.open("w", encoding="utf-8") as f:
                json.dump(mapping, f, ensure_ascii=False, indent=2)
            logger.info("node_map saved to %s (nodes: %d)", self.output_path, len(mapping))
            return mapping
        except Exception as exc:  # noqa: BLE001
            raise VRETLException(str(exc), sys) from exc


__all__ = ["NodeMapBuilder"]
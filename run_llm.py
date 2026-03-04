import argparse
import json
from pathlib import Path

from src.backend.retrieval import search_tree_with_llm, create_node_mapping, format_search_result


def load_tree(tree_path: Path):
    if not tree_path.exists():
        raise FileNotFoundError(f"Tree file not found at {tree_path}; run the ETL first.")
    with tree_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("result", data)


def main(query: str, tree_path: Path):
    tree = load_tree(tree_path)
    result = search_tree_with_llm(query, tree)
    node_map = create_node_mapping(tree)
    print(format_search_result(result, node_map))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run LLM tree search over PageIndex tree")
    parser.add_argument("--query", default="What are the conclusions in this document?", help="User question")
    parser.add_argument("--tree", type=Path, default=Path("data/processed/pageindex_tree.json"), help="Path to tree JSON")
    args = parser.parse_args()
    main(args.query, args.tree)

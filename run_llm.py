import json
from pathlib import Path

from src.backend.retrieval import search_tree_with_llm, create_node_mapping, format_search_result
from src.utils.logger import logger

DEFAULT_QUERY = "Give me the list of all regional tables and what is their content and page number. "
TREE_PATH = Path("data/processed/pageindex_tree.json")


def load_tree(tree_path: Path):
    logger.info("Loading tree from %s", tree_path)
    if not tree_path.exists():
        raise FileNotFoundError(f"Tree file not found at {tree_path}; run the ETL first.")
    with tree_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    tree = data.get("result", data)
    logger.info("Loaded tree; root type=%s", type(tree).__name__)
    return tree


def main(query: str = DEFAULT_QUERY, tree_path: Path = TREE_PATH):
    logger.info("Starting LLM tree search entrypoint.")
    tree = load_tree(tree_path)
    result = search_tree_with_llm(query, tree)
    node_map = create_node_mapping(tree)
    logger.info("Node map built; nodes=%d", len(node_map))
    print(format_search_result(result, node_map))
    logger.info("Completed LLM tree search entrypoint.")


if __name__ == "__main__":
    main()

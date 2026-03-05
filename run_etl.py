from pathlib import Path
from src.etl import PageIndexETLPipeline




if __name__ == "__main__":
    pipeline = PageIndexETLPipeline(
        pdf_path=Path("docs/State-of-the-Cyber-Security-Sector-in-Ireland-2022-Report.pdf"),
        doc_id_path=Path("data/processed/doc_id.txt"),
        tree_path=Path("data/processed/pageindex_tree.json"),
        node_map_path=Path("data/processed/node_map.json"),
        poll_interval=5,
        timeout=600,
    )
    pipeline.run()

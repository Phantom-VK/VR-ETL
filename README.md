# VR-ETL

Vectorless RAG ETL pipeline built around PageIndex to ingest PDFs and produce a structured, query-ready knowledge base (tree + node map).

## Prerequisites
- Python 3.9 (this environment’s 3.12 lacks `_ssl`; 3.9 works with pip/HTTPS).
- Virtual env (`python -m venv .venv`) and activate it.
- Install deps: `pip install -r requirements.txt`.
- Secrets: set `PAGEINDEX_API_KEY` (required) and `OPENAI_API_KEY` (not used in ETL but required for downstream agent). Copy `.env.example` → `.env` and fill values, or export in your shell.

## ETL Outputs (knowledge base artifacts)
- `data/processed/doc_id.txt` – PageIndex doc identifier.
- `data/processed/pageindex_tree.json` – full hierarchical tree returned by PageIndex (`get_tree`, with summaries).
- `data/processed/node_map.json` – flattened `node_id -> {title, summary, text, page_index, children}` for fast lookup.

## How to run the ETL
1) Activate venv and load env vars: `source .venv/bin/activate` and ensure `PAGEINDEX_API_KEY` is set (or placed in `.env`).
2) Run the pipeline entry point:
   ```bash
   python run_etl.py
   ```
   The default paths in `run_etl.py` point to `docs/State-of-the-Cyber-Security-Sector-in-Ireland-2022-Report.pdf` and write outputs under `data/processed/`.
3) Logs: emitted to `logs/<dd_mm_YYYY_HH:MM>/<timestamp>.log` and stdout, via `src/utils/logger.py`.

### Customizing paths/timeouts
Edit `run_etl.py` or instantiate `PageIndexETLPipeline` directly:
```python
from pathlib import Path
from src.etl import PageIndexETLPipeline

pipeline = PageIndexETLPipeline(
    pdf_path=Path("docs/State-of-the-Cyber-Security-Sector-in-Ireland-2022-Report.pdf"),
    doc_id_path=Path("data/processed/doc_id.txt"),
    tree_path=Path("data/processed/pageindex_tree.json"),
    node_map_path=Path("data/processed/node_map.json"),
    poll_interval=5,
    timeout=600,
)
pipeline.run()
```

## Components
- `src/etl/submit_to_pageindex.py` – submits PDF, stores `doc_id`.
- `src/etl/build_tree.py` – polls readiness, fetches PageIndex tree JSON.
- `src/etl/build_node_map.py` – flattens tree into node map.
- `src/etl/pipeline.py` – orchestrates the full ETL.
- `src/utils/logger.py` – shared logging (file + stdout).
- `src/utils/exception.py` – custom exception with filename/line capture.

## Notes
- Data artifacts (`data/processed/*`) and logs are ignored from git; regenerate via the ETL.

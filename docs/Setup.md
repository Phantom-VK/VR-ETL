# Setup

## Prerequisites
- Python 3.9 (this environment’s 3.12 lacks `_ssl`; 3.9 works with pip/HTTPS).
- Create and activate a virtual env: `python -m venv .venv && source .venv/bin/activate`.
- Install deps: `pip install -r requirements.txt`.
- Secrets: set `PAGEINDEX_API_KEY` (required). Copy `.env.example` → `.env` and fill values, or export in your shell.
- Generic LLM access: set `API_KEY`, `BASE_URL`, `CHAT_MODEL` (answers, temp fixed 0.2), `REASONING_MODEL` (PageIndex search + answer reasoning, temp fixed 0.1).

## ETL Outputs (knowledge base artifacts)
- `data/processed/doc_id.txt` – PageIndex doc identifier.
- `data/processed/pageindex_tree.json` – hierarchical tree returned by PageIndex (`get_tree`, with summaries).
- `data/processed/node_map.json` – flattened `node_id -> {title, summary, text, page_index, children}` for fast lookup.
- `data/processed/tables.json` – (if enabled) extracted table-like nodes.

## Run the ETL
1) Activate venv and load env vars.
2) Run:
   ```bash
   python run_etl.py
   ```
   Defaults point to `docs/State-of-the-Cyber-Security-Sector-in-Ireland-2022-Report.pdf` and write under `data/processed/`.
3) Logs: `logs/<dd_mm_YYYY_HH:MM>/<timestamp>.log` and stdout via `src/utils/logger.py`.

### Customizing paths/timeouts
Edit `run_etl.py` or instantiate `PageIndexETLPipeline`:
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

## Run the FastAPI backend (/chat)
Prereq: ETL outputs present and generic LLM creds in `.env`.
```bash
uvicorn src.backend.api:app --reload
```
Endpoint:
- `POST /chat` returns NDJSON: meta line (thinking, nodes, context preview) then streaming reasoning/answer tokens and a final `done`.

UI:
- Static UI in `src/frontend/index.html` calls `/chat`, streams reasoning/answer live.
- Run backend, then open the HTML (or serve via `python -m http.server -d src/frontend 5500`). CORS is enabled on the API for local use.

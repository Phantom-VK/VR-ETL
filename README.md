# VR-ETL

Vectorless RAG ETL pipeline built around PageIndex to ingest PDFs and produce a structured, query-ready knowledge base (tree + node map).

## Prerequisites
- Python 3.9 (this environment’s 3.12 lacks `_ssl`; 3.9 works with pip/HTTPS).
- Virtual env (`python -m venv .venv`) and activate it.
- Install deps: `pip install -r requirements.txt`.
- Secrets: set `PAGEINDEX_API_KEY` (required). Copy `.env.example` → `.env` and fill values, or export in your shell.
- Generic LLM access: set `API_KEY`, `BASE_URL`, `CHAT_MODEL` (used for search), `REASONING_MODEL` (used for search + answer), plus optional `CHAT_TEMPERATURE` and `REASONING_TEMPERATURE` (defaults 0.0). Requests can override `search_model`, `answer_model`, and `temperature`.

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

## How to run the FastAPI backend (search + answer)
Requires ETL outputs and generic LLM creds in `.env`.
```bash
uvicorn src.backend.api:app --reload
```
Endpoint:
- `POST /chat` returns NDJSON: meta line (thinking, nodes, context preview) then streaming reasoning/answer tokens and a final `done`.

- Static UI in `src/frontend/index.html` calls `/chat`, shows reasoning/selected nodes, and streams the answer tokens live.
- Run the backend, then open the HTML in a browser (or serve locally, e.g., `python -m http.server -d src/frontend 5500`). CORS is enabled on the API for local use.

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
- `src/backend/llm.py` – `call_llm(prompt, model, temperature)` wrapper over OpenAI-compatible chat completions (API key/base URL/model driven by env).
- `src/backend/retrieval.py` – LLM-driven tree search helpers (strip text, map nodes, format output).
- `src/utils/logger.py` – shared logging (file + stdout).
- `src/utils/exception.py` – custom exception with filename/line capture.

## Notes
- Data artifacts (`data/processed/*`) and logs are ignored from git; regenerate via the ETL.

# VR-ETL

Vectorless RAG ETL pipeline built around PageIndex to ingest PDFs and produce a structured, query-ready knowledge base (tree + node map).

## Setup
All setup/install/run instructions have moved to [docs/Setup.md](docs/Setup.md).

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

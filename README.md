# VR-ETL

[![Python](https://img.shields.io/badge/Python-3.9+-3670A0?logo=python&logoColor=ffdd54)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PageIndex](https://img.shields.io/badge/PageIndex-API-blue)](https://pageindex.ai/)
[![DeepSeek](https://img.shields.io/badge/DeepSeek-LLM-purple)](https://api.deepseek.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Orchestration-ff6f61)](https://langchain-ai.github.io/langgraph/)

Vectorless, agentic QA over the Cyber Ireland 2022 report. ETL ingests the PDF into a PageIndex tree + node map; a single `/chat` endpoint orchestrates retrieval, math tooling, and streaming answers with citations.

## Tech Stack
- FastAPI backend with LangGraph orchestration
- PageIndex for document ingestion and hierarchical retrieval
- DeepSeek (OpenAI-compatible) for reasoning + tool calls
- Sympy math tool (strict function-calling protocol)
- Static frontend (vanilla HTML/JS) with streamed NDJSON and Mermaid rendering

## Documentation
- [Setup](docs/Setup.md) — environment, env vars
- [ETL](docs/etl.md) — pipeline steps, artifacts
- [Backend](docs/backend.md) — endpoints, prompts, flow
- [Frontend](docs/frontend.md) — UI usage

## Quick Start
```bash
pip install -r requirements.txt
cp .env.example .env  # fill PAGEINDEX_API_KEY, API_KEY, BASE_URL, MODELS
python run_etl.py     # generates doc_id, tree, node_map
uvicorn src.backend.api:app --reload
# open src/frontend/index.html (or serve via python -m http.server -d src/frontend 5500)
```

## Notes
- Data artifacts (`data/processed/*`) and logs are git-ignored; regenerate via ETL.
- `/chat` streams NDJSON events: meta → tool (if math) → reason → answer → done.

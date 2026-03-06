# Setup

This file only covers environment prep and credentials. Run/ETL/backend usage is documented elsewhere.

## Prerequisites
- Python 3.9
- Virtual env: `python -m venv .venv && source .venv/bin/activate`
- Install deps: `pip install -r requirements.txt`

## Environment variables (.env)
- `PAGEINDEX_API_KEY` — required for PageIndex ETL (submit/fetch tree/node_map).
- `API_KEY` — required for LLM calls (DeepSeek/OpenAI-compatible) used by backend/tool calls.
- `BASE_URL` — LLM API base URL (e.g., DeepSeek endpoint).
- `CHAT_MODEL` — chat model for tool calls / answers (fallback if reasoning model absent).
- `REASONING_MODEL` — preferred model for reasoning/answers; also used when forcing tool calls.

How to set:
1) Copy `.env.example` to `.env` and fill the values, or export them in your shell.
2) Ensure your virtualenv is active so `python` sees the installed packages.

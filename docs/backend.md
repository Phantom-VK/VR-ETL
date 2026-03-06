# Backend Overview

Single FastAPI app exposing `/chat` for retrieval + reasoning + math tooling.

## Entry point
- [src/backend/api.py](../src/backend/api.py): creates FastAPI app, adds CORS, includes router.
- [src/backend/controllers.py](../src/backend/controllers.py): defines `POST /chat` → `handle_pageindex_combined_stream`.

## Request model
- [src/backend/models.py](../src/backend/models.py): `ChatRequest` with `query`, optional `doc_id`, temps, `use_math_tool`.

## Services / Orchestration
- [src/backend/services.py](../src/backend/services.py): core pipeline for `/chat`.
  - Runs LangGraph retrieval → PageIndex → node_map context.
  - Decides math usage via `require_math` from retrieval + heuristics.
  - Math tool path (DeepSeek tool call) feeds result back, then streams final answer.
  - Citation enforcement retry if answer lacks `<page=...>`.
  - Streams NDJSON events: `meta`, `tool`, `reason`, `answer`, `done`.

## Retrieval (LangGraph)
- [src/backend/graph/app.py](../src/backend/graph/app.py): builds graph (retrieve node).
- [src/backend/graph/nodes.py](../src/backend/graph/nodes.py): PageIndex chat search, node_map lookup, context build, math intent flag.
- [src/backend/graph/state.py](../src/backend/graph/state.py): shared state structure.

## Prompts
- [src/backend/prompts.py](../src/backend/prompts.py): system/user/citation-retry/search prompts.
- [src/backend/prompts_math.py](../src/backend/prompts_math.py): math intent heuristics.

## LLM wrappers
- [src/backend/llm.py](../src/backend/llm.py):
  - `call_llm_stream_messages` for streaming answer/reason.
  - `call_llm_tools` for tool call turn (DeepSeek/OpenAI style).

## PageIndex helper
- [src/backend/pageindex_chat.py](../src/backend/pageindex_chat.py): loads doc_id, streams PageIndex chat (citations always on).

## Math tool
- [src/backend/graph/tools.py](../src/backend/graph/tools.py): `evaluate_math` schema (strict) + Sympy-based safe evaluator.

## Frontend (companion UI)
- [src/frontend/index.html](../src/frontend/index.html) & [src/frontend/app.js](../src/frontend/app.js): static UI calling `/chat`, streaming reasoning/answer, renders Mermaid if present.

## Logging & Errors
- [src/utils/logger.py](../src/utils/logger.py): file+stdout logging.
- [src/utils/exception.py](../src/utils/exception.py): enriched exceptions.

## How `/chat` flows (concise)
1) Controller receives `ChatRequest` → service.
2) Service runs LangGraph retrieval (PageIndex chat → node_map context).
3) If `require_math` true, do tool-call turn, execute math, attach tool result.
4) Stream final answer (reason/answer tokens); retry with citation-enforce prompt if no `<page=...>` found.
5) NDJSON events returned to client.

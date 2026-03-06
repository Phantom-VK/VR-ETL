# Architecture

## Current flow (high level)
- ETL: PDF → PageIndex submit → retrieval-ready tree → node_map (flattened) → artifacts in `data/processed/`.
- Serving: `/chat` (FastAPI) → LangGraph retrieval node → PageIndex chat → node_map context → (optional) math tool → DeepSeek answer streaming.
- Streaming contract: NDJSON events `meta` → `tool` (if math) → `reason` → `answer` → `done`.

## Components (with links)
- ETL pipeline: [src/etl/pipeline.py](../src/etl/pipeline.py)
- PageIndex helpers: [src/backend/pageindex_chat.py](../src/backend/pageindex_chat.py)
- Graph orchestration: [src/backend/graph/app.py](../src/backend/graph/app.py), [src/backend/graph/nodes.py](../src/backend/graph/nodes.py), [src/backend/graph/state.py](../src/backend/graph/state.py)
- Prompts: [src/backend/prompts.py](../src/backend/prompts.py), [src/backend/prompts_math.py](../src/backend/prompts_math.py)
- Math tool: [src/backend/graph/tools.py](../src/backend/graph/tools.py)
- LLM wrappers: [src/backend/llm.py](../src/backend/llm.py)
- Service orchestration: [src/backend/services.py](../src/backend/services.py)
- API: [src/backend/api.py](../src/backend/api.py), [src/backend/controllers.py](../src/backend/controllers.py)
- Frontend: [src/frontend/index.html](../src/frontend/index.html), [src/frontend/app.js](../src/frontend/app.js)

## Architecture justification
- **ETL strategy (PageIndex + node_map):** Kept the ETL simple and modular for reuse. Chose PageIndex after exploring vectorless/VLM RAG on social media and read articles about it ,
thought this is a best chance to learn and implement the Vectorless RAG using Pageindex. It is a vectorless, reasoning-based RAG (retrieval) framework that simulates how human experts navigate and extract knowledge from long, complex documents. Instead of relying on vector similarity search, it transforms documents into a tree-structured index and enables LLMs to perform agentic reasoning over that structure for context-aware retrieval. 
The retrieval process is traceable and explainable, and requires no vector database and no chunking. On top of this we have added a node_map hash for O(1) node_id→text lookup so when PageIndex returns node_ids we can instantly fetch full context without re-walking the tree. Pageindex is kind of slower than basic vector RAGs, but its
context accuracy far way better than it.

- **Agent framework (LangGraph + PageIndex search):** LangGraph gives clean orchestration/state, so it’s easy to slot in more tools/steps later and keep state management explicit, I already has used it in one project, so was easier to design this system with Langgraph.
We are using, PageIndex’s tree search (Hybrid Tree Search: [docs](https://docs.pageindex.ai/tutorials/tree-search/hybrid)) to gather context quickly compared to ad-hoc LLM tree walks; the graph node wraps that retrieval so downstream steps stay simple.

- **Toolset (DeepSeek chat/reasoner + Sympy math tool):** 
Used deepseek-reasoner model here, cause by personal usage, I have experienced that deepseek has better reasoning than other LLMs the way it thinks is fabulous. Also it is pretty good at maths
(maybe cause its Chinese), jokes apart. It is generally good at maths, as I have used personally a lot and had some 2-3$ credits in its API, so considering all the plus points,
I decided to use DeepSeel reasoner model. As deepseek already takes care of maths, but as its a LLM, which just mathematically predicts next word, it can be wrong at calculations sometimes, to overcome this
we use Sympy to do math calculations over provided expression, for more accuracy.


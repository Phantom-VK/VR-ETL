# Frontend

Simple static UI (vanilla HTML/JS/CSS) under `src/frontend/` that calls the `/chat` endpoint, streams reasoning and answer tokens (NDJSON), and renders Mermaid diagrams when present in the answer. Serve locally (e.g., `python -m http.server -d src/frontend 5500`) after running the FastAPI backend.

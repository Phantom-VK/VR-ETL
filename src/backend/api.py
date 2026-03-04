from __future__ import annotations

from fastapi import FastAPI

from src.backend.controllers import router

app = FastAPI(title="VR-ETL Backend", version="0.1.0")
app.include_router(router)

__all__ = ["app"]

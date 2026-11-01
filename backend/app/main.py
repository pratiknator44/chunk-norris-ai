"""DocExtract API service."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import documents, feedback, health, jobs, schemas
from app.config import settings
from app.db.session import init_db
from app.jobs.worker import start_worker, stop_worker


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Initialize SQLite database and tables
    init_db()

    # Ensure runtime data directories exist
    settings.resolved_data_dir.mkdir(parents=True, exist_ok=True)
    (settings.resolved_data_dir / "uploads").mkdir(parents=True, exist_ok=True)
    (settings.resolved_data_dir / "parsed").mkdir(parents=True, exist_ok=True)

    # Start background job worker
    start_worker()

    yield

    # Shutdown worker
    await stop_worker()


app = FastAPI(
    title="Chunk Norris API",
    description="Convert PDF to JSON via local LLM",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handler for RFC 7807 problem details
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "type": "about:blank",
            "title": "Internal Server Error",
            "status": 500,
            "detail": str(exc),
            "instance": request.url.path,
        },
        media_type="application/problem+json",
    )


# API Routers under /api/v1
app.include_router(health.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(schemas.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(feedback.router, prefix="/api/v1")

# Also expose /health at root for container orchestrators
app.include_router(health.router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Chunk Norris API is running", "docs": "/docs"}

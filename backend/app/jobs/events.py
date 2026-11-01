"""Server-Sent Events (SSE) manager and pub/sub for DocExtract."""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from collections.abc import AsyncGenerator
from typing import Any

from sqlmodel import Session, select

from app.db.models import ChunkResult, Job
from app.db.session import engine

logger = logging.getLogger(__name__)


def format_sse(event: str, data: dict[str, Any]) -> str:
    """Formats event name and dictionary data into standard SSE string format."""
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


class EventManager:
    def __init__(self) -> None:
        # job_id -> set of asyncio.Queue listeners
        self._listeners: dict[str, set[asyncio.Queue[str]]] = defaultdict(set)
        self._parsing_progress: dict[str, dict[str, Any]] = {}
        self._in_progress_chunk: dict[str, dict[str, Any]] = {}

    async def broadcast(self, job_id: str, event_type: str, data: dict[str, Any]) -> None:
        """Broadcasts an SSE event to all connected listeners for a given job."""
        if event_type == "parsing_progress":
            self._parsing_progress[job_id] = data
        elif event_type == "chunk":
            if data.get("status") == "in_progress":
                self._in_progress_chunk[job_id] = data
            elif data.get("status") == "saved":
                self._in_progress_chunk.pop(job_id, None)
        elif event_type in ("done", "error") or (
            event_type == "status" and data.get("stage") not in ("parsing", "extracting", None)
        ):
            self._parsing_progress.pop(job_id, None)
            self._in_progress_chunk.pop(job_id, None)

        msg = format_sse(event_type, data)
        queues = list(self._listeners.get(job_id, set()))

        for q in queues:
            try:
                q.put_nowait(msg)
            except Exception as e:
                logger.warning(f"Failed to deliver SSE event to queue: {e}")

    async def subscribe(self, job_id: str) -> AsyncGenerator[str, None]:
        """Subscribes to SSE stream for job_id, replaying existing state on connect."""
        q: asyncio.Queue[str] = asyncio.Queue()
        self._listeners[job_id].add(q)

        try:
            # 1. State replay from DB
            with Session(engine) as session:
                job = session.exec(select(Job).where(Job.id == job_id)).first()
                if job:
                    # Initial status event
                    yield format_sse("status", {"stage": job.status})

                    # Parsing progress if currently parsing
                    if job.status == "parsing" and job_id in self._parsing_progress:
                        yield format_sse("parsing_progress", self._parsing_progress[job_id])

                    # Shape event if available
                    if job.resolved_shape:
                        try:
                            shape_data = json.loads(job.resolved_shape)
                            yield format_sse("shape", shape_data)
                        except Exception:
                            pass

                    # Chunk checkpoints replayed in chunk_index order
                    chunks = session.exec(
                        select(ChunkResult)
                        .where(ChunkResult.job_id == job_id)
                        .order_by(ChunkResult.chunk_index)  # type: ignore[arg-type]
                    ).all()

                    for chunk in chunks:
                        yield format_sse(
                            "chunk",
                            {
                                "index": chunk.chunk_index,
                                "total": job.chunks_total,
                                "status": "saved",
                                "attempts": chunk.attempts,
                                "duration_ms": chunk.duration_ms,
                                "duration_sec": round(chunk.duration_ms / 1000, 2),
                                "result": chunk.get_data(),
                            },
                        )

                    # In-progress chunk if currently extracting
                    if job.status == "extracting" and job_id in self._in_progress_chunk:
                        yield format_sse("chunk", self._in_progress_chunk[job_id])

                    # Result if already completed
                    if job.status == "done" and job.result_json:
                        yield format_sse("done", {"result": job.get_result()})
                    elif job.status == "failed":
                        yield format_sse("error", {"message": job.error or "Job failed"})
                    elif job.status == "cancelled":
                        yield format_sse("status", {"stage": "cancelled"})

            # 2. Live event stream loop
            while True:
                msg = await q.get()
                yield msg
                # Break after terminal events
                if msg.startswith("event: done") or msg.startswith("event: error"):
                    break
        finally:
            if job_id in self._listeners:
                self._listeners[job_id].discard(q)
                if not self._listeners[job_id]:
                    del self._listeners[job_id]


event_manager = EventManager()

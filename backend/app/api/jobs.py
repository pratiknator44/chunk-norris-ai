"""Job management, checkpoint inspection, and SSE endpoints."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db.models import ChunkResult, Document, Job, utc_now
from app.db.session import get_session
from app.jobs.events import event_manager
from app.jobs.queue import job_queue

router = APIRouter(prefix="/jobs", tags=["jobs"])

SessionDep = Annotated[Session, Depends(get_session)]


class CreateJobRequest(BaseModel):
    document_id: str
    input_text: str
    input_mode: str = "auto"  # "auto" | "shape" | "natural_language"
    model: str | None = None
    chunk_size: int | None = None


class JobSummary(BaseModel):
    id: str
    document_id: str
    status: str
    input_mode: str
    chunks_done: int
    chunks_total: int
    created_at: datetime
    updated_at: datetime
    error: str | None = None


class JobDetail(JobSummary):
    input_text: str
    resolved_shape: dict[str, Any] | None = None
    result: Any | None = None


class ChunkDetail(BaseModel):
    index: int
    status: str
    attempts: int
    duration_ms: int
    duration_sec: float | None = None
    result: Any


@router.post("", response_model=JobSummary, status_code=status.HTTP_202_ACCEPTED)
async def create_job(
    payload: CreateJobRequest,
    session: SessionDep,
) -> JobSummary:
    doc = session.exec(select(Document).where(Document.id == payload.document_id)).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {payload.document_id} not found.",
        )

    job = Job(
        document_id=payload.document_id,
        input_text=payload.input_text,
        input_mode=payload.input_mode,
        model=payload.model or "",
        chunk_size=payload.chunk_size or 8000,
        status="queued",
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    # Enqueue to background worker
    await job_queue.enqueue(job.id)

    return JobSummary(
        id=job.id,
        document_id=job.document_id,
        status=job.status,
        input_mode=job.input_mode,
        chunks_done=job.chunks_done,
        chunks_total=job.chunks_total,
        created_at=job.created_at,
        updated_at=job.updated_at,
        error=job.error,
    )


@router.get("", response_model=list[JobSummary])
async def list_jobs(
    session: SessionDep,
    limit: int = 50,
) -> list[JobSummary]:
    jobs = session.exec(
        select(Job).order_by(Job.created_at.desc()).limit(limit)  # type: ignore[attr-defined]
    ).all()
    return [
        JobSummary(
            id=j.id,
            document_id=j.document_id,
            status=j.status,
            input_mode=j.input_mode,
            chunks_done=j.chunks_done,
            chunks_total=j.chunks_total,
            created_at=j.created_at,
            updated_at=j.updated_at,
            error=j.error,
        )
        for j in jobs
    ]


@router.get("/{job_id}", response_model=JobDetail)
async def get_job(
    job_id: str,
    session: SessionDep,
) -> JobDetail:
    job = session.exec(select(Job).where(Job.id == job_id)).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found.",
        )

    resolved_shape_data = None
    if job.resolved_shape:
        try:
            resolved_shape_data = json.loads(job.resolved_shape)
        except Exception:
            pass

    return JobDetail(
        id=job.id,
        document_id=job.document_id,
        status=job.status,
        input_mode=job.input_mode,
        input_text=job.input_text,
        resolved_shape=resolved_shape_data,
        chunks_done=job.chunks_done,
        chunks_total=job.chunks_total,
        result=job.get_result(),
        created_at=job.created_at,
        updated_at=job.updated_at,
        error=job.error,
    )


@router.get("/{job_id}/chunks", response_model=list[ChunkDetail])
async def get_job_chunks(
    job_id: str,
    session: SessionDep,
) -> list[ChunkDetail]:
    job = session.exec(select(Job).where(Job.id == job_id)).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found.",
        )

    chunks = session.exec(
        select(ChunkResult).where(ChunkResult.job_id == job_id).order_by(ChunkResult.chunk_index)  # type: ignore[arg-type]
    ).all()

    return [
        ChunkDetail(
            index=c.chunk_index,
            status="saved",
            attempts=c.attempts,
            duration_ms=c.duration_ms,
            duration_sec=round(c.duration_ms / 1000, 2),
            result=c.get_data(),
        )
        for c in chunks
    ]


@router.get("/{job_id}/events")
async def stream_job_events(job_id: str) -> StreamingResponse:
    """Streams SSE updates for a job with automatic state replay on connect."""
    return StreamingResponse(
        event_manager.subscribe(job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{job_id}/cancel", response_model=JobSummary)
async def cancel_job_endpoint(
    job_id: str,
    session: SessionDep,
) -> JobSummary:
    job = session.exec(select(Job).where(Job.id == job_id)).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found.",
        )

    await job_queue.cancel(job_id)
    job.status = "cancelled"
    job.updated_at = utc_now()
    session.commit()
    session.refresh(job)

    await event_manager.broadcast(job_id, "status", {"stage": "cancelled"})

    return JobSummary(
        id=job.id,
        document_id=job.document_id,
        status=job.status,
        input_mode=job.input_mode,
        chunks_done=job.chunks_done,
        chunks_total=job.chunks_total,
        created_at=job.created_at,
        updated_at=job.updated_at,
        error=job.error,
    )


@router.post("/{job_id}/retry", response_model=JobSummary, status_code=status.HTTP_202_ACCEPTED)
async def retry_job_endpoint(
    job_id: str,
    session: SessionDep,
) -> JobSummary:
    job = session.exec(select(Job).where(Job.id == job_id)).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found.",
        )

    job.status = "queued"
    job.error = None
    job.updated_at = utc_now()
    session.commit()
    session.refresh(job)

    await job_queue.enqueue(job.id)

    return JobSummary(
        id=job.id,
        document_id=job.document_id,
        status=job.status,
        input_mode=job.input_mode,
        chunks_done=job.chunks_done,
        chunks_total=job.chunks_total,
        created_at=job.created_at,
        updated_at=job.updated_at,
        error=job.error,
    )


@router.get("/{job_id}/result.json")
async def download_job_result(
    job_id: str,
    session: SessionDep,
) -> Response:
    job = session.exec(select(Job).where(Job.id == job_id)).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found.",
        )

    if not job.result_json:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job {job_id} has no completed result yet (status: {job.status}).",
        )

    return Response(
        content=job.result_json,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="result_{job_id[:8]}.json"'},
    )

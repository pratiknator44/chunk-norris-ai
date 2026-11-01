"""Background job worker with checkpoint resumption and SSE streaming."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

from sqlmodel import Session, select

from app.config import settings
from app.core.chunking import split_document
from app.core.llm import (
    TokenLimitExceededError,
    extract_chunk_json,
    get_active_model_id,
    get_async_openai_client,
    infer_shape_from_nl,
)
from app.core.merge import merge_results
from app.core.parsing import parse_pdf
from app.core.prompts import build_extraction_prompts
from app.core.schema import (
    shape_tree_to_json_schema,
    shape_tree_to_pydantic_model,
    validate_extracted_data,
)
from app.core.shape import detect_mode, parse_shape
from app.db.models import ChunkResult, Document, Job, utc_now
from app.db.session import engine
from app.jobs.events import event_manager
from app.jobs.queue import job_queue

logger = logging.getLogger(__name__)

_worker_task: asyncio.Task[None] | None = None
_stop_event = asyncio.Event()


def _resolve_pdf_path(doc_filename: str, parsed_md_path: str | None) -> Path:
    if parsed_md_path and Path(parsed_md_path).exists():
        return Path(parsed_md_path)
    p = settings.resolved_data_dir / "uploads" / doc_filename
    if not p.exists():
        raise FileNotFoundError(f"PDF upload not found on disk: {p}")
    return p


async def process_single_chunk(
    client: Any,
    model: str,
    tree: Any,
    json_schema: dict[str, Any],
    pydantic_model: Any,
    chunk_text: str,
    chunk_index: int,
    total_chunks: int,
) -> dict[str, Any] | list[Any]:
    """Extracts and validates a chunk, halving chunk size if token limit is exceeded."""
    sys_prompt, usr_prompt = build_extraction_prompts(
        tree,
        chunk_text,
        chunk_index + 1,
        total_chunks,
        json_schema,
    )

    try:
        raw_output = await extract_chunk_json(
            client=client,
            model=model,
            system_prompt=sys_prompt,
            user_prompt=usr_prompt,
            json_schema=json_schema,
            chunk_text=chunk_text,
        )
        return validate_extracted_data(raw_output, tree, pydantic_model)
    except TokenLimitExceededError:
        logger.warning(
            f"Chunk {chunk_index + 1} hit token limit. Halving chunk and processing parts..."
        )
        # Split chunk into two halves and extract both
        mid = len(chunk_text) // 2
        split_at = chunk_text.rfind("\n\n", 0, mid + 200)
        if split_at <= 0:
            split_at = chunk_text.rfind(" ", 0, mid + 200)
        if split_at <= 0:
            split_at = mid

        part1 = chunk_text[:split_at].strip()
        part2 = chunk_text[split_at:].strip()

        sub_res1 = await process_single_chunk(
            client, model, tree, json_schema, pydantic_model, part1, chunk_index, total_chunks
        )
        sub_res2 = await process_single_chunk(
            client, model, tree, json_schema, pydantic_model, part2, chunk_index, total_chunks
        )
        return merge_results([sub_res1, sub_res2], tree)


async def execute_job(job_id: str) -> None:
    """Executes the extraction pipeline for a job."""
    logger.info(f"Starting execution of job {job_id}")

    with Session(engine) as session:
        job = session.exec(select(Job).where(Job.id == job_id)).first()
        if not job:
            logger.error(f"Job {job_id} not found in database")
            return

        doc = session.exec(select(Document).where(Document.id == job.document_id)).first()
        if not doc:
            job.status = "failed"
            job.error = "Associated document not found"
            session.commit()
            await event_manager.broadcast(job_id, "error", {"message": job.error})
            return

    try:
        if await job_queue.is_cancelled(job_id):
            with Session(engine) as session:
                j = session.exec(select(Job).where(Job.id == job_id)).first()
                if j:
                    j.status = "cancelled"
                    session.commit()
            await event_manager.broadcast(job_id, "status", {"stage": "cancelled"})
            return

        client = get_async_openai_client()
        active_model = job.model or await get_active_model_id(client)

        # -------------------------------------------------------------
        # Stage 1: Shape Resolution & Mode Detection
        # -------------------------------------------------------------
        shape_text: str = ""
        mode = job.input_mode

        if mode == "auto":
            detected_mode, mode_info = detect_mode(job.input_text)
            mode = detected_mode

        if mode == "natural_language":
            with Session(engine) as session:
                j = session.exec(select(Job).where(Job.id == job_id)).first()
                if j:
                    j.status = "inferring_shape"
                    j.updated_at = utc_now()
                    session.commit()
            await event_manager.broadcast(job_id, "status", {"stage": "inferring_shape"})

            tree, inferred_shape_text = await infer_shape_from_nl(
                job.input_text, client, active_model
            )
            shape_text = inferred_shape_text
        else:
            shape_text = job.input_text
            tree = parse_shape(shape_text)

        json_schema = shape_tree_to_json_schema(tree)
        pydantic_model = shape_tree_to_pydantic_model(tree)

        # Snapshot resolved shape on job
        shape_snapshot = {
            "shape_text": shape_text,
            "json_schema": json_schema,
        }
        with Session(engine) as session:
            j = session.exec(select(Job).where(Job.id == job_id)).first()
            if j:
                j.resolved_shape = json.dumps(shape_snapshot, ensure_ascii=False)
                j.model = active_model
                session.commit()
        await event_manager.broadcast(job_id, "shape", shape_snapshot)

        # -------------------------------------------------------------
        # Stage 2: PDF Parsing (Docling + Cache)
        # -------------------------------------------------------------
        if await job_queue.is_cancelled(job_id):
            with Session(engine) as session:
                j = session.exec(select(Job).where(Job.id == job_id)).first()
                if j:
                    j.status = "cancelled"
                    session.commit()
            await event_manager.broadcast(job_id, "status", {"stage": "cancelled"})
            return

        with Session(engine) as session:
            j = session.exec(select(Job).where(Job.id == job_id)).first()
            if j:
                j.status = "parsing"
                j.updated_at = utc_now()
                session.commit()
        await event_manager.broadcast(job_id, "status", {"stage": "parsing"})

        pdf_path = await asyncio.to_thread(_resolve_pdf_path, doc.filename, doc.parsed_md_path)
        loop = asyncio.get_running_loop()

        # Emit initial parsing progress if page count can be pre-inspected
        try:
            import pypdfium2

            pdf_doc = pypdfium2.PdfDocument(pdf_path)
            total_pages = len(pdf_doc)
            pdf_doc.close()
            await event_manager.broadcast(
                job_id,
                "parsing_progress",
                {
                    "completed": 0,
                    "current": 1,
                    "total": total_pages,
                    "message": f"processing page 1 of {total_pages}",
                },
            )
        except Exception:
            pass

        def on_docling_progress(completed: int, total: int) -> None:
            current = min(completed + 1, total) if completed < total else total
            asyncio.run_coroutine_threadsafe(
                event_manager.broadcast(
                    job_id,
                    "parsing_progress",
                    {
                        "completed": completed,
                        "current": current,
                        "total": total,
                        "message": f"processing page {current} of {total}",
                    },
                ),
                loop,
            )

        markdown_text, doc_hash = await parse_pdf(
            pdf_path, sha256_hash=doc.sha256, progress_callback=on_docling_progress
        )
        with Session(engine) as session:
            d = session.exec(select(Document).where(Document.id == doc.id)).first()
            if d:
                cache_file = settings.resolved_data_dir / "parsed" / f"{doc_hash}.md"
                d.parsed_md_path = str(cache_file)
                session.commit()

        # -------------------------------------------------------------
        # Stage 3: Document Chunking
        # -------------------------------------------------------------
        chunks = split_document(
            markdown_text,
            max_chars=job.chunk_size or settings.chunk_max_chars,
            overlap_chars=settings.chunk_overlap_chars,
        )
        total_chunks = len(chunks)

        with Session(engine) as session:
            j = session.exec(select(Job).where(Job.id == job_id)).first()
            if j:
                j.chunks_total = total_chunks
                j.status = "extracting"
                j.updated_at = utc_now()
                session.commit()
        await event_manager.broadcast(job_id, "status", {"stage": "extracting"})

        # -------------------------------------------------------------
        # Stage 4: Extraction per Chunk (with Checkpoint Resume)
        # -------------------------------------------------------------
        with Session(engine) as session:
            existing_results = session.exec(
                select(ChunkResult).where(ChunkResult.job_id == job_id)
            ).all()
            completed_map: dict[int, Any] = {c.chunk_index: c.get_data() for c in existing_results}

        for i, chunk_text in enumerate(chunks):
            if await job_queue.is_cancelled(job_id):
                with Session(engine) as session:
                    j = session.exec(select(Job).where(Job.id == job_id)).first()
                    if j:
                        j.status = "cancelled"
                        session.commit()
                await event_manager.broadcast(job_id, "status", {"stage": "cancelled"})
                return

            # Checkpoint resumption: skip chunk if already completed
            if i in completed_map:
                logger.info(
                    "Job %s: Chunk %d/%d already saved in checkpoint, skipping.",
                    job_id,
                    i + 1,
                    total_chunks,
                )
                continue

            # Emit in_progress SSE chunk event
            await event_manager.broadcast(
                job_id,
                "chunk",
                {
                    "index": i,
                    "total": total_chunks,
                    "status": "in_progress",
                    "attempts": 1,
                    "duration_ms": 0,
                    "duration_sec": 0,
                    "result": None,
                },
            )

            start_t = time.perf_counter()
            chunk_result = await process_single_chunk(
                client=client,
                model=active_model,
                tree=tree,
                json_schema=json_schema,
                pydantic_model=pydantic_model,
                chunk_text=chunk_text,
                chunk_index=i,
                total_chunks=total_chunks,
            )
            duration_ms = int((time.perf_counter() - start_t) * 1000)
            duration_sec = round(duration_ms / 1000, 2)

            # Save checkpoint to database
            with Session(engine) as session:
                checkpoint = ChunkResult(
                    job_id=job_id,
                    chunk_index=i,
                    result_json=json.dumps(chunk_result, ensure_ascii=False),
                    attempts=1,
                    duration_ms=duration_ms,
                )
                session.add(checkpoint)

                j = session.exec(select(Job).where(Job.id == job_id)).first()
                if j:
                    j.chunks_done += 1
                    j.updated_at = utc_now()
                session.commit()

            completed_map[i] = chunk_result

            # Emit SSE chunk event
            await event_manager.broadcast(
                job_id,
                "chunk",
                {
                    "index": i,
                    "total": total_chunks,
                    "status": "saved",
                    "attempts": 1,
                    "duration_ms": duration_ms,
                    "duration_sec": duration_sec,
                    "result": chunk_result,
                },
            )

            # Compute and emit live partial merged result
            ordered_results = [completed_map[k] for k in sorted(completed_map.keys())]
            partial_merged = merge_results(ordered_results, tree)
            await event_manager.broadcast(job_id, "partial", {"merged": partial_merged})

        # -------------------------------------------------------------
        # Stage 5: Final Merge
        # -------------------------------------------------------------
        with Session(engine) as session:
            j = session.exec(select(Job).where(Job.id == job_id)).first()
            if j:
                j.status = "merging"
                j.updated_at = utc_now()
                session.commit()
        await event_manager.broadcast(job_id, "status", {"stage": "merging"})

        all_results = [completed_map[k] for k in sorted(completed_map.keys())]
        final_result = merge_results(all_results, tree)

        with Session(engine) as session:
            j = session.exec(select(Job).where(Job.id == job_id)).first()
            if j:
                j.status = "done"
                j.set_result(final_result)
                j.updated_at = utc_now()
                session.commit()

        await event_manager.broadcast(job_id, "done", {"result": final_result})
        logger.info(f"Job {job_id} successfully completed!")

    except Exception as e:
        logger.exception(f"Job {job_id} failed: {e}")
        with Session(engine) as session:
            j = session.exec(select(Job).where(Job.id == job_id)).first()
            if j:
                j.status = "failed"
                j.error = str(e)
                j.updated_at = utc_now()
                session.commit()
        await event_manager.broadcast(job_id, "error", {"message": str(e)})


async def worker_loop() -> None:
    """Continuous worker loop reading job IDs from the queue."""
    logger.info("Starting background job worker loop...")

    # Crash-recovery: re-enqueue any pending or in-flight jobs from DB
    try:
        with Session(engine) as session:
            in_flight = session.exec(
                select(Job).where(
                    Job.status.in_(  # type: ignore[attr-defined]
                        ["queued", "inferring_shape", "parsing", "extracting", "merging"]
                    )
                )
            ).all()
            for j in in_flight:
                logger.info(f"Recovering interrupted job {j.id} (status: {j.status}) on startup")
                await job_queue.enqueue(j.id)
    except Exception as e:
        logger.warning(f"Error during worker startup job recovery: {e}")

    while not _stop_event.is_set():
        try:
            job_id = await job_queue.get_next()
            try:
                await execute_job(job_id)
            finally:
                job_queue.task_done()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Unexpected error in worker loop: {e}")


def start_worker() -> None:
    """Launches the background worker task."""
    global _worker_task
    _stop_event.clear()
    _worker_task = asyncio.create_task(worker_loop())


async def stop_worker() -> None:
    """Gracefully shuts down the background worker task."""
    global _worker_task
    _stop_event.set()
    if _worker_task:
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
        _worker_task = None

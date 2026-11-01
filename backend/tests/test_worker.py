import json
from unittest.mock import AsyncMock, patch

import pytest
from sqlmodel import Session, select

from app.config import settings
from app.db.models import ChunkResult, Document, Job
from app.db.session import engine
from app.jobs.queue import job_queue
from app.jobs.worker import execute_job


@pytest.fixture
def test_doc():
    pdf_file = settings.resolved_data_dir / "uploads" / "sample.pdf"
    pdf_file.parent.mkdir(parents=True, exist_ok=True)
    pdf_file.write_bytes(b"%PDF-1.4 mock pdf content")

    with Session(engine) as session:
        doc = Document(filename="sample.pdf", sha256="test_sha_12345", size=2048)
        session.add(doc)
        session.commit()
        session.refresh(doc)
        doc_id = doc.id
    return doc_id


@pytest.mark.asyncio
async def test_worker_happy_path_mocked_llm(test_doc: str):
    # 1. Setup Job
    with Session(engine) as session:
        job = Job(
            document_id=test_doc,
            input_mode="shape",
            input_text="{ name: string, score: number }",
            model="mock-model",
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        job_id = job.id

    mock_markdown = "Sample chunk text for extraction."

    with (
        patch(
            "app.jobs.worker.parse_pdf",
            new=AsyncMock(return_value=(mock_markdown, "test_sha_12345")),
        ),
        patch(
            "app.jobs.worker.extract_chunk_json",
            new=AsyncMock(return_value={"name": "Alice", "score": 98.5}),
        ),
    ):
        await execute_job(job_id)

    with Session(engine) as session:
        completed_job = session.exec(select(Job).where(Job.id == job_id)).first()
        assert completed_job is not None
        assert completed_job.status == "done"
        assert completed_job.get_result() == {"name": "Alice", "score": 98.5}

        # Checkpoints saved
        chunks = session.exec(select(ChunkResult).where(ChunkResult.job_id == job_id)).all()
        assert len(chunks) >= 1
        assert chunks[0].get_data() == {"name": "Alice", "score": 98.5}


@pytest.mark.asyncio
async def test_worker_cancellation(test_doc: str):
    with Session(engine) as session:
        job = Job(
            document_id=test_doc,
            input_mode="shape",
            input_text="{ item: string }",
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        job_id = job.id

    await job_queue.cancel(job_id)
    await execute_job(job_id)

    with Session(engine) as session:
        cancelled_job = session.exec(select(Job).where(Job.id == job_id)).first()
        assert cancelled_job is not None
        assert cancelled_job.status == "cancelled"


@pytest.mark.asyncio
async def test_worker_crash_resume_checkpoint(test_doc: str):
    """Proves that worker resumes from saved checkpoints without re-processing completed chunks."""
    with Session(engine) as session:
        job = Job(
            document_id=test_doc,
            input_mode="shape",
            input_text="{ items: [string] }",
            model="mock-model",
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        job_id = job.id

        # Simulate pre-existing saved checkpoint for chunk 0
        cp0 = ChunkResult(
            job_id=job_id,
            chunk_index=0,
            result_json=json.dumps({"items": ["Apple", "Banana"]}),
            duration_ms=100,
        )
        session.add(cp0)
        session.commit()

    # Markdown with 2 paragraphs that force 2 chunks
    mock_md = "Para 1 text.\n\nPara 2 text."

    mock_extract = AsyncMock(return_value={"items": ["Cherry"]})

    with (
        patch("app.jobs.worker.parse_pdf", new=AsyncMock(return_value=(mock_md, "test_sha_12345"))),
        patch("app.jobs.worker.split_document", return_value=["Para 1 text.", "Para 2 text."]),
        patch("app.jobs.worker.extract_chunk_json", mock_extract),
    ):
        await execute_job(job_id)

    # Verify that extract_chunk_json was called ONLY ONCE (for chunk 1, chunk 0 was skipped!)
    assert mock_extract.call_count == 1

    with Session(engine) as session:
        resumed_job = session.exec(select(Job).where(Job.id == job_id)).first()
        assert resumed_job is not None
        assert resumed_job.status == "done"
        final_res = resumed_job.get_result()
        # Both chunk 0 (Apple, Banana) and chunk 1 (Cherry) are merged
        assert set(final_res["items"]) == {"Apple", "Banana", "Cherry"}


@pytest.mark.asyncio
async def test_worker_error_handling(test_doc: str):
    with Session(engine) as session:
        job = Job(
            document_id=test_doc,
            input_mode="shape",
            input_text="{ name: string }",
            model="mock-model",
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        job_id = job.id

    with patch("app.jobs.worker.parse_pdf", side_effect=RuntimeError("Docling parsing crashed")):
        await execute_job(job_id)

    with Session(engine) as session:
        failed_job = session.exec(select(Job).where(Job.id == job_id)).first()
        assert failed_job is not None
        assert failed_job.status == "failed"
        assert "Docling parsing crashed" in (failed_job.error or "")

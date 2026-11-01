import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from app.db.models import ChunkResult, Document, Feedback, Job


@pytest.fixture
def memory_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_db_happy_path(memory_db: Session):
    # 1. Create document
    doc = Document(
        filename="report.pdf",
        sha256="abc123sha256",
        size=1024,
    )
    memory_db.add(doc)
    memory_db.commit()
    memory_db.refresh(doc)

    assert doc.id is not None
    assert doc.sha256 == "abc123sha256"

    # 2. Create job
    job = Job(
        document_id=doc.id,
        input_mode="shape",
        input_text="{ name: string }",
        model="test-model",
    )
    job.set_result({"name": "Extracted Result"})
    memory_db.add(job)
    memory_db.commit()
    memory_db.refresh(job)

    assert job.status == "queued"
    assert job.get_result() == {"name": "Extracted Result"}

    # 3. Create ChunkResult checkpoint
    chunk_res = ChunkResult(
        job_id=job.id,
        chunk_index=0,
        result_json='{"name": "Alice"}',
        attempts=1,
        duration_ms=120,
    )
    memory_db.add(chunk_res)
    memory_db.commit()

    # 4. Create Feedback
    fb = Feedback(
        job_id=job.id,
        rating=5,
        comment="Great extraction",
    )
    fb.set_tags(["Accurate", "Fast"])
    memory_db.add(fb)
    memory_db.commit()

    # Query back
    queried_job = memory_db.exec(select(Job).where(Job.id == job.id)).first()
    assert queried_job is not None
    assert queried_job.get_result() == {"name": "Extracted Result"}


def test_db_edge_case_unicode_inputs(memory_db: Session):
    unicode_filename = "résumé_日本語_🚀.pdf"
    doc = Document(
        filename=unicode_filename,
        sha256="hash_unicode_123",
        size=5000,
    )
    memory_db.add(doc)
    memory_db.commit()

    queried = memory_db.exec(select(Document).where(Document.filename == unicode_filename)).first()
    assert queried is not None
    assert queried.filename == unicode_filename


def test_db_edge_case_oversized_json(memory_db: Session):
    doc = Document(filename="test.pdf", sha256="h1", size=100)
    memory_db.add(doc)
    memory_db.commit()

    large_dict = {f"key_{i}": f"value_string_item_{i}" for i in range(2000)}
    job = Job(
        document_id=doc.id,
        input_text="{ data: string }",
    )
    job.set_result(large_dict)
    memory_db.add(job)
    memory_db.commit()

    queried = memory_db.exec(select(Job).where(Job.id == job.id)).first()
    assert queried is not None
    res = queried.get_result()
    assert len(res) == 2000
    assert res["key_100"] == "value_string_item_100"


def test_db_edge_case_empty_and_corrupt_tags(memory_db: Session):
    fb = Feedback(rating=1, tags_json="invalid_json{")
    memory_db.add(fb)
    memory_db.commit()

    # get_tags handles invalid JSON gracefully
    assert fb.get_tags() == []

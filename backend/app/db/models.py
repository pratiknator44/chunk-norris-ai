"""Database models for DocExtract using SQLModel."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(UTC)


class Document(SQLModel, table=True):
    __tablename__ = "documents"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True)
    filename: str
    sha256: str = Field(index=True)
    size: int
    parsed_md_path: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class Job(SQLModel, table=True):
    __tablename__ = "jobs"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True)
    document_id: str = Field(foreign_key="documents.id", index=True)
    input_mode: str = Field(default="auto")  # "shape" | "natural_language" | "auto"
    input_text: str
    resolved_shape: str | None = None  # JSON snapshot of ShapeTree
    model: str = Field(default="")
    chunk_size: int = Field(default=8000)
    status: str = Field(default="queued", index=True)
    chunks_done: int = Field(default=0)
    chunks_total: int = Field(default=0)
    error: str | None = None
    result_json: str | None = None  # JSON string of final output
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def get_result(self) -> Any:
        if self.result_json:
            return json.loads(self.result_json)
        return None

    def set_result(self, data: Any) -> None:
        self.result_json = json.dumps(data, ensure_ascii=False)


class ChunkResult(SQLModel, table=True):
    __tablename__ = "chunk_results"

    id: int | None = Field(default=None, primary_key=True)
    job_id: str = Field(foreign_key="jobs.id", index=True)
    chunk_index: int = Field(index=True)
    result_json: str  # Checkpoint: JSON string of extracted chunk data
    attempts: int = Field(default=1)
    duration_ms: int = Field(default=0)
    created_at: datetime = Field(default_factory=utc_now)

    def get_data(self) -> Any:
        return json.loads(self.result_json)

    def set_data(self, data: Any) -> None:
        self.result_json = json.dumps(data, ensure_ascii=False)


class Feedback(SQLModel, table=True):
    __tablename__ = "feedback"

    id: int | None = Field(default=None, primary_key=True)
    job_id: str | None = Field(default=None, index=True)
    rating: int  # 1-5 or thumbs
    tags_json: str = Field(default="[]")
    comment: str | None = None
    email: str | None = None
    app_version: str = Field(default="0.1.0")
    created_at: datetime = Field(default_factory=utc_now)

    def get_tags(self) -> list[str]:
        try:
            parsed = json.loads(self.tags_json)
            if isinstance(parsed, list):
                return [str(t) for t in parsed]
            return []
        except Exception:
            return []

    def set_tags(self, tags: list[str]) -> None:
        self.tags_json = json.dumps(tags)

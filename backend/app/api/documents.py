"""Document upload and inspection endpoints."""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.config import settings
from app.core.parsing import compute_file_sha256
from app.db.models import Document
from app.db.session import get_session

router = APIRouter(prefix="/documents", tags=["documents"])

SessionDep = Annotated[Session, Depends(get_session)]


class DocumentUploadResponse(BaseModel):
    id: str
    filename: str
    sha256: str
    size: int


class MarkdownResponse(BaseModel):
    document_id: str
    sha256: str
    markdown: str


def _save_upload_file(file_obj: Any, target_path: Path) -> int:
    with open(target_path, "wb") as buffer:
        shutil.copyfileobj(file_obj, buffer)
    return target_path.stat().st_size


@router.post("", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile,
    session: SessionDep,
) -> DocumentUploadResponse:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported.",
        )

    uploads_dir = settings.resolved_data_dir / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    # Save to a temporary file in uploads to calculate hash
    temp_path = uploads_dir / f"tmp_{file.filename}"
    size = await asyncio.to_thread(_save_upload_file, file.file, temp_path)

    max_bytes = settings.max_upload_mb * 1024 * 1024
    if size > max_bytes:
        temp_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum upload size of {settings.max_upload_mb}MB.",
        )

    sha256 = compute_file_sha256(temp_path)

    # Check for existing document with identical content
    existing_doc = session.exec(select(Document).where(Document.sha256 == sha256)).first()
    if existing_doc:
        temp_path.unlink(missing_ok=True)
        return DocumentUploadResponse(
            id=existing_doc.id,
            filename=existing_doc.filename,
            sha256=existing_doc.sha256,
            size=existing_doc.size,
        )

    # Move to permanent path
    target_path = uploads_dir / file.filename
    # Avoid collision if different file has the same name
    if target_path.exists():
        target_path = uploads_dir / f"{sha256[:8]}_{file.filename}"

    shutil.move(temp_path, target_path)

    doc = Document(
        filename=target_path.name,
        sha256=sha256,
        size=size,
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)

    return DocumentUploadResponse(
        id=doc.id,
        filename=doc.filename,
        sha256=doc.sha256,
        size=doc.size,
    )


@router.get("/{document_id}/markdown", response_model=MarkdownResponse)
async def get_document_markdown(
    document_id: str,
    session: SessionDep,
) -> MarkdownResponse:
    doc = session.exec(select(Document).where(Document.id == document_id)).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found.",
        )

    cache_file = settings.resolved_data_dir / "parsed" / f"{doc.sha256}.md"
    if not cache_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document has not been parsed yet. Start an extraction job first.",
        )

    markdown = cache_file.read_text(encoding="utf-8")
    return MarkdownResponse(
        document_id=doc.id,
        sha256=doc.sha256,
        markdown=markdown,
    )

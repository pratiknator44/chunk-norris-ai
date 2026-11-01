"""Docling PDF parsing with content-hash SHA-256 caching for DocExtract."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


def compute_file_sha256(file_path: Path) -> str:
    """Computes SHA-256 hash of a file's contents."""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


def compute_bytes_sha256(data: bytes) -> str:
    """Computes SHA-256 hash of byte content."""
    return hashlib.sha256(data).hexdigest()


def _run_docling_sync(
    pdf_path: Path,
    progress_callback: Callable[[int, int], None] | None = None,
) -> str:
    """Synchronous CPU/GPU Docling converter call."""
    from docling.datamodel.progress import PageCompletedProgress
    from docling.document_converter import DocumentConverter

    def on_progress(event: Any) -> None:
        if progress_callback:
            completed = getattr(event, "completed_pages", None)
            total = getattr(event, "total_pages", None)
            if completed is not None and total is not None:
                progress_callback(int(completed), int(total))
            elif isinstance(event, PageCompletedProgress):
                progress_callback(event.completed_pages, event.total_pages)

    converter = DocumentConverter()
    conv_res = converter.convert(
        str(pdf_path),
        progress_callback=on_progress if progress_callback else None,
    )
    return conv_res.document.export_to_markdown()


def _parse_pdf_sync(
    pdf_path: Path,
    sha256_hash: str | None = None,
    use_cache: bool = True,
    progress_callback: Callable[[int, int], None] | None = None,
) -> tuple[str, str]:
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found at {pdf_path}")

    file_hash = sha256_hash or compute_file_sha256(pdf_path)

    cache_dir = settings.resolved_data_dir / "parsed"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{file_hash}.md"

    if use_cache and cache_file.exists():
        logger.info(f"Loaded cached Markdown for hash {file_hash}")
        cached_text = cache_file.read_text(encoding="utf-8")
        return cached_text, file_hash

    logger.info(f"Running Docling converter for {pdf_path.name} (hash: {file_hash})...")
    markdown_text = _run_docling_sync(pdf_path, progress_callback)

    if not markdown_text.strip():
        raise RuntimeError(f"Docling produced no text for {pdf_path.name}")

    cache_file.write_text(markdown_text, encoding="utf-8")
    logger.info(f"Saved parsed Markdown to {cache_file}")
    return markdown_text, file_hash


async def parse_pdf(
    pdf_path: Path,
    sha256_hash: str | None = None,
    use_cache: bool = True,
    progress_callback: Callable[[int, int], None] | None = None,
) -> tuple[str, str]:
    """Parses a PDF into Markdown using Docling in a thread pool, cached by SHA-256 hash."""
    return await asyncio.to_thread(
        _parse_pdf_sync, pdf_path, sha256_hash, use_cache, progress_callback
    )

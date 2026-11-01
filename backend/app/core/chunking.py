"""Paragraph-aware document chunking with overlap for DocExtract.

Splits document text into manageable chunks respecting paragraph and word boundaries,
with optional overlap to avoid splitting entities across chunk edges.
"""

from __future__ import annotations

import re


def _find_word_boundary(text: str, max_idx: int) -> int:
    """Finds the last space or newline before max_idx to avoid splitting words."""
    idx = text.rfind(" ", 0, max_idx)
    nl_idx = text.rfind("\n", 0, max_idx)
    boundary = max(idx, nl_idx)
    if boundary <= 0:
        return max_idx
    return boundary


def split_document(
    text: str,
    max_chars: int = 8000,
    overlap_chars: int = 200,
) -> list[str]:
    """Splits markdown/text into chunks respecting paragraph boundaries and max_chars limit.

    Args:
        text: The source text to split.
        max_chars: Maximum character length per chunk.
        overlap_chars: Number of trailing characters from the previous chunk to include in the next.

    Returns:
        A list of string chunks.
    """
    clean_text = text.strip()
    if not clean_text:
        return []

    if len(clean_text) <= max_chars:
        return [clean_text]

    # Split into paragraphs
    raw_paragraphs = re.split(r"\n\s*\n", clean_text)
    paragraphs: list[str] = []

    # Handle single paragraphs exceeding max_chars
    for para in raw_paragraphs:
        para = para.strip()
        if not para:
            continue

        while len(para) > max_chars:
            split_at = _find_word_boundary(para, max_chars)
            paragraphs.append(para[:split_at].strip())
            para = para[split_at:].strip()

        if para:
            paragraphs.append(para)

    chunks: list[str] = []
    current_chunk = ""

    for para in paragraphs:
        separator = "\n\n" if current_chunk else ""
        projected_len = len(current_chunk) + len(separator) + len(para)

        if projected_len > max_chars and current_chunk:
            # Finalize current chunk
            chunks.append(current_chunk)

            # Build overlap prefix from the end of current_chunk
            if overlap_chars > 0 and len(current_chunk) > overlap_chars:
                overlap_slice = current_chunk[-overlap_chars:]
                # Trim to leading word boundary in the slice
                first_space = overlap_slice.find(" ")
                if first_space != -1:
                    overlap_prefix = overlap_slice[first_space:].strip() + "\n\n"
                else:
                    overlap_prefix = overlap_slice.strip() + "\n\n"
                current_chunk = overlap_prefix + para
            else:
                current_chunk = para
        else:
            current_chunk = f"{current_chunk}{separator}{para}" if current_chunk else para

    if current_chunk:
        chunks.append(current_chunk)

    return chunks

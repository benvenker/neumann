from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Chroma Cloud maximum document size in bytes
CHROMA_CLOUD_DOC_MAX_BYTES = 16_384


def load_page_uris(pages_jsonl_path: Path) -> List[str]:
    """Load and return sorted page URIs from pages.jsonl.

    Reads pages.jsonl, extracts URIs sorted by page number, and returns a deduplicated list.
    Returns an empty list if the file is missing or unreadable.

    Args:
        pages_jsonl_path: Path to pages.jsonl file

    Returns:
        List of URIs sorted by page number, with duplicates removed
    """
    if not pages_jsonl_path.exists():
        return []

    uris: List[Tuple[int, str]] = []
    try:
        for line in pages_jsonl_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                page = int(row.get("page", 0))
                uri = str(row.get("uri", ""))
                if uri:
                    uris.append((page, uri))
            except (json.JSONDecodeError, ValueError, KeyError, TypeError):
                # Skip malformed JSONL rows
                continue
    except (OSError, IOError, UnicodeDecodeError):
        # File unreadable
        return []

    # Sort by page and dedupe preserving order
    uris.sort(key=lambda t: t[0] or 0)
    seen = set()
    out: List[str] = []
    for _, u in uris:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _split_line_by_bytes(s: str, max_bytes: int) -> List[str]:
    """Split a string into byte-safe chunks respecting UTF-8 character boundaries.

    Args:
        s: String to split
        max_bytes: Maximum bytes per chunk

    Returns:
        List of string chunks, each <= max_bytes when encoded as UTF-8
    """
    b = s.encode("utf-8")
    out: List[str] = []
    i = 0
    while i < len(b):
        j = min(len(b), i + max_bytes)
        # Back off if j lands in a UTF-8 continuation byte
        # UTF-8 continuation bytes start with 0b10xxxxxx
        while j > i and (b[j - 1] & 0b11000000) == 0b10000000:
            j -= 1
        out.append(b[i:j].decode("utf-8", errors="strict"))
        i = j
    return out


def chunk_file_by_lines(
    text: str,
    pages_jsonl_path: Path,
    per_chunk: int = 180,
    overlap: int = 30,
) -> List[Dict[str, Any]]:
    """Split text into overlapping line-based chunks with byte limit enforcement.

    Chunks the input text into overlapping windows of approximately `per_chunk` lines
    with `overlap` lines shared between consecutive chunks. Each chunk is guaranteed
    to be <= 16,384 bytes (Chroma Cloud limit). Attaches page URIs from pages.jsonl
    to each chunk's metadata.

    Args:
        text: Raw file contents as a string
        pages_jsonl_path: Path to pages/pages.jsonl for the source file's rendered output
        per_chunk: Desired lines per chunk (default 180)
        overlap: Number of overlapping lines with previous chunk (default 30)

    Returns:
        List of chunk dicts, each containing:
        - text: str - raw text of the chunk (with original newline characters preserved)
        - line_start: int - 1-indexed inclusive start line for this chunk
        - line_end: int - 1-indexed inclusive end line for this chunk
        - page_uris: List[str] - ordered list of page image URIs for the document

    Raises:
        ValueError: If per_chunk <= 0, overlap < 0, or overlap >= per_chunk

    Example:
        >>> from pathlib import Path
        >>> chunks = chunk_file_by_lines("line1\\nline2\\n", Path("pages.jsonl"), per_chunk=2, overlap=1)
        >>> chunks[0]["line_start"]
        1
        >>> chunks[0]["line_end"]
        2
    """
    # Validate parameters
    if per_chunk <= 0:
        raise ValueError("per_chunk must be positive")
    if overlap < 0:
        raise ValueError("overlap must be non-negative")
    if overlap >= per_chunk:
        raise ValueError("overlap must be less than per_chunk")

    # Load page URIs (gracefully handle missing/invalid files)
    page_uris = load_page_uris(pages_jsonl_path)

    # Split to lines with newline retention
    lines = text.splitlines(keepends=True)
    n = len(lines)
    if n == 0:
        return []

    chunks: List[Dict[str, Any]] = []
    start = 0

    while start < n:
        end = min(n, start + per_chunk)

        # Enforce byte limit (greedy shrink)
        chunk_text = "".join(lines[start:end])
        while len(chunk_text.encode("utf-8")) > CHROMA_CLOUD_DOC_MAX_BYTES and end > start + 1:
            end -= 1
            chunk_text = "".join(lines[start:end])

        # If single line still exceeds limit after shrink, split it
        if len(chunk_text.encode("utf-8")) > CHROMA_CLOUD_DOC_MAX_BYTES and end == start + 1:
            for seg in _split_line_by_bytes(lines[start], CHROMA_CLOUD_DOC_MAX_BYTES):
                chunks.append(
                    {
                        "text": seg,
                        "line_start": start + 1,
                        "line_end": start + 1,
                        "page_uris": page_uris,
                    }
                )
            start += 1
            continue

        # Emit chunk
        chunks.append(
            {
                "text": chunk_text,
                "line_start": start + 1,
                "line_end": end,
                "page_uris": page_uris,
            }
        )

        # If we've reached the end of the file, stop
        if end >= n:
            break

        # Compute step; if the chunk had fewer lines than requested due to byte limits,
        # step by actual_chunk_len - overlap (minimum 1) to prevent skipping or infinite loops
        actual_len = end - start
        step = max(1, actual_len - overlap)
        start = start + step

    return chunks


__all__ = ["chunk_file_by_lines", "load_page_uris", "CHROMA_CLOUD_DOC_MAX_BYTES"]


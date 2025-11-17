import json
from pathlib import Path

import pytest

from chunker import CHROMA_CLOUD_DOC_MAX_BYTES, chunk_file_by_lines, load_page_uris


def test_load_page_uris_missing_file():
    """Test load_page_uris returns [] for missing file."""
    missing_path = Path("/nonexistent/pages.jsonl")
    assert load_page_uris(missing_path) == []


def test_load_page_uris_empty_file(tmp_path: Path):
    """Test load_page_uris returns [] for empty file."""
    jsonl_path = tmp_path / "pages.jsonl"
    jsonl_path.write_text("", encoding="utf-8")
    assert load_page_uris(jsonl_path) == []


def test_load_page_uris_valid_sorted(tmp_path: Path):
    """Test load_page_uris reads and sorts URIs by page number."""
    jsonl_path = tmp_path / "pages.jsonl"
    # Write pages in reverse order
    records = [
        {"doc_id": "test", "page": 3, "uri": "http://example.com/p3.webp"},
        {"doc_id": "test", "page": 1, "uri": "http://example.com/p1.webp"},
        {"doc_id": "test", "page": 2, "uri": "http://example.com/p2.webp"},
    ]
    with jsonl_path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")

    uris = load_page_uris(jsonl_path)
    assert uris == [
        "http://example.com/p1.webp",
        "http://example.com/p2.webp",
        "http://example.com/p3.webp",
    ]


def test_load_page_uris_deduplicates(tmp_path: Path):
    """Test load_page_uris removes duplicate URIs."""
    jsonl_path = tmp_path / "pages.jsonl"
    records = [
        {"doc_id": "test", "page": 1, "uri": "http://example.com/p1.webp"},
        {"doc_id": "test", "page": 2, "uri": "http://example.com/p1.webp"},  # duplicate
        {"doc_id": "test", "page": 3, "uri": "http://example.com/p2.webp"},
    ]
    with jsonl_path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")

    uris = load_page_uris(jsonl_path)
    assert uris == [
        "http://example.com/p1.webp",
        "http://example.com/p2.webp",
    ]


def test_load_page_uris_skips_malformed_rows(tmp_path: Path):
    """Test load_page_uris skips malformed JSONL rows."""
    jsonl_path = tmp_path / "pages.jsonl"
    content = """{"doc_id": "test", "page": 1, "uri": "http://example.com/p1.webp"}
not json
{"doc_id": "test", "page": 2, "uri": "http://example.com/p2.webp"}
{"invalid": "missing page"}
"""
    jsonl_path.write_text(content, encoding="utf-8")

    uris = load_page_uris(jsonl_path)
    assert uris == [
        "http://example.com/p1.webp",
        "http://example.com/p2.webp",
    ]


def test_chunk_basic_file(tmp_path: Path):
    """Test chunking a basic file into expected chunks."""
    # Create a simple pages.jsonl
    jsonl_path = tmp_path / "pages.jsonl"
    jsonl_path.write_text(
        '{"doc_id": "test", "page": 1, "uri": "http://example.com/p1.webp"}\n',
        encoding="utf-8",
    )

    # Create text with 200 lines (will create chunks with overlap)
    lines = [f"Line {i}\n" for i in range(1, 201)]
    text = "".join(lines)

    chunks = chunk_file_by_lines(text, jsonl_path, per_chunk=100, overlap=20)
    # With 200 lines, per_chunk=100, overlap=20: chunk 1 (1-100), chunk 2 (81-180), chunk 3 (161-200)
    assert len(chunks) == 3

    # First chunk: lines 1-100
    assert chunks[0]["line_start"] == 1
    assert chunks[0]["line_end"] == 100
    assert chunks[0]["text"].count("\n") == 100
    assert chunks[0]["page_uris"] == ["http://example.com/p1.webp"]

    # Second chunk: lines 81-180 (20 line overlap from previous)
    assert chunks[1]["line_start"] == 81  # 100 - 20 + 1
    assert chunks[1]["line_end"] == 180
    assert chunks[1]["text"].count("\n") == 100
    assert chunks[1]["page_uris"] == ["http://example.com/p1.webp"]

    # Third chunk: lines 161-200 (20 line overlap from previous)
    assert chunks[2]["line_start"] == 161
    assert chunks[2]["line_end"] == 200
    assert chunks[2]["text"].count("\n") == 40
    assert chunks[2]["page_uris"] == ["http://example.com/p1.webp"]


def test_chunk_with_overlap(tmp_path: Path):
    """Test that overlap is correctly applied between chunks."""
    jsonl_path = tmp_path / "pages.jsonl"
    jsonl_path.write_text('{"doc_id": "test", "page": 1, "uri": "http://example.com/p1.webp"}\n', encoding="utf-8")

    # Create text with exactly 200 lines
    lines = [f"Line {i}\n" for i in range(1, 201)]
    text = "".join(lines)

    chunks = chunk_file_by_lines(text, jsonl_path, per_chunk=100, overlap=30)

    # With 200 lines, per_chunk=100, overlap=30: chunk 1 (1-100), chunk 2 (71-170), chunk 3 (141-200)
    assert len(chunks) == 3

    # First chunk: lines 1-100
    first_chunk_lines = chunks[0]["text"].splitlines(keepends=True)
    assert len(first_chunk_lines) == 100

    # Second chunk should start at line 71 (100 - 30 + 1)
    assert chunks[1]["line_start"] == 71
    assert chunks[1]["line_end"] == 170
    # Verify overlap by checking first 30 lines of second chunk match last 30 of first
    second_chunk_lines = chunks[1]["text"].splitlines(keepends=True)
    assert second_chunk_lines[:30] == first_chunk_lines[-30:]

    # Third chunk should start at line 141 (170 - 30 + 1)
    assert chunks[2]["line_start"] == 141
    assert chunks[2]["line_end"] == 200


def test_chunk_respects_16kb_limit(tmp_path: Path):
    """Test that chunks are enforced to be <= 16KB."""
    jsonl_path = tmp_path / "pages.jsonl"
    jsonl_path.write_text('{"doc_id": "test", "page": 1, "uri": "http://example.com/p1.webp"}\n', encoding="utf-8")

    # Create text with many lines that would exceed 16KB if all included
    # Each line is ~100 bytes, so 200 lines = ~20KB
    lines = [f"{'x' * 95}\n" for _ in range(200)]
    text = "".join(lines)

    chunks = chunk_file_by_lines(text, jsonl_path, per_chunk=200, overlap=20)

    # Verify all chunks are <= 16KB
    for chunk in chunks:
        chunk_bytes = len(chunk["text"].encode("utf-8"))
        assert chunk_bytes <= CHROMA_CLOUD_DOC_MAX_BYTES, (
            f"Chunk {chunk['line_start']}-{chunk['line_end']} exceeds limit"
        )


def test_page_uris_attached(tmp_path: Path):
    """Test that page_uris from pages.jsonl are attached to each chunk."""
    jsonl_path = tmp_path / "pages.jsonl"
    records = [
        {"doc_id": "test", "page": 1, "uri": "http://example.com/p1.webp"},
        {"doc_id": "test", "page": 2, "uri": "http://example.com/p2.webp"},
    ]
    with jsonl_path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")

    text = "line 1\nline 2\n"
    chunks = chunk_file_by_lines(text, jsonl_path, per_chunk=2, overlap=0)

    assert len(chunks) == 1
    assert chunks[0]["page_uris"] == [
        "http://example.com/p1.webp",
        "http://example.com/p2.webp",
    ]


def test_file_smaller_than_chunk_size(tmp_path: Path):
    """Test chunking a file smaller than per_chunk returns single chunk."""
    jsonl_path = tmp_path / "pages.jsonl"
    jsonl_path.write_text('{"doc_id": "test", "page": 1, "uri": "http://example.com/p1.webp"}\n', encoding="utf-8")

    # 5 lines, chunk size 100
    text = "line 1\nline 2\nline 3\nline 4\nline 5\n"
    chunks = chunk_file_by_lines(text, jsonl_path, per_chunk=100, overlap=20)

    assert len(chunks) == 1
    assert chunks[0]["line_start"] == 1
    assert chunks[0]["line_end"] == 5
    assert chunks[0]["text"] == text


def test_empty_file(tmp_path: Path):
    """Test chunking empty file returns empty list."""
    jsonl_path = tmp_path / "pages.jsonl"
    jsonl_path.write_text('{"doc_id": "test", "page": 1, "uri": "http://example.com/p1.webp"}\n', encoding="utf-8")

    chunks = chunk_file_by_lines("", jsonl_path)
    assert chunks == []


def test_chunk_with_zero_overlap(tmp_path: Path):
    """Test chunking with zero overlap (contiguous chunks)."""
    jsonl_path = tmp_path / "pages.jsonl"
    jsonl_path.write_text('{"doc_id": "test", "page": 1, "uri": "http://example.com/p1.webp"}\n', encoding="utf-8")

    lines = [f"line {i}\n" for i in range(1, 51)]
    text = "".join(lines)

    chunks = chunk_file_by_lines(text, jsonl_path, per_chunk=20, overlap=0)

    assert len(chunks) == 3  # 20, 20, 10 lines
    assert chunks[0]["line_end"] == 20
    assert chunks[1]["line_start"] == 21  # No overlap
    assert chunks[1]["line_end"] == 40
    assert chunks[2]["line_start"] == 41
    assert chunks[2]["line_end"] == 50


def test_chunk_parameter_validation():
    """Test that invalid parameters raise ValueError."""
    jsonl_path = Path("/tmp/test.jsonl")

    # per_chunk <= 0
    with pytest.raises(ValueError, match="per_chunk must be positive"):
        chunk_file_by_lines("test", jsonl_path, per_chunk=0)

    with pytest.raises(ValueError, match="per_chunk must be positive"):
        chunk_file_by_lines("test", jsonl_path, per_chunk=-1)

    # overlap < 0
    with pytest.raises(ValueError, match="overlap must be non-negative"):
        chunk_file_by_lines("test", jsonl_path, per_chunk=100, overlap=-1)

    # overlap >= per_chunk
    with pytest.raises(ValueError, match="overlap must be less than per_chunk"):
        chunk_file_by_lines("test", jsonl_path, per_chunk=100, overlap=100)

    with pytest.raises(ValueError, match="overlap must be less than per_chunk"):
        chunk_file_by_lines("test", jsonl_path, per_chunk=100, overlap=150)


def test_chunk_very_long_line(tmp_path: Path):
    """Test that a single line exceeding 16KB is split into multiple chunks."""
    jsonl_path = tmp_path / "pages.jsonl"
    jsonl_path.write_text('{"doc_id": "test", "page": 1, "uri": "http://example.com/p1.webp"}\n', encoding="utf-8")

    # Create a line that's > 16KB
    long_line = "x" * (CHROMA_CLOUD_DOC_MAX_BYTES + 1000) + "\n"
    text = long_line

    chunks = chunk_file_by_lines(text, jsonl_path, per_chunk=180, overlap=30)

    # Should create multiple chunks for this single line
    assert len(chunks) > 1

    # All chunks should have same line_start and line_end (it's one logical line)
    for chunk in chunks:
        assert chunk["line_start"] == 1
        assert chunk["line_end"] == 1
        # Each chunk should be <= 16KB
        chunk_bytes = len(chunk["text"].encode("utf-8"))
        assert chunk_bytes <= CHROMA_CLOUD_DOC_MAX_BYTES


def test_chunk_newline_preservation(tmp_path: Path):
    """Test that original newline characters are preserved."""
    jsonl_path = tmp_path / "pages.jsonl"
    jsonl_path.write_text('{"doc_id": "test", "page": 1, "uri": "http://example.com/p1.webp"}\n', encoding="utf-8")

    # Mix of different line endings
    text = "line 1\nline 2\r\nline 3\n"
    chunks = chunk_file_by_lines(text, jsonl_path, per_chunk=10, overlap=0)

    assert len(chunks) == 1
    # Verify newlines are preserved
    assert "\r\n" in chunks[0]["text"]
    assert chunks[0]["text"] == text


def test_chunk_line_numbers_one_indexed(tmp_path: Path):
    """Test that line_start and line_end are 1-indexed."""
    jsonl_path = tmp_path / "pages.jsonl"
    jsonl_path.write_text('{"doc_id": "test", "page": 1, "uri": "http://example.com/p1.webp"}\n', encoding="utf-8")

    text = "line 1\nline 2\nline 3\n"
    chunks = chunk_file_by_lines(text, jsonl_path, per_chunk=2, overlap=0)

    assert len(chunks) == 2
    assert chunks[0]["line_start"] == 1  # 1-indexed, not 0
    assert chunks[0]["line_end"] == 2
    assert chunks[1]["line_start"] == 3
    assert chunks[1]["line_end"] == 3


def test_chunk_missing_pages_jsonl(tmp_path: Path):
    """Test that chunking works even when pages.jsonl is missing."""
    missing_jsonl = tmp_path / "nonexistent.jsonl"

    text = "line 1\nline 2\n"
    chunks = chunk_file_by_lines(text, missing_jsonl, per_chunk=10, overlap=0)

    assert len(chunks) == 1
    assert chunks[0]["page_uris"] == []  # Should be empty, not raise error


def test_chunk_dynamic_step_size_for_byte_limited_chunks(tmp_path: Path):
    """Test that chunks that shrink due to byte limits still advance correctly."""
    jsonl_path = tmp_path / "pages.jsonl"
    jsonl_path.write_text('{"doc_id": "test", "page": 1, "uri": "http://example.com/p1.webp"}\n', encoding="utf-8")

    # Create lines where a chunk of 100 lines would exceed 16KB, forcing shrink
    # Each line ~200 bytes, so ~50 lines max per chunk
    lines = [f"{'x' * 195}\n" for _ in range(200)]
    text = "".join(lines)

    chunks = chunk_file_by_lines(text, jsonl_path, per_chunk=100, overlap=20)

    # Should create multiple chunks
    assert len(chunks) > 1

    # Verify no gaps between chunks (each chunk should start where previous ended - overlap + 1)
    for i in range(1, len(chunks)):
        prev_end = chunks[i - 1]["line_end"]
        current_start = chunks[i]["line_start"]
        overlap_size = 20
        expected_start = max(1, prev_end - overlap_size + 1)
        assert current_start <= expected_start, f"Gap detected between chunks {i - 1} and {i}"


def test_load_page_uris_with_missing_uri_field(tmp_path: Path):
    """Test load_page_uris handles rows missing uri field."""
    jsonl_path = tmp_path / "pages.jsonl"
    records = [
        {"doc_id": "test", "page": 1, "uri": "http://example.com/p1.webp"},
        {"doc_id": "test", "page": 2},  # missing uri
        {"doc_id": "test", "page": 3, "uri": "http://example.com/p3.webp"},
    ]
    with jsonl_path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")

    uris = load_page_uris(jsonl_path)
    assert uris == [
        "http://example.com/p1.webp",
        "http://example.com/p3.webp",
    ]


def test_load_page_uris_with_empty_uri(tmp_path: Path):
    """Test load_page_uris skips rows with empty uri."""
    jsonl_path = tmp_path / "pages.jsonl"
    records = [
        {"doc_id": "test", "page": 1, "uri": "http://example.com/p1.webp"},
        {"doc_id": "test", "page": 2, "uri": ""},  # empty uri
        {"doc_id": "test", "page": 3, "uri": "http://example.com/p3.webp"},
    ]
    with jsonl_path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")

    uris = load_page_uris(jsonl_path)
    assert uris == [
        "http://example.com/p1.webp",
        "http://example.com/p3.webp",
    ]


def test_small_file_over_16kb_chunked_fully(tmp_path: Path):
    """Test that a file with n ≤ per_chunk but total bytes > 16KB is fully chunked without data loss.

    This addresses the bug where the special-case branch would shrink the file and
    return early with incorrect line_end metadata, dropping the remainder of the file.
    """
    jsonl_path = tmp_path / "pages.jsonl"
    jsonl_path.write_text('{"doc_id": "test", "page": 1, "uri": "http://example.com/p1.webp"}\n', encoding="utf-8")

    # Create 200 lines, each ~100 bytes -> ~20KB total
    # per_chunk=200 means file is smaller than chunk size, but exceeds 16KB
    lines = [f"{'x' * 95}\n" for _ in range(200)]
    text = "".join(lines)

    chunks = chunk_file_by_lines(text, jsonl_path, per_chunk=200, overlap=0)

    # Should create multiple chunks to cover all lines (not truncated)
    assert len(chunks) > 1, "Small file exceeding 16KB should be split into multiple chunks"

    # Verify all chunks are within byte limit
    for chunk in chunks:
        chunk_bytes = len(chunk["text"].encode("utf-8"))
        assert chunk_bytes <= CHROMA_CLOUD_DOC_MAX_BYTES, f"Chunk exceeds 16KB limit: {chunk_bytes} bytes"

    # Verify all lines are covered (no data loss)
    covered_lines = set()
    for chunk in chunks:
        for line_num in range(chunk["line_start"], chunk["line_end"] + 1):
            covered_lines.add(line_num)

    # All lines 1..200 should be covered
    assert covered_lines == set(range(1, 201)), "Not all lines covered - data loss detected"


def test_multiline_with_first_line_very_long(tmp_path: Path):
    """Test that a multi-line file with the first line > 16KB splits that line properly.

    This verifies that long single lines are handled correctly even when they appear
    in multi-line files, not just as standalone single-line files.
    """
    jsonl_path = tmp_path / "pages.jsonl"
    jsonl_path.write_text('{"doc_id": "test", "page": 1, "uri": "http://example.com/p1.webp"}\n', encoding="utf-8")

    # First line exceeds 16KB, followed by short lines
    long_line = "x" * (CHROMA_CLOUD_DOC_MAX_BYTES + 1000) + "\n"
    short_lines = "".join([f"short line {i}\n" for i in range(1, 11)])
    text = long_line + short_lines

    chunks = chunk_file_by_lines(text, jsonl_path, per_chunk=180, overlap=30)

    # Should create multiple chunks
    assert len(chunks) > 1

    # Find chunks for line 1 (the long line)
    line_1_chunks = [c for c in chunks if c["line_start"] == 1 and c["line_end"] == 1]
    assert len(line_1_chunks) > 1, "Long first line should be split into multiple chunks"

    # All line 1 chunks should be within byte limit
    for chunk in line_1_chunks:
        chunk_bytes = len(chunk["text"].encode("utf-8"))
        assert chunk_bytes <= CHROMA_CLOUD_DOC_MAX_BYTES, f"Line 1 chunk exceeds limit: {chunk_bytes} bytes"

    # Subsequent chunks should cover lines 2+ (the short lines)
    subsequent_chunks = [c for c in chunks if c["line_start"] >= 2]
    assert len(subsequent_chunks) > 0, "Short lines after long line should be chunked normally"

    # Verify all subsequent chunks start at line 2 or later
    for chunk in subsequent_chunks:
        assert chunk["line_start"] >= 2, f"Unexpected line_start: {chunk['line_start']}"

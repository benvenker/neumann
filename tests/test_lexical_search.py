from pathlib import Path

import pytest

from indexer import get_client, lexical_search, upsert_code_chunks


def test_empty_filters_returns_empty_list(tmp_path: Path) -> None:
    """Empty filters should return empty results."""
    client = get_client(str(tmp_path / "chroma"))
    results = lexical_search(must_terms=None, regexes=None, path_like=None, client=client)
    assert results == []


def test_fts_contains_single_term(tmp_path: Path) -> None:
    """Single term search using $contains should find matching documents."""
    client = get_client(str(tmp_path / "chroma"))
    
    # Insert test data
    upsert_code_chunks(
        [
            {
                "id": "chunk1",
                "document": "This is a test document with authentication",
                "metadata": {
                    "doc_id": "file1",
                    "source_path": "src/file1.ts",
                    "lang": "ts",
                    "line_start": 1,
                    "line_end": 5,
                }
            },
            {
                "id": "chunk2",
                "document": "Another file without the keyword",
                "metadata": {
                    "doc_id": "file2",
                    "source_path": "src/file2.ts",
                    "lang": "ts",
                    "line_start": 1,
                    "line_end": 5,
                }
            },
        ],
        client=client,
    )
    
    results = lexical_search(must_terms=["authentication"], k=10, client=client)
    assert len(results) == 1
    assert results[0]["doc_id"] == "file1"
    assert "authentication" in results[0]["why"][0]


def test_fts_contains_multiple_terms(tmp_path: Path) -> None:
    """Multiple terms with AND logic should require all terms."""
    client = get_client(str(tmp_path / "chroma"))
    
    upsert_code_chunks(
        [
            {
                "id": "chunk1",
                "document": "This has both auth and login keywords",
                "metadata": {
                    "doc_id": "file1",
                    "source_path": "src/file1.ts",
                    "lang": "ts",
                    "line_start": 1,
                    "line_end": 5,
                }
            },
            {
                "id": "chunk2",
                "document": "This only has auth keyword",
                "metadata": {
                    "doc_id": "file2",
                    "source_path": "src/file2.ts",
                    "lang": "ts",
                    "line_start": 1,
                    "line_end": 5,
                }
            },
        ],
        client=client,
    )
    
    results = lexical_search(must_terms=["auth", "login"], k=10, client=client)
    assert len(results) == 1
    assert results[0]["doc_id"] == "file1"


def test_regex_search_single(tmp_path: Path) -> None:
    """Single regex pattern should match documents."""
    client = get_client(str(tmp_path / "chroma"))
    
    upsert_code_chunks(
        [
            {
                "id": "chunk1",
                "document": "const api_key = 'secret123'",
                "metadata": {
                    "doc_id": "file1",
                    "source_path": "src/file1.ts",
                    "lang": "ts",
                    "line_start": 1,
                    "line_end": 5,
                }
            },
        ],
        client=client,
    )
    
    results = lexical_search(regexes=[r"api_key"], k=10, client=client)
    assert len(results) == 1
    assert "regex" in results[0]["why"][0]


def test_regex_search_multiple(tmp_path: Path) -> None:
    """Multiple regex patterns with OR logic should match if any pattern matches."""
    client = get_client(str(tmp_path / "chroma"))
    
    upsert_code_chunks(
        [
            {
                "id": "chunk1",
                "document": "const username = 'user'",
                "metadata": {
                    "doc_id": "file1",
                    "source_path": "src/file1.ts",
                    "lang": "ts",
                    "line_start": 1,
                    "line_end": 5,
                }
            },
            {
                "id": "chunk2",
                "document": "const password = 'pass'",
                "metadata": {
                    "doc_id": "file2",
                    "source_path": "src/file2.ts",
                    "lang": "ts",
                    "line_start": 1,
                    "line_end": 5,
                }
            },
        ],
        client=client,
    )
    
    results = lexical_search(regexes=[r"username", r"password"], k=10, client=client)
    assert len(results) == 2


def test_path_filter_client_side(tmp_path: Path) -> None:
    """Path filtering done client-side after retrieval."""
    client = get_client(str(tmp_path / "chroma"))
    
    upsert_code_chunks(
        [
            {
                "id": "chunk1",
                "document": "Authentication code here",
                "metadata": {
                    "doc_id": "file1",
                    "source_path": "src/auth/login.ts",
                    "lang": "ts",
                    "line_start": 1,
                    "line_end": 5,
                }
            },
            {
                "id": "chunk2",
                "document": "Authentication code here",
                "metadata": {
                    "doc_id": "file2",
                    "source_path": "src/utils/helper.ts",
                    "lang": "ts",
                    "line_start": 1,
                    "line_end": 5,
                }
            },
        ],
        client=client,
    )
    
    results = lexical_search(must_terms=["Authentication"], path_like="auth", k=10, client=client)
    assert len(results) == 1
    assert "auth" in results[0]["source_path"]


def test_combined_filters(tmp_path: Path) -> None:
    """Combined filters: terms + regex + path should all apply."""
    client = get_client(str(tmp_path / "chroma"))
    
    upsert_code_chunks(
        [
            {
                "id": "chunk1",
                "document": "API key secret123 authentication code",
                "metadata": {
                    "doc_id": "file1",
                    "source_path": "src/auth/api.ts",
                    "lang": "ts",
                    "line_start": 1,
                    "line_end": 5,
                }
            },
            {
                "id": "chunk2",
                "document": "authentication code without pattern",
                "metadata": {
                    "doc_id": "file2",
                    "source_path": "src/auth/login.ts",
                    "lang": "ts",
                    "line_start": 1,
                    "line_end": 5,
                }
            },
        ],
        client=client,
    )
    
    results = lexical_search(
        must_terms=["authentication"],
        regexes=[r"secret\d+"],
        path_like="api",
        k=10,
        client=client
    )
    assert len(results) == 1
    assert results[0]["doc_id"] == "file1"


def test_k_limit_enforced(tmp_path: Path) -> None:
    """Results should be limited to k even if more matches exist."""
    client = get_client(str(tmp_path / "chroma"))
    
    # Insert multiple chunks that all match
    chunks = [
        {
            "id": f"chunk{i}",
            "document": f"Test document {i} with keyword",
            "metadata": {
                "doc_id": f"file{i}",
                "source_path": f"src/file{i}.ts",
                "lang": "ts",
                "line_start": 1,
                "line_end": 5,
            }
        }
        for i in range(10)
    ]
    upsert_code_chunks(chunks, client=client)
    
    results = lexical_search(must_terms=["keyword"], k=3, client=client)
    assert len(results) == 3


def test_k_zero_or_negative_returns_empty(tmp_path: Path) -> None:
    """k <= 0 should return empty results immediately."""
    # No need to insert data - should return empty immediately based on k <= 0 check
    client = get_client(str(tmp_path / "chroma"))
    
    upsert_code_chunks(
        [{"id": "chunk1", "document": "test", "metadata": {"doc_id": "file1"}}],
        client=client,
    )
    
    assert lexical_search(must_terms=["test"], k=0, client=client) == []
    assert lexical_search(must_terms=["test"], k=-1, client=client) == []


def test_why_signals_include_matches(tmp_path: Path) -> None:
    """Results should include 'why' signals explaining matches."""
    client = get_client(str(tmp_path / "chroma"))
    
    upsert_code_chunks(
        [
            {
                "id": "chunk1",
                "document": "const redirect_uri = 'http://localhost'",
                "metadata": {
                    "doc_id": "file1",
                    "source_path": "src/auth/callback.ts",
                    "lang": "ts",
                    "line_start": 1,
                    "line_end": 5,
                }
            },
        ],
        client=client,
    )
    
    results = lexical_search(
        must_terms=["redirect"],
        regexes=[r"localhost"],
        path_like="callback",
        k=10,
        client=client
    )
    
    assert len(results) == 1
    why = results[0]["why"]
    assert len(why) == 3  # term match, regex match, path match
    assert any("term" in w for w in why)
    assert any("regex" in w for w in why)
    assert any("path" in w for w in why)


def test_invalid_regex_skipped(tmp_path: Path) -> None:
    """Invalid regex patterns should be silently skipped."""
    client = get_client(str(tmp_path / "chroma"))
    
    upsert_code_chunks(
        [
            {
                "id": "chunk1",
                "document": "test content",
                "metadata": {
                    "doc_id": "file1",
                    "source_path": "src/file1.ts",
                    "lang": "ts",
                    "line_start": 1,
                    "line_end": 5,
                }
            },
        ],
        client=client,
    )
    
    # Invalid regex: [unclosed character class
    results = lexical_search(regexes=["["], k=10, client=client)
    # Should not crash, but no matches for invalid regex
    assert len(results) == 0


def test_page_uris_handled_as_string_or_list(tmp_path: Path) -> None:
    """page_uris should be normalized whether stored as string or list."""
    client = get_client(str(tmp_path / "chroma"))
    
    # Note: ChromaDB metadata values must be primitives (not lists), so we store as strings
    # The lexical_search function normalizes strings to lists
    upsert_code_chunks(
        [
            {
                "id": "chunk1",
                "document": "test",
                "metadata": {
                    "doc_id": "file1",
                    "source_path": "src/file1.ts",
                    "page_uris": "http://example.com/page1.webp,http://example.com/page2.webp",
                }
            },
            {
                "id": "chunk2",
                "document": "test",
                "metadata": {
                    "doc_id": "file2",
                    "source_path": "src/file2.ts",
                    "page_uris": "http://example.com/page3.webp",
                }
            },
        ],
        client=client,
    )
    
    results = lexical_search(must_terms=["test"], k=10, client=client)
    assert len(results) == 2
    assert isinstance(results[0]["page_uris"], list)
    assert isinstance(results[1]["page_uris"], list)
    assert len(results[0]["page_uris"]) == 2
    assert len(results[1]["page_uris"]) == 1

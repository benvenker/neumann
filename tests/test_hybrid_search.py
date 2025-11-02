import hashlib
from pathlib import Path

from indexer import (
    LEX_PATH_ONLY_BASELINE,
    get_client,
    hybrid_search,
    lexical_search,
    upsert_code_chunks,
    upsert_summaries,
)


def fake_embedding_function(texts):
    """Fake embedding function that returns deterministic vectors for testing."""
    # Return simple deterministic embeddings based on text hash
    vectors = []
    for text in texts:
        # Simple hash-based deterministic embedding (1536 dim)
        h = hashlib.md5(text.encode()).hexdigest()
        # Create a 1536-dim vector from hash
        vec = []
        for i in range(1536):
            # Use hash to seed deterministic values
            val = (int(h[i % len(h)], 16) % 100) / 100.0 if i < len(h) * 8 else 0.0
            vec.append(val)
        vectors.append(vec)
    return vectors


def test_hybrid_semantic_only(tmp_path: Path) -> None:
    """Semantic-only mode: query provided, no lexical filters."""
    client = get_client(str(tmp_path / "chroma"))

    # Insert test summaries
    upsert_summaries(
        [
            {
                "id": "doc1",
                "document": "This is a document about authentication and PKCE",
                "metadata": {
                    "doc_id": "doc1",
                    "source_path": "src/auth.ts",
                    "page_uris": "http://example.com/doc1-p1.webp",
                },
            },
            {
                "id": "doc2",
                "document": "Another document about database queries",
                "metadata": {
                    "doc_id": "doc2",
                    "source_path": "src/db.ts",
                    "page_uris": "http://example.com/doc2-p1.webp",
                },
            },
        ],
        client=client,
        embedding_function=fake_embedding_function,
    )

    results = hybrid_search(
        "authentication PKCE",
        k=10,
        client=client,
        embedding_function=fake_embedding_function,
    )

    assert len(results) > 0
    assert all("doc_id" in r for r in results)
    assert all("score" in r for r in results)
    assert all("sem_score" in r for r in results)
    assert all("lex_score" in r for r in results)
    assert all("rrf_score" in r for r in results)
    # Should have doc1 first (matches authentication and PKCE)
    assert results[0]["doc_id"] == "doc1"


def test_hybrid_lexical_only(tmp_path: Path) -> None:
    """Lexical-only mode: empty query, lexical filters provided."""
    client = get_client(str(tmp_path / "chroma"))

    # Insert test code chunks
    upsert_code_chunks(
        [
            {
                "id": "chunk1",
                "document": "function redirect_uri() { return '/callback'; }",
                "metadata": {
                    "doc_id": "file1",
                    "source_path": "src/auth.ts",
                    "lang": "ts",
                    "line_start": 10,
                    "line_end": 15,
                    "page_uris": "http://example.com/file1-p1.webp",
                },
            },
            {
                "id": "chunk2",
                "document": "const config = { api_key: 'xyz' };",
                "metadata": {
                    "doc_id": "file2",
                    "source_path": "src/config.ts",
                    "lang": "ts",
                    "line_start": 1,
                    "line_end": 5,
                    "page_uris": "http://example.com/file2-p1.webp",
                },
            },
        ],
        client=client,
    )

    results = hybrid_search(
        "",
        must_terms=["redirect_uri"],
        k=10,
        client=client,
    )

    assert len(results) == 1
    assert results[0]["doc_id"] == "file1"
    assert results[0]["line_start"] == 10
    assert results[0]["line_end"] == 15
    assert "score" in results[0]
    assert "sem_score" in results[0]
    assert "lex_score" in results[0]
    assert "rrf_score" in results[0]


def test_hybrid_combined(tmp_path: Path) -> None:
    """True hybrid: both query and filters, verify score fusion."""
    client = get_client(str(tmp_path / "chroma"))

    # Insert summaries
    upsert_summaries(
        [
            {
                "id": "doc1",
                "document": "Authentication module with PKCE support",
                "metadata": {
                    "doc_id": "doc1",
                    "source_path": "src/auth.ts",
                    "page_uris": "http://example.com/doc1-p1.webp",
                },
            },
        ],
        client=client,
        embedding_function=fake_embedding_function,
    )

    # Insert code chunks
    upsert_code_chunks(
        [
            {
                "id": "chunk1",
                "document": "function redirect_uri() { return '/callback'; }",
                "metadata": {
                    "doc_id": "doc1",
                    "source_path": "src/auth.ts",
                    "lang": "ts",
                    "line_start": 10,
                    "line_end": 15,
                    "page_uris": "http://example.com/doc1-p1.webp",
                },
            },
        ],
        client=client,
    )

    results = hybrid_search(
        "authentication",
        must_terms=["redirect_uri"],
        k=10,
        client=client,
        embedding_function=fake_embedding_function,
    )

    assert len(results) == 1
    assert results[0]["doc_id"] == "doc1"
    # Verify score fusion
    assert "score" in results[0]
    assert "sem_score" in results[0]
    assert "lex_score" in results[0]
    assert "rrf_score" in results[0]
    # Combined score should be weighted sum if both present
    if results[0]["sem_score"] > 0 and results[0]["lex_score"] > 0:
        expected = 0.6 * results[0]["sem_score"] + 0.4 * results[0]["lex_score"]
        assert abs(results[0]["score"] - expected) < 0.001


def test_hybrid_deduplication(tmp_path: Path) -> None:
    """Same doc_id in both channels, verify merge."""
    client = get_client(str(tmp_path / "chroma"))

    # Insert summary
    upsert_summaries(
        [
            {
                "id": "doc1",
                "document": "Authentication module",
                "metadata": {
                    "doc_id": "doc1",
                    "source_path": "src/auth.ts",
                    "page_uris": "http://example.com/doc1-p1.webp",
                },
            },
        ],
        client=client,
        embedding_function=fake_embedding_function,
    )

    # Insert code chunk with same doc_id
    upsert_code_chunks(
        [
            {
                "id": "chunk1",
                "document": "function auth() { }",
                "metadata": {
                    "doc_id": "doc1",
                    "source_path": "src/auth.ts",
                    "lang": "ts",
                    "line_start": 5,
                    "line_end": 10,
                    "page_uris": "http://example.com/doc1-p2.webp",
                },
            },
        ],
        client=client,
    )

    results = hybrid_search(
        "authentication",
        must_terms=["auth"],
        k=10,
        client=client,
        embedding_function=fake_embedding_function,
    )

    # Should be deduplicated to one result
    assert len(results) == 1
    assert results[0]["doc_id"] == "doc1"
    # page_uris should be union
    assert len(results[0]["page_uris"]) == 2
    # line_start/line_end should prefer lexical
    assert results[0]["line_start"] == 5
    assert results[0]["line_end"] == 10
    # why signals should be concatenated
    assert len(results[0]["why"]) >= 2


def test_lexical_scoring_determinism(tmp_path: Path) -> None:
    """Verify lexical results sort by score deterministically."""
    client = get_client(str(tmp_path / "chroma"))

    # Insert multiple chunks with different match counts
    upsert_code_chunks(
        [
            {
                "id": "chunk1",
                "document": "auth auth auth auth auth",  # 5 matches
                "metadata": {
                    "doc_id": "file1",
                    "source_path": "src/file1.ts",
                    "lang": "ts",
                    "line_start": 1,
                    "line_end": 5,
                    "page_uris": "http://example.com/file1-p1.webp",
                },
            },
            {
                "id": "chunk2",
                "document": "auth auth",  # 2 matches
                "metadata": {
                    "doc_id": "file2",
                    "source_path": "src/file2.ts",
                    "lang": "ts",
                    "line_start": 1,
                    "line_end": 5,
                    "page_uris": "http://example.com/file2-p1.webp",
                },
            },
            {
                "id": "chunk3",
                "document": "auth auth auth",  # 3 matches
                "metadata": {
                    "doc_id": "file3",
                    "source_path": "src/file3.ts",
                    "lang": "ts",
                    "line_start": 1,
                    "line_end": 5,
                    "page_uris": "http://example.com/file3-p1.webp",
                },
            },
        ],
        client=client,
    )

    results = lexical_search(must_terms=["auth"], k=10, client=client)

    assert len(results) == 3
    # Should be sorted by score descending
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)
    # file1 should rank highest (5 matches, but capped)
    # Results should be deterministic
    assert results[0]["doc_id"] in ["file1", "file3"]  # Both have high match counts


def test_hybrid_score_fields(tmp_path: Path) -> None:
    """Verify all score fields are present in results."""
    client = get_client(str(tmp_path / "chroma"))

    # Insert test data
    upsert_summaries(
        [
            {
                "id": "doc1",
                "document": "Test document",
                "metadata": {
                    "doc_id": "doc1",
                    "source_path": "src/file1.ts",
                    "page_uris": "http://example.com/doc1-p1.webp",
                },
            },
        ],
        client=client,
        embedding_function=fake_embedding_function,
    )

    upsert_code_chunks(
        [
            {
                "id": "chunk1",
                "document": "test code",
                "metadata": {
                    "doc_id": "doc1",
                    "source_path": "src/file1.ts",
                    "lang": "ts",
                    "line_start": 1,
                    "line_end": 5,
                    "page_uris": "http://example.com/doc1-p1.webp",
                },
            },
        ],
        client=client,
    )

    results = hybrid_search(
        "test",
        must_terms=["test"],
        k=10,
        client=client,
        embedding_function=fake_embedding_function,
    )

    assert len(results) > 0
    for r in results:
        assert "score" in r, "Missing 'score' field"
        assert "sem_score" in r, "Missing 'sem_score' field"
        assert "lex_score" in r, "Missing 'lex_score' field"
        assert "rrf_score" in r, "Missing 'rrf_score' field"
        # Verify score is in [0,1] range
        assert 0.0 <= r["score"] <= 1.0, f"score out of range: {r['score']}"
        assert 0.0 <= r["sem_score"] <= 1.0, f"sem_score out of range: {r['sem_score']}"
        assert 0.0 <= r["lex_score"] <= 1.0, f"lex_score out of range: {r['lex_score']}"


def test_path_only_lexical(tmp_path: Path) -> None:
    """Verify path-only queries return non-zero scores with baseline."""
    client = get_client(str(tmp_path / "chroma"))

    # Insert chunks across multiple files
    upsert_code_chunks(
        [
            {
                "id": "chunk1",
                "document": "function auth() { return true; }",
                "metadata": {
                    "doc_id": "file1",
                    "source_path": "src/auth.ts",
                    "lang": "ts",
                    "line_start": 1,
                    "line_end": 5,
                    "page_uris": "http://example.com/file1-p1.webp",
                },
            },
            {
                "id": "chunk2",
                "document": "const config = { api_key: 'xyz' };",
                "metadata": {
                    "doc_id": "file2",
                    "source_path": "src/config.ts",
                    "lang": "ts",
                    "line_start": 1,
                    "line_end": 5,
                    "page_uris": "http://example.com/file2-p1.webp",
                },
            },
            {
                "id": "chunk3",
                "document": "class AuthHandler { }",
                "metadata": {
                    "doc_id": "file3",
                    "source_path": "components/auth.tsx",
                    "lang": "tsx",
                    "line_start": 1,
                    "line_end": 5,
                    "page_uris": "http://example.com/file3-p1.webp",
                },
            },
        ],
        client=client,
    )

    # Query with path_like only (no terms/regex)
    results = lexical_search(path_like="auth.ts", k=10, client=client)

    assert len(results) >= 1, "Should return results matching path"
    # Verify all results have score >= baseline
    for r in results:
        assert r["score"] >= LEX_PATH_ONLY_BASELINE, (
            f"Path-only match should have score >= {LEX_PATH_ONLY_BASELINE}, got {r['score']}"
        )
        # Verify why signals include baseline message
        baseline_msg = f"path-only match baseline applied: {LEX_PATH_ONLY_BASELINE:.2f}"
        assert any(baseline_msg in signal for signal in r["why"]), (
            f"Why signals should include baseline message, got: {r['why']}"
        )


def test_hybrid_with_path_only_lexical(tmp_path: Path) -> None:
    """Verify path baseline contributes to hybrid fusion."""
    client = get_client(str(tmp_path / "chroma"))

    # Upsert one summary
    upsert_summaries(
        [
            {
                "id": "doc1",
                "document": "Authentication module with secure token handling",
                "metadata": {
                    "doc_id": "doc1",
                    "source_path": "src/auth.ts",
                    "page_uris": "http://example.com/doc1-p1.webp",
                },
            },
        ],
        client=client,
        embedding_function=fake_embedding_function,
    )

    # Upsert one code chunk matching path
    upsert_code_chunks(
        [
            {
                "id": "chunk1",
                "document": "function login() { return true; }",
                "metadata": {
                    "doc_id": "doc1",
                    "source_path": "src/auth.ts",
                    "lang": "ts",
                    "line_start": 10,
                    "line_end": 15,
                    "page_uris": "http://example.com/doc1-p2.webp",
                },
            },
        ],
        client=client,
    )

    # Query with semantic query + path_like (path-only lexical)
    results = hybrid_search(
        "authentication",
        path_like="auth.ts",
        k=10,
        client=client,
        embedding_function=fake_embedding_function,
    )

    assert len(results) > 0, "Should return results"
    # Find doc1 result
    doc1_result = next((r for r in results if r["doc_id"] == "doc1"), None)
    assert doc1_result is not None, "Should find doc1 in results"

    # Verify lex_score >= baseline
    assert doc1_result["lex_score"] >= LEX_PATH_ONLY_BASELINE, (
        f"Path-only lexical should have lex_score >= {LEX_PATH_ONLY_BASELINE}, "
        f"got {doc1_result['lex_score']}"
    )

    # Verify combined score > w_semantic * sem_score (i.e., path baseline contributed)
    # With path baseline, combined should be: 0.6 * sem_score + 0.4 * lex_score
    # If lex_score == baseline (0.25), then combined should be > 0.6 * sem_score
    expected_min = 0.6 * doc1_result["sem_score"]
    assert doc1_result["score"] > expected_min, (
        f"Combined score {doc1_result['score']:.4f} should be > "
        f"{expected_min:.4f} (w_semantic * sem_score) due to path baseline"
    )


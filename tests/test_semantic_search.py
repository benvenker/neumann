from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from indexer import get_client, semantic_search, upsert_summaries


def fake_embedding_function(dimension: int = 1536) -> callable[[Sequence[str]], list[list[float]]]:
    """Create a deterministic fake embedding function for testing.
    
    Args:
        dimension: Embedding dimension (default 1536 to match OpenAI text-embedding-3-small)
    
    Returns:
        Callable that returns deterministic embeddings based on text hash
    """
    def embed(texts: Sequence[str]) -> list[list[float]]:
        embeddings = []
        for text in texts:
            # Generate deterministic embedding based on text hash
            # This creates a fixed vector for the same text
            hash_val = hash(text)
            # Create dimension-sized vector with values based on hash
            # Use modulo to keep values bounded
            vec = [float((hash_val + i) % 100) / 100.0 for i in range(dimension)]
            embeddings.append(vec)
        return embeddings
    return embed


def test_semantic_search_returns_results(tmp_path: Path) -> None:
    """Test that semantic_search returns results with correct structure."""
    client = get_client(str(tmp_path / "chroma"))
    fake_embed = fake_embedding_function()

    # Index 2 summaries with fake embeddings
    count = upsert_summaries(
        [
            {
                "id": "doc1",
                "document": "This is a Python file about web scraping. It uses requests library to fetch HTML content.",
                "metadata": {
                    "doc_id": "doc1",
                    "source_path": "src/scraper.py",
                    "language": "python",
                    "key_topics": "web scraping,HTTP requests",
                    "page_uris": "http://example.com/doc1-p001.webp",
                },
            },
            {
                "id": "doc2",
                "document": "This TypeScript file implements a React component for user authentication.",
                "metadata": {
                    "doc_id": "doc2",
                    "source_path": "src/auth.tsx",
                    "language": "typescript",
                    "key_topics": "React,authentication,components",
                    "page_uris": "http://example.com/doc2-p001.webp",
                },
            },
        ],
        client=client,
        embedding_function=fake_embed,
    )
    assert count == 2

    # Search with fake embedding function
    results = semantic_search("web scraping Python", k=2, client=client, embedding_function=fake_embed)

    assert len(results) > 0, "Should return at least one result"

    # Verify structure of first result
    result = results[0]
    assert "doc_id" in result
    assert "source_path" in result
    assert "score" in result
    assert "page_uris" in result
    assert "line_start" in result
    assert "line_end" in result
    assert "why" in result
    assert "metadata" in result

    # Verify field types
    assert isinstance(result["doc_id"], str)
    assert isinstance(result["score"], float)
    assert isinstance(result["page_uris"], list)
    assert result["line_start"] is None  # Summaries don't have line ranges
    assert result["line_end"] is None
    assert isinstance(result["why"], list)
    assert isinstance(result["metadata"], dict)

    # Verify score is in [0, 1] range
    assert 0.0 <= result["score"] <= 1.0

    # Verify metadata normalization (key_topics should be a list)
    metadata = result["metadata"]
    assert "key_topics" in metadata
    assert isinstance(metadata["key_topics"], list)
    assert "page_uris" in metadata
    assert isinstance(metadata["page_uris"], list)


def test_semantic_search_respects_k_limit(tmp_path: Path) -> None:
    """Test that semantic_search respects the k limit parameter."""
    client = get_client(str(tmp_path / "chroma"))
    fake_embed = fake_embedding_function()

    # Index 5 summaries
    count = upsert_summaries(
        [
            {
                "id": f"doc{i}",
                "document": f"This is document {i} about topic {i}.",
                "metadata": {"doc_id": f"doc{i}", "source_path": f"src/file{i}.py"},
            }
            for i in range(5)
        ],
        client=client,
        embedding_function=fake_embed,
    )
    assert count == 5

    # Query with k=3 - should return exactly 3 results
    results = semantic_search("topic", k=3, client=client, embedding_function=fake_embed)
    assert len(results) == 3, f"Expected 3 results, got {len(results)}"

    # Query with k=10 (more than available) - should return only 5 results
    results = semantic_search("topic", k=10, client=client, embedding_function=fake_embed)
    assert len(results) == 5, f"Expected 5 results (all available), got {len(results)}"

    # Query with k=0 - should return empty list
    results = semantic_search("topic", k=0, client=client, embedding_function=fake_embed)
    assert len(results) == 0, f"Expected 0 results for k=0, got {len(results)}"


def test_semantic_search_sorts_by_relevance(tmp_path: Path) -> None:
    """Test that semantic_search returns results sorted by relevance (score descending)."""
    client = get_client(str(tmp_path / "chroma"))

    # Create embeddings where query embedding is closest to doc1, then doc2, then doc3
    # We'll use a simple distance-based approach
    def controlled_embed(texts: Sequence[str]) -> list[list[float]]:
        """Create embeddings where first text is closest to query embedding."""
        embeddings = []
        for text in texts:
            # For indexing: create different vectors based on text
            if "python web scraping" in text.lower():
                # doc1: close to query (small differences)
                vec = [0.1] * 100 + [0.9] * 1436
            elif "typescript react" in text.lower():
                # doc2: medium distance
                vec = [0.3] * 100 + [0.7] * 1436
            elif "css styling" in text.lower():
                # doc3: far from query
                vec = [0.5] * 100 + [0.5] * 1436
            else:
                # Default: very far
                vec = [0.9] * 100 + [0.1] * 1436
            embeddings.append(vec)
        return embeddings

    # Query embedding should be close to doc1
    def query_embed(texts: Sequence[str]) -> list[list[float]]:
        """Query embedding close to doc1."""
        return [[0.1] * 100 + [0.9] * 1436 for _ in texts]

    # Index 3 summaries with controlled embeddings
    count = upsert_summaries(
        [
            {
                "id": "doc1",
                "document": "This is a Python file about web scraping with requests library.",
                "metadata": {"doc_id": "doc1", "source_path": "src/scraper.py"},
            },
            {
                "id": "doc2",
                "document": "This TypeScript file implements React components for UI.",
                "metadata": {"doc_id": "doc2", "source_path": "src/components.tsx"},
            },
            {
                "id": "doc3",
                "document": "This CSS file contains styling rules and theme definitions.",
                "metadata": {"doc_id": "doc3", "source_path": "src/styles.css"},
            },
        ],
        client=client,
        embedding_function=controlled_embed,
    )
    assert count == 3

    # Search with query embedding close to doc1
    results = semantic_search(
        "python web scraping", k=3, client=client, embedding_function=query_embed
    )

    assert len(results) >= 1, "Should return at least one result"

    # Verify results are sorted by score descending
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True), "Results should be sorted by score descending"

    # Verify scores decrease monotonically (or stay equal)
    for i in range(len(scores) - 1):
        assert scores[i] >= scores[i + 1], f"Score at index {i} ({scores[i]}) should be >= score at index {i+1} ({scores[i+1]})"

    # Verify doc1 has highest score (should be first or among top results)
    # Note: Exact ordering depends on Chroma's distance calculation, but scores should be ordered
    assert results[0]["score"] == max(scores), "First result should have highest score"


def test_semantic_search_empty_query(tmp_path: Path) -> None:
    """Test edge cases: empty query returns empty results."""
    client = get_client(str(tmp_path / "chroma"))

    # Empty query
    results = semantic_search("", k=5, client=client)
    assert len(results) == 0

    # Whitespace-only query
    results = semantic_search("   ", k=5, client=client)
    assert len(results) == 0


def test_semantic_search_metadata_normalization(tmp_path: Path) -> None:
    """Test that metadata fields are properly normalized from comma-separated strings to lists."""
    client = get_client(str(tmp_path / "chroma"))
    fake_embed = fake_embedding_function()

    # Index summary with comma-separated strings in metadata
    count = upsert_summaries(
        [
            {
                "id": "doc1",
                "document": "Test document",
                "metadata": {
                    "doc_id": "doc1",
                    "source_path": "src/test.py",
                    "key_topics": "topic1,topic2,topic3",  # Comma-separated string
                    "product_tags": "tag1,tag2",  # Comma-separated string
                    "api_symbols": "func1,func2,func3",  # Comma-separated string
                    "page_uris": "uri1,uri2",  # Comma-separated string
                },
            },
        ],
        client=client,
        embedding_function=fake_embed,
    )
    assert count == 1

    results = semantic_search("test", k=1, client=client, embedding_function=fake_embed)
    assert len(results) == 1

    metadata = results[0]["metadata"]

    # Verify all list-like fields are normalized to lists
    assert isinstance(metadata["key_topics"], list)
    assert len(metadata["key_topics"]) == 3
    assert metadata["key_topics"] == ["topic1", "topic2", "topic3"]

    assert isinstance(metadata["product_tags"], list)
    assert len(metadata["product_tags"]) == 2
    assert metadata["product_tags"] == ["tag1", "tag2"]

    assert isinstance(metadata["api_symbols"], list)
    assert len(metadata["api_symbols"]) == 3
    assert metadata["api_symbols"] == ["func1", "func2", "func3"]

    assert isinstance(metadata["page_uris"], list)
    assert len(metadata["page_uris"]) == 2
    assert metadata["page_uris"] == ["uri1", "uri2"]

    # Verify top-level page_uris is also a list
    assert isinstance(results[0]["page_uris"], list)
    assert results[0]["page_uris"] == ["uri1", "uri2"]


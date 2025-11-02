#!/usr/bin/env python3
"""Manual end-to-end test for semantic_search functionality (nm-22).

This script demonstrates the full workflow:
1. Loads existing summary files from output_summaries directory
2. Parses YAML front matter + body
3. Indexes summaries into ChromaDB search_summaries collection with embeddings
4. Performs semantic searches
5. Displays results with scores and metadata

Usage:
    python tests/manual/test_semantic_search_e2e.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import yaml

# Add project root to path so we can import from root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from embeddings import embed_texts  # noqa: E402
from indexer import get_client, semantic_search, upsert_summaries  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_summary_file(summary_path: Path) -> dict[str, object]:
    """Load a .summary.md file and parse YAML front matter + body.

    Returns:
        dict with keys: 'id', 'document' (body), 'metadata' (front matter dict)
    """
    content = summary_path.read_text(encoding="utf-8")

    # Split YAML front matter from body
    if not content.startswith("---"):
        raise ValueError(f"{summary_path} does not start with YAML front matter marker")

    parts = content.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"{summary_path} has malformed YAML front matter")

    yaml_content = parts[1].strip()
    body = parts[2].strip()

    # Parse YAML front matter
    front_matter = yaml.safe_load(yaml_content)
    if not isinstance(front_matter, dict):
        raise ValueError(f"{summary_path} front matter is not a dict")

    # Extract doc_id for the ChromaDB id
    doc_id = front_matter.get("doc_id", summary_path.stem.replace(".summary", ""))

    # Metadata normalization now handled by indexer.upsert_summaries
    # No need to manually convert lists - indexer does it automatically
    return {
        "id": doc_id,
        "document": body,
        "metadata": front_matter,
    }


def index_summaries(summaries_dir: Path, chroma_client) -> int:
    """Index all summary files from summaries_dir into ChromaDB.

    Returns:
        Number of summaries indexed.
    """
    logger.info(f"Scanning {summaries_dir} for summary files...")
    summary_files = sorted(summaries_dir.glob("*.summary.md"))

    if not summary_files:
        logger.warning(f"No *.summary.md files found in {summaries_dir}")
        return 0

    logger.info(f"Found {len(summary_files)} summary files")

    items = []
    for summary_path in summary_files:
        try:
            logger.info(f"Loading {summary_path.name}...")
            item = load_summary_file(summary_path)
            items.append(item)
            logger.info(
                f"  doc_id={item['id']}, source_path={item['metadata'].get('source_path')}, "
                f"words={len(item['document'].split())}"
            )
        except Exception as e:
            logger.error(f"Failed to load {summary_path}: {e}", exc_info=True)
            continue

    if not items:
        logger.warning("No valid summary items to index")
        return 0

    logger.info(f"Indexing {len(items)} summaries into ChromaDB with embeddings...")
    count = upsert_summaries(items, client=chroma_client, embedding_function=embed_texts)
    logger.info(f"✓ Indexed {count} summaries")
    return count


def test_embedding_function_parameter(chroma_client):
    """Test that the optional embedding_function parameter works correctly."""
    logger.info("\n" + "=" * 60)
    logger.info("Step 2a: Testing embedding_function parameter")
    logger.info("=" * 60)

    # Create a simple fake embedding function for testing
    def fake_embed(texts):
        """Simple deterministic embedding for testing."""
        dimension = 1536
        embeddings = []
        for text in texts:
            # Create deterministic vector based on text hash
            hash_val = hash(text)
            vec = [float((hash_val + i) % 100) / 100.0 for i in range(dimension)]
            embeddings.append(vec)
        return embeddings

    logger.info("Testing with custom embedding_function parameter...")
    try:
        results = semantic_search(
            "test query",
            k=3,
            client=chroma_client,
            embedding_function=fake_embed,
        )
        logger.info(f"✓ Custom embedding_function works: returned {len(results)} results")
        if results:
            logger.info(f"  First result: doc_id={results[0].get('doc_id')}, score={results[0].get('score'):.4f}")
    except Exception as e:
        logger.error(f"✗ Custom embedding_function test failed: {e}", exc_info=True)
        raise


def test_error_handling(chroma_client):
    """Test that error handling works correctly."""
    logger.info("\n" + "=" * 60)
    logger.info("Step 2b: Testing error handling")
    logger.info("=" * 60)

    # Test empty query handling (should return empty list, not raise)
    logger.info("Testing empty query handling...")
    try:
        results = semantic_search("", k=5, client=chroma_client)
        assert len(results) == 0, "Empty query should return empty list"
        logger.info("✓ Empty query handled correctly (returns empty list)")
    except Exception as e:
        logger.error(f"✗ Empty query handling failed: {e}", exc_info=True)
        raise

    # Test whitespace-only query handling
    logger.info("Testing whitespace-only query handling...")
    try:
        results = semantic_search("   ", k=5, client=chroma_client)
        assert len(results) == 0, "Whitespace-only query should return empty list"
        logger.info("✓ Whitespace-only query handled correctly (returns empty list)")
    except Exception as e:
        logger.error(f"✗ Whitespace-only query handling failed: {e}", exc_info=True)
        raise

    # Test k=0 handling
    logger.info("Testing k=0 handling...")
    try:
        results = semantic_search("test", k=0, client=chroma_client)
        assert len(results) == 0, "k=0 should return empty list"
        logger.info("✓ k=0 handled correctly (returns empty list)")
    except Exception as e:
        logger.error(f"✗ k=0 handling failed: {e}", exc_info=True)
        raise


def test_result_structure(chroma_client):
    """Test that result structure matches the expected format."""
    logger.info("\n" + "=" * 60)
    logger.info("Step 2c: Testing result structure")
    logger.info("=" * 60)

    results = semantic_search("chat API", k=1, client=chroma_client)

    if not results:
        logger.warning("No results to verify structure")
        return

    result = results[0]
    logger.info("Verifying result structure...")

    # Check required fields
    required_fields = ["doc_id", "source_path", "score", "page_uris", "line_start", "line_end", "why", "metadata"]
    for field in required_fields:
        assert field in result, f"Missing required field: {field}"
    logger.info(f"✓ All required fields present: {', '.join(required_fields)}")

    # Check field types
    assert isinstance(result["doc_id"], str), "doc_id should be string"
    assert isinstance(result["score"], float), "score should be float"
    assert isinstance(result["page_uris"], list), "page_uris should be list"
    assert result["line_start"] is None, "line_start should be None for summaries"
    assert result["line_end"] is None, "line_end should be None for summaries"
    assert isinstance(result["why"], list), "why should be list"
    assert isinstance(result["metadata"], dict), "metadata should be dict"
    logger.info("✓ All field types are correct")

    # Check score range
    assert 0.0 <= result["score"] <= 1.0, f"score should be in [0,1], got {result['score']}"
    logger.info(f"✓ Score in valid range: {result['score']:.4f}")

    # Check metadata normalization
    metadata = result["metadata"]
    if "key_topics" in metadata:
        assert isinstance(metadata["key_topics"], list), "key_topics should be normalized to list"
        logger.info(f"✓ Metadata normalization works: key_topics is a list with {len(metadata['key_topics'])} items")

    # Check page_uris duplication (both top-level and in metadata)
    assert "page_uris" in metadata, "page_uris should also appear in metadata"
    assert isinstance(metadata["page_uris"], list), "metadata.page_uris should be normalized to list"
    logger.info("✓ page_uris appears in both top-level and metadata (intentional duplication)")


def run_searches(chroma_client):
    """Run a series of semantic searches and display results."""

    test_queries = [
        "Python code",
        "file handling",
        "function definitions",
        "UI components",
        "TypeScript code",
        "chat API streaming",
    ]

    logger.info("\n" + "=" * 60)
    logger.info("Step 2d: Running semantic searches with real embeddings")
    logger.info("=" * 60)

    for query in test_queries:
        logger.info("=" * 60)
        logger.info(f"Query: '{query}'")
        logger.info("-" * 60)

        try:
            results = semantic_search(query, k=5, client=chroma_client)

            if not results:
                logger.info("  No results found")
                continue

            logger.info(f"  Found {len(results)} results:\n")

            for i, result in enumerate(results, 1):
                logger.info(f"  [{i}] doc_id: {result['doc_id']}")
                logger.info(f"      source_path: {result.get('source_path', 'N/A')}")
                logger.info(f"      score: {result['score']:.4f}")
                logger.info(f"      page_uris: {len(result.get('page_uris', []))} URIs")
                logger.info(f"      why: {', '.join(result.get('why', []))}")

                # Show normalized metadata if available
                metadata = result.get("metadata", {})
                if metadata:
                    key_topics = metadata.get("key_topics", [])
                    if key_topics:
                        logger.info(f"      topics: {', '.join(key_topics[:3])}...")

                logger.info("")

        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)


def main():
    """Main test runner."""
    project_root = Path(__file__).parent.parent.parent
    # Check test_output_summaries first (has real summaries), fallback to output_summaries
    test_summaries_dir = project_root / "test_output_summaries"
    output_summaries_dir = project_root / "output_summaries"

    if test_summaries_dir.exists() and any(test_summaries_dir.glob("*.summary.md")):
        summaries_dir = test_summaries_dir
        logger.info("Using test_output_summaries (has real summaries)")
    elif output_summaries_dir.exists():
        summaries_dir = output_summaries_dir
    else:
        summaries_dir = test_summaries_dir  # Will fail with clear error

    chroma_path = project_root / "chroma_data"

    if not summaries_dir.exists():
        logger.error(f"Summaries directory not found: {summaries_dir}")
        logger.info("Expected summary files in: output_summaries/*.summary.md")
        sys.exit(1)

    logger.info("🧪 Testing Semantic Search over Summaries (nm-22)")
    logger.info("=" * 60)
    logger.info(f"Summaries directory: {summaries_dir}")
    logger.info(f"ChromaDB path: {chroma_path}")

    # Check for OPENAI_API_KEY
    from config import config

    if not config.has_openai_key:
        logger.warning("⚠️  OPENAI_API_KEY not set - embeddings will fail")
        logger.warning("  Set OPENAI_API_KEY in .env or environment to run this test")
        sys.exit(1)
    else:
        logger.info("✓ OPENAI_API_KEY configured")

    # Initialize ChromaDB client
    logger.info("\n" + "=" * 60)
    logger.info("Step 1: Indexing summaries")
    logger.info("=" * 60)
    chroma_client = get_client(str(chroma_path))

    indexed_count = index_summaries(summaries_dir, chroma_client)

    if indexed_count == 0:
        logger.error("No summaries indexed. Cannot run searches.")
        sys.exit(1)

    # Run comprehensive tests
    logger.info("\n" + "=" * 60)
    logger.info("Step 2: Comprehensive semantic search testing")
    logger.info("=" * 60)

    # Test new features
    test_embedding_function_parameter(chroma_client)
    test_error_handling(chroma_client)
    test_result_structure(chroma_client)

    # Run real searches
    run_searches(chroma_client)

    logger.info("\n" + "=" * 60)
    logger.info("✅ Semantic search test complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Fatal error: {type(e).__name__}: {e}")
        sys.exit(1)

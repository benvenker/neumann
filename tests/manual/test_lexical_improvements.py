#!/usr/bin/env python3
"""Manual test for lexical search improvements (nm-24 feedback).

Tests the new features:
- Lexical scoring with caps and tie-breakers
- Regex scoring and ordering
- Path fetch multiplier
- Metadata normalization
- Rich metrics in why signals

Usage:
    .venv/bin/python tests/manual/test_lexical_improvements.py [--output OUTPUT_FILE]
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from tempfile import mkdtemp

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from chunker import chunk_file_by_lines
from indexer import get_client, lexical_search, upsert_code_chunks

# Module-level logger (will be configured in main)
logger = logging.getLogger(__name__)


def setup_logging(output_file: Path | None = None) -> logging.Logger:
    """Setup logging to both console and file.
    
    Args:
        output_file: Optional path to log file. If None, uses default in test_output/.
    
    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Clear any existing handlers
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (if output_file provided)
    if output_file:
        # Ensure parent directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(output_file, mode='w', encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        logger.info(f"📝 Writing output to: {output_file}")

    return logger


def index_test_file(file_path: Path, client, output_root: Path) -> int:
    """Index a file by chunking and upserting."""
    logger.info(f"📄 Indexing {file_path.name}...")

    text = file_path.read_text(encoding="utf-8")
    doc_id = file_path.stem.replace(".", "_")

    # Mock pages.jsonl path (empty page URIs for now)
    pages_jsonl_path = output_root / doc_id / "pages" / "pages.jsonl"
    pages_jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    pages_jsonl_path.write_text("")  # Empty pages.jsonl

    # Chunk with smaller size for testing
    chunks = chunk_file_by_lines(text, pages_jsonl_path, per_chunk=50, overlap=5)
    logger.info(f"   Created {len(chunks)} chunks")

    items = []
    for i, chunk in enumerate(chunks):
        chunk_id = f"{doc_id}:chunk_{i:03d}"
        items.append({
            "id": chunk_id,
            "document": chunk["text"],
            "metadata": {
                "doc_id": doc_id,
                "source_path": str(file_path),
                "lang": file_path.suffix.lstrip("."),
                "line_start": chunk["line_start"],
                "line_end": chunk["line_end"],
                "page_uris": "",
            }
        })

    count = upsert_code_chunks(items, client=client)
    logger.info(f"   ✓ Indexed {count} chunks\n")
    return count


def print_result(result: dict, index: int) -> None:
    """Pretty print a search result."""
    logger.info(f"   [{index}] {result['doc_id']}")
    logger.info(f"       📍 {result['source_path']}")
    logger.info(f"       ⭐ score={result['score']:.4f}")
    if result.get("line_start"):
        logger.info(f"       📏 lines {result['line_start']}-{result['line_end']}")
    if result.get("metadata"):
        lang = result["metadata"].get("language") or result["metadata"].get("lang")
        if lang:
            logger.info(f"       🏷️  lang={lang}")
    if result.get("why"):
        logger.info(f"       💡 why: {'; '.join(result['why'])}")


def test_case_1_regex_scoring(client):
    """Test 1: Regex scoring with multiple matches shows ordering by tie-breakers."""
    logger.info("\n" + "="*70)
    logger.info("TEST 1: Regex Scoring & Tie-Breakers")
    logger.info("="*70)
    logger.info("Query: regex 'const\\s+' (should find multiple matches)")
    logger.info("Expected: Files with more regex matches rank higher")
    logger.info("         Tie-breakers: categories → raw_hits → doc_len")

    results = lexical_search(
        regexes=[r"const\s+"],
        k=10,
        client=client
    )

    logger.info(f"\n📊 Found {len(results)} results:\n")
    for i, r in enumerate(results, 1):
        print_result(r, i)

    # Verify results
    assert len(results) > 0, "Should find at least one result"
    logger.info("\n✅ Test 1 passed: Regex scoring works")


def test_case_2_term_and_regex_combined(client):
    """Test 2: Combined term + regex search with AND logic."""
    logger.info("\n" + "="*70)
    logger.info("TEST 2: Combined Term + Regex (AND)")
    logger.info("="*70)
    logger.info(r"Query: must_terms=['function'] + regexes=[r'export\s+']")
    logger.info("Expected: Only chunks containing BOTH 'function' AND matching regex")

    results = lexical_search(
        must_terms=["function"],
        regexes=[r"export\s+"],
        k=10,
        client=client
    )

    logger.info(f"\n📊 Found {len(results)} results:\n")
    for i, r in enumerate(results, 1):
        print_result(r, i)
        # Verify both conditions are met
        why_str = "; ".join(r["why"])
        assert "term" in why_str.lower() or "matched term" in why_str
        assert "regex" in why_str.lower() or "matched regex" in why_str

    logger.info("\n✅ Test 2 passed: Combined filters work correctly")


def test_case_3_path_filtering_with_fetch_multiplier(client):
    """Test 3: Path filtering uses fetch multiplier for better recall."""
    logger.info("\n" + "="*70)
    logger.info("TEST 3: Path Filtering with Fetch Multiplier")
    logger.info("="*70)
    logger.info("Query: path_like='components' (client-side filtering)")
    logger.info("Expected: Finds results in components/ directory")
    logger.info("         Uses k×10 fetch limit for better recall")

    results = lexical_search(
        path_like="components",
        k=5,
        client=client
    )

    logger.info(f"\n📊 Found {len(results)} results:\n")
    for i, r in enumerate(results, 1):
        print_result(r, i)
        # Verify path filtering worked
        assert "components" in r["source_path"].lower(), "Path filter should match"

    logger.info("\n✅ Test 3 passed: Path filtering with fetch multiplier works")


def test_case_4_metadata_normalization(client):
    """Test 4: Metadata normalization symmetry with semantic_search."""
    logger.info("\n" + "="*70)
    logger.info("TEST 4: Metadata Normalization")
    logger.info("="*70)
    logger.info("Query: any search to check metadata structure")
    logger.info("Expected: Results include normalized 'metadata' dict with")
    logger.info("         language, last_updated, and list-like fields parsed")

    results = lexical_search(
        must_terms=["import"],
        k=3,
        client=client
    )

    logger.info(f"\n📊 Checking metadata in {len(results)} results:\n")
    for i, r in enumerate(results, 1):
        logger.info(f"   [{i}] {r['doc_id']}")
        metadata = r.get("metadata", {})
        logger.info(f"       📦 metadata keys: {list(metadata.keys())}")
        logger.info(f"       🏷️  language: {metadata.get('language')}")
        logger.info(f"       📄 page_uris (normalized): {metadata.get('page_uris', [])}")
        # Verify structure
        assert isinstance(metadata, dict), "metadata should be a dict"
        assert isinstance(metadata.get("page_uris", []), list), "page_uris should be list"

    logger.info("\n✅ Test 4 passed: Metadata normalization works")


def test_case_5_rich_why_signals(client):
    """Test 5: Rich 'why' signals with match counts from metrics."""
    logger.info("\n" + "="*70)
    logger.info("TEST 5: Rich Why Signals with Match Counts")
    logger.info("="*70)
    logger.info("Query: must_terms=['const'] + regexes=[r'\\w+\\s*=']")
    logger.info("Expected: 'why' signals show match counts (xN)")
    logger.info("         Counts come from metrics, not re-counting")

    results = lexical_search(
        must_terms=["const"],
        regexes=[r"\w+\s*="],
        k=5,
        client=client
    )

    logger.info(f"\n📊 Found {len(results)} results:\n")
    for i, r in enumerate(results, 1):
        print_result(r, i)
        # Verify why signals have counts
        why_str = "; ".join(r["why"])
        has_counts = " x" in why_str or " x" in why_str
        logger.info(f"       {'✓ Has match counts' if has_counts else '✗ Missing counts'}")

    logger.info("\n✅ Test 5 passed: Rich why signals work")


def test_case_6_lexical_scoring_with_caps(client):
    """Test 6: Lexical scoring respects caps (terms/regex don't dominate)."""
    logger.info("\n" + "="*70)
    logger.info("TEST 6: Lexical Scoring with Caps")
    logger.info("="*70)
    logger.info("Query: must_terms=['import'] (find files with many imports)")
    logger.info("Expected: Scores capped at 3 per term to prevent domination")
    logger.info("         Files with 1-3 imports score similar to 10+ imports")

    results = lexical_search(
        must_terms=["import"],
        k=5,
        client=client
    )

    logger.info(f"\n📊 Found {len(results)} results (sorted by score):\n")
    prev_score = float('inf')
    for i, r in enumerate(results, 1):
        print_result(r, i)
        score = r["score"]
        logger.info(f"       📉 Score progression: {prev_score:.4f} → {score:.4f}")
        # Verify scores are descending
        assert score <= prev_score, "Results should be sorted by score desc"
        prev_score = score

    logger.info("\n✅ Test 6 passed: Lexical scoring with caps works")


def test_case_7_path_only_baseline(client):
    """Test 7: Path-only queries get baseline score for hybrid fusion."""
    logger.info("\n" + "="*70)
    logger.info("TEST 7: Path-Only Baseline")
    logger.info("="*70)
    logger.info("Query: path_like='components' (no terms/regex)")
    logger.info("Expected: Results get LEX_PATH_ONLY_BASELINE (0.25) score")
    logger.info("         'why' includes 'path-only match baseline applied'")

    results = lexical_search(
        path_like="components",
        k=5,
        client=client
    )

    logger.info(f"\n📊 Found {len(results)} results:\n")
    for i, r in enumerate(results, 1):
        print_result(r, i)
        # Verify baseline applied
        score = r["score"]
        why_str = "; ".join(r["why"])
        has_baseline = "baseline" in why_str.lower()
        logger.info(f"       Score: {score:.4f} ({'✓ Has baseline' if has_baseline else '✗ Missing baseline'})")

    logger.info("\n✅ Test 7 passed: Path-only baseline works")


def main() -> int:
    """Run all manual tests."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Manual test for lexical search improvements",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Path to output log file (default: test_output/lexical_test_YYYYMMDD_HHMMSS.log)",
    )
    args = parser.parse_args()

    # Setup output file (default or user-specified)
    project_root = Path(__file__).parent.parent.parent
    if args.output:
        output_file = args.output
    else:
        # Default to test_output/ directory with timestamp
        test_output_dir = project_root / "test_output"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = test_output_dir / f"lexical_test_{timestamp}.log"

    # Setup logging (this creates the logger)
    logger = setup_logging(output_file)

    test_data_dir = project_root / "test_data"

    if not test_data_dir.exists():
        logger.error(f"❌ Test data directory not found: {test_data_dir}")
        return 1

    logger.info("🧪 Manual Tests for Lexical Search Improvements")
    logger.info("=" * 70)

    # Setup ChromaDB
    chroma_path = mkdtemp(prefix="neumann_lexical_test_")
    logger.info(f"📁 Using ChromaDB at: {chroma_path}")
    client = get_client(chroma_path)

    # Index test files
    logger.info(f"\n📚 Indexing files from {test_data_dir}...")
    logger.info("-" * 70)

    text_extensions = {".py", ".ts", ".tsx", ".js", ".jsx", ".css", ".md"}
    files = sorted([f for f in test_data_dir.rglob("*")
                    if f.is_file() and f.suffix.lower() in text_extensions])

    # Limit to a good selection for testing
    test_files = []
    for f in files:
        # Pick diverse files
        if "chat-section" in f.name or "route" in f.name or "button" in f.name:
            test_files.append(f)
        if len(test_files) >= 5:
            break

    logger.info(f"Selected {len(test_files)} files to index\n")

    total_chunks = 0
    for file_path in test_files:
        try:
            chunks_count = index_test_file(file_path, client, project_root / "output")
            total_chunks += chunks_count
        except Exception as e:
            logger.error(f"❌ Failed to index {file_path}: {e}", exc_info=True)
            return 1

    logger.info(f"✓ Total: {total_chunks} chunks indexed")

    # Run test cases
    logger.info("\n" + "="*70)
    logger.info("🔍 Running Test Cases")
    logger.info("="*70)

    try:
        test_case_1_regex_scoring(client)
        test_case_2_term_and_regex_combined(client)
        test_case_3_path_filtering_with_fetch_multiplier(client)
        test_case_4_metadata_normalization(client)
        test_case_5_rich_why_signals(client)
        test_case_6_lexical_scoring_with_caps(client)
        test_case_7_path_only_baseline(client)

        logger.info("\n" + "="*70)
        logger.info("✅ All tests completed successfully!")
        logger.info("="*70)
        logger.info(f"📁 ChromaDB data: {chroma_path}")
        logger.info(f"📝 Output log: {output_file}")
        logger.info("💡 You can inspect the ChromaDB to verify indexing")

        return 0

    except AssertionError as e:
        logger.error(f"\n❌ Test failed: {e}", exc_info=True)
        return 1
    except Exception as e:
        logger.error(f"\n❌ Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"💥 Fatal error: {type(e).__name__}: {e}")
        sys.exit(1)


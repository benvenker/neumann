#!/usr/bin/env python3
"""Manual end-to-end test for lexical_search functionality (nm-23).

This script demonstrates the full workflow:
1. Reads files from test_data directory
2. Chunks them using chunker.py
3. Indexes chunks into ChromaDB search_code collection
4. Performs various lexical searches
5. Displays results with "why" signals

Usage:
    python tests/manual/test_lexical_search_e2e.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Add project root to path so we can import from root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from chunker import chunk_file_by_lines  # noqa: E402
from indexer import get_client, lexical_search, upsert_code_chunks  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def find_text_files(root_dir: Path) -> list[Path]:
    """Find all text files in the directory tree."""
    text_extensions = {".py", ".ts", ".tsx", ".js", ".jsx", ".css", ".md"}
    files = []
    for path in root_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in text_extensions:
            files.append(path)
    return sorted(files)


def index_file(file_path: Path, chroma_client, output_root: Path) -> int:
    """Index a single file by chunking and upserting into ChromaDB.

    Returns the number of chunks indexed.
    """
    logger.info(f"Processing {file_path.name}...")

    # Read file content
    text = file_path.read_text(encoding="utf-8")

    # Find corresponding pages.jsonl (mock for now since we don't have rendered output)
    # In a real scenario, this would be at: output_root / doc_id / pages / pages.jsonl
    pages_jsonl_path = output_root / file_path.name / "pages" / "pages.jsonl"

    # Chunk the file
    chunks = chunk_file_by_lines(text, pages_jsonl_path, per_chunk=50, overlap=5)
    logger.info(f"  Created {len(chunks)} chunks")

    # Prepare items for upsert
    items = []
    for i, chunk in enumerate(chunks):
        doc_id = file_path.name.replace(".", "_")
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
                "page_uris": ",".join(chunk["page_uris"]) if chunk["page_uris"] else "",
            }
        })

    # Upsert chunks
    count = upsert_code_chunks(items, client=chroma_client)
    logger.info(f"  Indexed {count} chunks into ChromaDB")

    return count


def run_searches(chroma_client):
    """Run a series of lexical searches and display results."""

    test_searches = [
        {
            "name": "Single term search",
            "must_terms": ["function"],
            "regexes": None,
            "path_like": None,
        },
        {
            "name": "Multiple terms (AND)",
            "must_terms": ["function", "return"],
            "regexes": None,
            "path_like": None,
        },
        {
            "name": "Regex search",
            "must_terms": None,
            "regexes": [r"import\s+\w+"],
            "path_like": None,
        },
        {
            "name": "Path filtering",
            "must_terms": ["class"],
            "regexes": None,
            "path_like": ".tsx",
        },
        {
            "name": "Combined filters",
            "must_terms": ["export"],
            "regexes": [r"const\s+\w+\s*="],
            "path_like": ".tsx",
        },
    ]

    for search in test_searches:
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"Search: {search['name']}")
        logger.info(f"  Terms: {search['must_terms']}")
        logger.info(f"  Regex: {search['regexes']}")
        logger.info(f"  Path: {search['path_like']}")
        logger.info("-" * 60)

        results = lexical_search(
            must_terms=search["must_terms"],
            regexes=search["regexes"],
            path_like=search["path_like"],
            k=5,
            client=chroma_client
        )

        if not results:
            logger.info("  No results found")
        else:
            for i, result in enumerate(results, 1):
                logger.info(f"  Result {i}:")
                logger.info(f"    doc_id: {result['doc_id']}")
                logger.info(f"    source: {result['source_path']}")
                if result.get("line_start"):
                    logger.info(f"    lines: {result['line_start']}-{result['line_end']}")
                if result["why"]:
                    logger.info(f"    why: {'; '.join(result['why'])}")
                logger.info("")


def main() -> int:
    """Run the end-to-end test."""
    project_root = Path(__file__).parent.parent.parent
    test_data_dir = project_root / "test_data"

    if not test_data_dir.exists():
        logger.error(f"Test data directory not found: {test_data_dir}")
        return 1

    logger.info("🧪 Testing Lexical Search End-to-End (nm-23)")
    logger.info("=" * 60)

    # Initialize ChromaDB client with temporary storage
    from tempfile import mkdtemp

    chroma_path = mkdtemp(prefix="neumann_test_")
    logger.info(f"Using ChromaDB at: {chroma_path}")
    chroma_client = get_client(chroma_path)

    # Find and index files
    logger.info(f"\n📁 Scanning {test_data_dir} for files...")
    files = find_text_files(test_data_dir)

    if not files:
        logger.error(f"No text files found in {test_data_dir}")
        return 1

    # Limit to first 5 files for testing
    files = files[:5]
    logger.info(f"Found {len(files)} files to index")

    total_chunks = 0
    for file_path in files:
        try:
            chunks_count = index_file(file_path, chroma_client, project_root / "output")
            total_chunks += chunks_count
        except Exception as e:
            logger.error(f"Failed to index {file_path}: {e}", exc_info=True)
            return 1

    logger.info(f"\n✓ Indexed {total_chunks} total chunks")

    # Run searches
    logger.info("\n🔍 Running search queries...")
    try:
        run_searches(chroma_client)
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        return 1

    logger.info("=" * 60)
    logger.info("✅ End-to-end test completed successfully")
    logger.info(f"📁 ChromaDB data: {chroma_path}")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Fatal error: {type(e).__name__}: {e}")
        sys.exit(1)

#!/usr/bin/env python3
"""Manual test script for OpenAI summarization.

Reads files from test_data directory, generates summaries using OpenAI,
and saves them to test_output_summaries/ directory.

Usage:
    python tests/manual/test_summarization.py
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

# Add project root to path so we can import from root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from summarize import save_summary_md, summarize_file  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def find_text_files(root_dir: Path) -> list[Path]:
    """Find all text files in the directory tree."""
    text_extensions = {".py", ".ts", ".tsx", ".js", ".jsx", ".css", ".md", ".rs", ".go", ".java"}
    files = []
    for path in root_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in text_extensions:
            files.append(path)
    return sorted(files)


def test_summarization(test_data_dir: Path, output_dir: Path, limit: int | None = None) -> None:
    """Test summarization on files in test_data_dir.

    Args:
        test_data_dir: Directory containing test files
        output_dir: Directory to save summaries
        limit: Optional limit on number of files to process (for testing)
    """
    logger.info(f"Scanning {test_data_dir} for text files...")
    files = find_text_files(test_data_dir)

    if not files:
        logger.error(f"No text files found in {test_data_dir}")
        sys.exit(1)

    if limit:
        files = files[:limit]
        logger.info(f"Limited to first {limit} files")

    logger.info(f"Found {len(files)} files to summarize")
    logger.info(f"Output directory: {output_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    success_count = 0
    error_count = 0
    start_time = time.time()

    for i, file_path in enumerate(files, 1):
        file_start = time.time()
        relative_path = file_path.relative_to(test_data_dir)

        try:
            logger.info(f"[{i}/{len(files)}] Processing {relative_path}...")

            # Read file content
            logger.debug(f"Reading file content ({file_path.stat().st_size} bytes)...")
            text = file_path.read_text(encoding="utf-8")
            logger.debug(f"File contains {len(text)} characters, {len(text.split())} words")

            # Generate summary (uses OpenAI since no callback provided)
            logger.info("Calling OpenAI API for summarization...")
            api_start = time.time()
            try:
                summary = summarize_file(str(file_path), text)
            except Exception as api_error:
                api_time = time.time() - api_start
                logger.error(f"✗ OpenAI API call failed after {api_time:.2f}s")
                logger.error(f"  Error type: {type(api_error).__name__}")
                logger.error(f"  Error message: {str(api_error)}")
                # Try to extract more details from OpenAI errors
                if hasattr(api_error, "response"):
                    try:
                        error_body = api_error.response.json() if hasattr(api_error.response, "json") else {}
                        logger.error(f"  API error details: {error_body}")
                    except Exception:
                        pass
                raise
            api_time = time.time() - api_start
            logger.info(f"✓ OpenAI API call completed in {api_time:.2f}s")

            # Verify summary
            word_count = len(summary.summary_md.split())
            logger.info(
                f"Generated summary: {word_count} words, "
                f"language={summary.front_matter.language}, "
                f"topics={len(summary.front_matter.key_topics)}"
            )

            # Save summary
            output_path = output_dir / f"{file_path.stem}.summary.md"
            logger.debug(f"Saving summary to {output_path}...")
            save_summary_md(output_path, summary)

            # Verify output
            if output_path.exists():
                file_time = time.time() - file_start
                logger.info(
                    f"✓ Saved: {output_path.name} (doc_id={summary.front_matter.doc_id}, {file_time:.2f}s total)"
                )
                if summary.front_matter.key_topics:
                    topics_preview = ", ".join(summary.front_matter.key_topics[:3])
                    logger.debug(f"  Topics: {topics_preview}...")
                success_count += 1
            else:
                logger.error(f"✗ Output file not created: {output_path}")
                error_count += 1

        except KeyboardInterrupt:
            logger.warning("Interrupted by user")
            raise
        except Exception as e:
            logger.error(f"✗ ERROR processing {relative_path}: {type(e).__name__}: {e}", exc_info=True)
            error_count += 1

        print()  # Blank line between files

    # Summary
    total_time = time.time() - start_time
    logger.info("=" * 60)
    logger.info(f"✅ Successfully summarized: {success_count}/{len(files)} files")
    if error_count > 0:
        logger.warning(f"❌ Errors: {error_count} files")
    logger.info(f"⏱️  Total time: {total_time:.2f}s ({total_time / len(files):.2f}s per file)")
    logger.info(f"📁 Output directory: {output_dir}")


if __name__ == "__main__":
    project_root = Path(__file__).parent.parent.parent
    test_data_dir = project_root / "test_data"
    output_dir = project_root / "test_output_summaries"

    if not test_data_dir.exists():
        logger.error(f"Test data directory not found: {test_data_dir}")
        sys.exit(1)

    logger.info("🧪 Testing OpenAI Summarization")
    logger.info("=" * 60)

    # Check for OPENAI_API_KEY
    from config import config

    if not config.has_openai_key:
        logger.warning("⚠️  OPENAI_API_KEY not set - summarization calls will fail")
        logger.warning("  Add OPENAI_API_KEY to .env (or prefix this command) before rerunning.")
        logger.warning("  Remember to recreate tmux sessions after editing .env so the key is visible.")
    else:
        logger.info("✓ OPENAI_API_KEY configured")

    # Limit to first 2 files for initial testing (remove limit=None to process all)
    try:
        test_summarization(test_data_dir, output_dir, limit=2)
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Fatal error: {type(e).__name__}: {e}")
        sys.exit(1)

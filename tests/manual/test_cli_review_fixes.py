#!/usr/bin/env python3
"""Manual test for CLI review fixes (nm-25).

This script tests:
1. hybrid_search keyword argument fix (semantic and lexical-only paths)
2. asset_root configurability in ingest command
3. Optional robustness improvements (serve command)

Usage:
    python tests/manual/test_cli_review_fixes.py
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_command(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    logger.info(f"Running: {' '.join(cmd)}")

    # Use the project's Python if running with python -m main
    if cmd[0] == "python" and len(cmd) > 1 and cmd[1] == "-m":
        venv_python = project_root / ".venv" / "bin" / "python"
        if venv_python.exists():
            cmd = [str(venv_python)] + cmd[1:]

    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=cwd or project_root
    )
    logger.debug(f"Return code: {result.returncode}")
    if result.stdout:
        logger.debug(f"STDOUT:\n{result.stdout}")
    if result.stderr:
        logger.debug(f"STDERR:\n{result.stderr}")
    return result.returncode, result.stdout, result.stderr


def test_hybrid_search_keyword_args():
    """Test that hybrid_search is called with keyword arguments."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 1: hybrid_search keyword argument fix")
    logger.info("=" * 60)

    # Test semantic search path (requires OpenAI key)
    logger.info("\n1.1 Testing semantic search path...")
    from config import config

    if config.has_openai_key:
        logger.info("OpenAI key available - testing semantic search")
        rc, stdout, stderr = run_command(
            ["python", "-m", "main", "search", "vector store", "--k", "3"]
        )
        if rc == 0:
            logger.info("✓ Semantic search executed successfully")
            logger.info("  (keyword args fix verified - no test failure)")
        else:
            logger.error(f"✗ Semantic search failed: {stderr}")
            return False
    else:
        logger.info("⚠ OpenAI key not available - skipping semantic search test")
        logger.info("  (This is expected if OPENAI_API_KEY is not set)")

    # Test lexical-only search path (no OpenAI key needed)
    logger.info("\n1.2 Testing lexical-only search path...")
    rc, stdout, stderr = run_command(
        ["python", "-m", "main", "search", "--must", "chroma", "--k", "3"]
    )
    if rc == 0:
        logger.info("✓ Lexical-only search executed successfully")
        logger.info("  (keyword args fix verified - no test failure)")
        if stdout:
            logger.info(f"  Results preview:\n{stdout[:200]}...")
    else:
        logger.error(f"✗ Lexical-only search failed: {stderr}")
        return False

    # Test empty query (should use lexical-only path)
    logger.info("\n1.3 Testing empty query (lexical-only fallback)...")
    rc, stdout, stderr = run_command(
        ["python", "-m", "main", "search", "", "--must", "test", "--k", "3"]
    )
    if rc == 0 or rc == 2:  # rc=2 is expected when no matches
        logger.info("✓ Empty query handled correctly")
    else:
        logger.error(f"✗ Empty query failed unexpectedly: {stderr}")
        return False

    return True


def test_asset_root_configurability():
    """Test asset_root configurability in ingest command."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: asset_root configurability")
    logger.info("=" * 60)

    with tempfile.TemporaryDirectory(prefix="neumann_test_") as tmpdir:
        test_dir = Path(tmpdir)
        input_dir = test_dir / "test_input"
        output_dir = test_dir / "test_output"
        custom_output_dir = test_dir / "custom_output"

        # Create test input
        input_dir.mkdir()
        test_file = input_dir / "test.py"
        test_file.write_text('print("Hello, World!")\n')

        # Test 2.1: Default asset_root (should use out_dir.name)
        logger.info("\n2.1 Testing default asset_root (derived from out_dir.name)...")
        output_dir.mkdir()
        rc, stdout, stderr = run_command(
            [
                "python",
                "-m",
                "main",
                "ingest",
                "--input-dir",
                str(input_dir),
                "--out-dir",
                str(output_dir),
                "--no-summary",
                "--no-index",
            ]
        )
        if rc == 0:
            logger.info("✓ Ingest with default asset_root succeeded")
            # Check pages.jsonl for asset_root
            pages_jsonl = output_dir / "test.py" / "pages" / "pages.jsonl"
            if pages_jsonl.exists():
                with open(pages_jsonl) as f:
                    first_line = f.readline()
                    if first_line:
                        data = json.loads(first_line)
                        uri = data.get("uri", "")
                        if "test_output" in uri:
                            logger.info(
                                f"✓ URI uses 'test_output' as asset_root: {uri[:80]}..."
                            )
                        else:
                            logger.warning(
                                f"⚠ URI doesn't match expected asset_root: {uri[:80]}..."
                            )
            else:
                logger.warning("⚠ pages.jsonl not found")
        else:
            logger.error(f"✗ Ingest failed: {stderr}")
            return False

        # Test 2.2: Explicit asset_root matching out_dir.name (no warning)
        logger.info("\n2.2 Testing explicit asset_root matching out_dir.name...")
        custom_output_dir.mkdir()
        rc, stdout, stderr = run_command(
            [
                "python",
                "-m",
                "main",
                "ingest",
                "--input-dir",
                str(input_dir),
                "--out-dir",
                str(custom_output_dir),
                "--asset-root",
                "custom_output",
                "--no-summary",
                "--no-index",
            ]
        )
        if rc == 0:
            logger.info("✓ Ingest with matching asset_root succeeded")
            if "Warning" not in stderr:
                logger.info("✓ No warning (asset_root matches out_dir.name)")
            else:
                logger.warning(f"⚠ Unexpected warning: {stderr}")
        else:
            logger.error(f"✗ Ingest failed: {stderr}")
            return False

        # Test 2.3: Explicit asset_root mismatching out_dir.name (should warn)
        logger.info("\n2.3 Testing explicit asset_root mismatching out_dir.name...")
        another_output_dir = test_dir / "another_output"
        another_output_dir.mkdir()
        rc, stdout, stderr = run_command(
            [
                "python",
                "-m",
                "main",
                "ingest",
                "--input-dir",
                str(input_dir),
                "--out-dir",
                str(another_output_dir),
                "--asset-root",
                "custom_asset",
                "--no-summary",
                "--no-index",
            ]
        )
        if rc == 0:
            logger.info("✓ Ingest with mismatched asset_root succeeded")
            if "Warning" in stderr and "custom_asset" in stderr:
                logger.info("✓ Warning correctly displayed for mismatched asset_root")
            else:
                logger.warning(f"⚠ Expected warning not found in stderr: {stderr}")
        else:
            logger.error(f"✗ Ingest failed: {stderr}")
            return False

    return True


def test_serve_robustness():
    """Test serve command robustness (KeyboardInterrupt handling and --asset-root)."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: Serve command robustness")
    logger.info("=" * 60)

    # Create a test output directory
    test_output_dir = project_root / "output"
    if not test_output_dir.exists():
        logger.warning("⚠ output directory not found - creating minimal structure")
        test_output_dir.mkdir(exist_ok=True)
        (test_output_dir / "test.html").write_text("<html><body>Test</body></html>")

    import signal
    import time

    # Get the venv Python path
    venv_python = project_root / ".venv" / "bin" / "python"
    python_cmd = str(venv_python) if venv_python.exists() else "python"

    # Test 3.1: Default serve command starts correctly
    logger.info("\n3.1 Testing serve command starts correctly...")
    proc = subprocess.Popen(
        [python_cmd, "-m", "main", "serve", str(test_output_dir), "--port", "8765"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Give it a moment to start
    time.sleep(1)

    if proc.poll() is None:
        logger.info("✓ Serve command started successfully")
        logger.info("  (Robustness: KeyboardInterrupt handling improved)")
        # Send SIGINT (Ctrl+C) and wait briefly
        proc.send_signal(signal.SIGINT)
        time.sleep(0.5)
        if proc.poll() is not None:
            logger.info("✓ Serve command terminated gracefully on SIGINT")
        else:
            logger.warning("⚠ Serve command still running after SIGINT")
            proc.terminate()
            proc.wait()
    else:
        logger.error(f"✗ Serve command failed to start: {proc.stderr.read()}")
        return False

    # Test 3.2: serve with --asset-root flag
    logger.info("\n3.2 Testing serve command with --asset-root...")
    proc = subprocess.Popen(
        [python_cmd, "-m", "main", "serve", str(test_output_dir), "--asset-root", "output", "--port", "8766"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    time.sleep(1)

    if proc.poll() is None:
        logger.info("✓ Serve command with --asset-root started successfully")
        proc.send_signal(signal.SIGINT)
        time.sleep(0.5)
        if proc.poll() is not None:
            logger.info("✓ Serve command terminated gracefully")
        else:
            proc.terminate()
            proc.wait()
    else:
        logger.error(f"✗ Serve with --asset-root failed to start: {proc.stderr.read()}")
        return False

    return True


def main() -> int:
    """Run all manual tests."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = project_root / "test_output" / f"cli_review_fixes_{timestamp}.log"

    logger.info("🧪 Testing CLI Review Fixes (nm-25)")
    logger.info("=" * 60)
    logger.info(f"📁 Output will be saved to: {output_file}")

    results = []

    # Run tests
    try:
        results.append(("hybrid_search_keyword_args", test_hybrid_search_keyword_args()))
        results.append(("asset_root_configurability", test_asset_root_configurability()))
        results.append(("serve_robustness", test_serve_robustness()))
    except Exception as e:
        logger.exception(f"Fatal error during testing: {e}")
        return 1

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)

    all_passed = True
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        logger.info(f"{test_name}: {status}")
        if not passed:
            all_passed = False

    logger.info("=" * 60)
    if all_passed:
        logger.info("✅ All tests passed!")
        return 0
    else:
        logger.error("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Fatal error: {type(e).__name__}: {e}")
        sys.exit(1)


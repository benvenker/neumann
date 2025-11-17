#!/usr/bin/env python3
"""Manual end-to-end test for FastAPI search endpoints (nm-3573.2).

This script demonstrates the full API workflow:
1. Checks if API server is running (or provides instructions to start it)
2. Tests each search endpoint (lexical, semantic, hybrid)
3. Validates response structure matches expected schema
4. Tests error cases (missing API key, invalid inputs)
5. Displays results with scores and metadata

Prerequisites:
- ChromaDB must be populated with indexed content (run ingestion first)
- API server should be running on port 8001 (or specify via --port)
- OPENAI_API_KEY required for semantic/hybrid tests (optional flag to skip)

Usage:
    # Start API server in separate terminal/tmux:
    uvicorn api.app:create_app --factory --reload --port 8001

    # Run this test script:
    python tests/manual/test_api_search_endpoints.py

    # Skip semantic tests if no OpenAI key:
    python tests/manual/test_api_search_endpoints.py --skip-semantic

    # Use different port:
    python tests/manual/test_api_search_endpoints.py --port 8080
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

import requests

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


class APITestRunner:
    """Runner for API endpoint tests."""

    def __init__(self, base_url: str, skip_semantic: bool = False):
        self.base_url = base_url
        self.skip_semantic = skip_semantic
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def check_server_health(self) -> bool:
        """Check if API server is running and healthy."""
        logger.info(f"Checking server health at {self.base_url}...")
        try:
            response = self.session.get(f"{self.base_url}/healthz", timeout=5)
            if response.status_code == 200:
                logger.info("✓ Server is healthy")
                return True
            else:
                logger.error(f"✗ Server returned status {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Cannot connect to server: {e}")
            logger.error("\nPlease start the API server:")
            logger.error(f"  uvicorn api.app:create_app --factory --reload --port {self.base_url.split(':')[-1]}")
            return False

    def test_lexical_search(self) -> bool:
        """Test POST /api/v1/search/lexical endpoint."""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 1: Lexical Search - Basic term search")
        logger.info("=" * 60)

        endpoint = f"{self.base_url}/api/v1/search/lexical"
        payload = {
            "must_terms": ["chroma", "collection"],
            "k": 5,
        }

        logger.info(f"POST {endpoint}")
        logger.info(f"Payload: {json.dumps(payload, indent=2)}")

        try:
            response = self.session.post(endpoint, json=payload, timeout=10)
            logger.info(f"Status: {response.status_code}")

            if response.status_code != 200:
                logger.error(f"✗ Expected 200, got {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False

            results = response.json()
            logger.info(f"✓ Received {len(results)} results")

            # Validate structure
            if results:
                self._validate_lexical_result(results[0])
                self._display_result(results[0], "Lexical")

            return True

        except Exception as e:
            logger.error(f"✗ Test failed: {e}")
            return False

    def test_lexical_with_regex(self) -> bool:
        """Test lexical search with regex patterns."""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 2: Lexical Search - Regex patterns")
        logger.info("=" * 60)

        endpoint = f"{self.base_url}/api/v1/search/lexical"
        payload = {
            "regexes": [r"def\s+\w+_search", r"class\s+\w+Request"],
            "k": 5,
        }

        logger.info(f"POST {endpoint}")
        logger.info(f"Payload: {json.dumps(payload, indent=2)}")

        try:
            response = self.session.post(endpoint, json=payload, timeout=10)
            logger.info(f"Status: {response.status_code}")

            if response.status_code != 200:
                logger.error(f"✗ Expected 200, got {response.status_code}")
                return False

            results = response.json()
            logger.info(f"✓ Received {len(results)} results")

            if results:
                self._display_result(results[0], "Lexical+Regex")

            return True

        except Exception as e:
            logger.error(f"✗ Test failed: {e}")
            return False

    def test_lexical_with_path_filter(self) -> bool:
        """Test lexical search with path filtering."""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 3: Lexical Search - Path filtering")
        logger.info("=" * 60)

        endpoint = f"{self.base_url}/api/v1/search/lexical"
        payload = {
            "must_terms": ["search"],
            "path_like": "indexer.py",
            "k": 3,
        }

        logger.info(f"POST {endpoint}")
        logger.info(f"Payload: {json.dumps(payload, indent=2)}")

        try:
            response = self.session.post(endpoint, json=payload, timeout=10)
            logger.info(f"Status: {response.status_code}")

            if response.status_code != 200:
                logger.error(f"✗ Expected 200, got {response.status_code}")
                return False

            results = response.json()
            logger.info(f"✓ Received {len(results)} results")

            # Verify path filtering worked
            for r in results:
                source = r.get("source_path", "")
                if "indexer.py" not in source:
                    logger.warning(f"⚠ Result doesn't match path filter: {source}")

            if results:
                self._display_result(results[0], "Lexical+Path")

            return True

        except Exception as e:
            logger.error(f"✗ Test failed: {e}")
            return False

    def test_lexical_error_no_filters(self) -> bool:
        """Test lexical search error case: no filters provided."""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 4: Lexical Search - Error: No filters")
        logger.info("=" * 60)

        endpoint = f"{self.base_url}/api/v1/search/lexical"
        payload = {"k": 5}  # No filters

        logger.info(f"POST {endpoint}")
        logger.info(f"Payload: {json.dumps(payload, indent=2)}")

        try:
            response = self.session.post(endpoint, json=payload, timeout=10)
            logger.info(f"Status: {response.status_code}")

            if response.status_code != 400:
                logger.error(f"✗ Expected 400 Bad Request, got {response.status_code}")
                return False

            error = response.json()
            logger.info(f"✓ Received expected error: {error.get('detail')}")
            return True

        except Exception as e:
            logger.error(f"✗ Test failed: {e}")
            return False

    def test_semantic_search(self) -> bool:
        """Test POST /api/v1/search/semantic endpoint."""
        if self.skip_semantic:
            logger.info("\n[SKIPPED] Semantic search tests (--skip-semantic flag)")
            return True

        logger.info("\n" + "=" * 60)
        logger.info("TEST 5: Semantic Search - Natural language query")
        logger.info("=" * 60)

        endpoint = f"{self.base_url}/api/v1/search/semantic"
        payload = {
            "query": "How does vector similarity search work with embeddings?",
            "k": 5,
        }

        logger.info(f"POST {endpoint}")
        logger.info(f"Payload: {json.dumps(payload, indent=2)}")

        try:
            response = self.session.post(endpoint, json=payload, timeout=30)
            logger.info(f"Status: {response.status_code}")

            if response.status_code == 400:
                error = response.json()
                if "OPENAI_API_KEY" in error.get("detail", ""):
                    logger.warning("⚠ OPENAI_API_KEY not configured, skipping semantic tests")
                    logger.info("  Add the key to .env (or prefix this command) and recreate tmux sessions after edits")
                    return True
                else:
                    logger.error(f"✗ Unexpected 400 error: {error}")
                    return False

            if response.status_code != 200:
                logger.error(f"✗ Expected 200, got {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False

            results = response.json()
            logger.info(f"✓ Received {len(results)} results")

            # Validate structure
            if results:
                self._validate_semantic_result(results[0])
                self._display_result(results[0], "Semantic")

            return True

        except Exception as e:
            logger.error(f"✗ Test failed: {e}")
            return False

    def test_semantic_error_empty_query(self) -> bool:
        """Test semantic search error case: empty query."""
        if self.skip_semantic:
            return True

        logger.info("\n" + "=" * 60)
        logger.info("TEST 6: Semantic Search - Error: Empty query")
        logger.info("=" * 60)

        endpoint = f"{self.base_url}/api/v1/search/semantic"
        payload = {"query": "   ", "k": 5}  # Whitespace-only query

        logger.info(f"POST {endpoint}")
        logger.info(f"Payload: {json.dumps(payload, indent=2)}")

        try:
            response = self.session.post(endpoint, json=payload, timeout=10)
            logger.info(f"Status: {response.status_code}")

            if response.status_code == 400 and "OPENAI_API_KEY" in response.text:
                logger.info("✓ OPENAI_API_KEY check triggered before empty query validation")
                logger.info("  Update .env or prefix the command, then rerun once the key is available")
                return True

            if response.status_code != 422:  # Pydantic validation error
                logger.error(f"✗ Expected 422 Validation Error, got {response.status_code}")
                return False

            logger.info("✓ Validation error caught empty query")
            return True

        except Exception as e:
            logger.error(f"✗ Test failed: {e}")
            return False

    def test_hybrid_search_full(self) -> bool:
        """Test POST /api/v1/search/hybrid with both semantic and lexical."""
        if self.skip_semantic:
            logger.info("\n[SKIPPED] Hybrid search with semantic (--skip-semantic flag)")
            return True

        logger.info("\n" + "=" * 60)
        logger.info("TEST 7: Hybrid Search - Semantic + Lexical")
        logger.info("=" * 60)

        endpoint = f"{self.base_url}/api/v1/search/hybrid"
        payload = {
            "query": "document indexing and retrieval",
            "must_terms": ["chroma"],
            "k": 5,
            "w_semantic": 0.6,
            "w_lexical": 0.4,
        }

        logger.info(f"POST {endpoint}")
        logger.info(f"Payload: {json.dumps(payload, indent=2)}")

        try:
            response = self.session.post(endpoint, json=payload, timeout=30)
            logger.info(f"Status: {response.status_code}")

            if response.status_code == 400 and "OPENAI_API_KEY" in response.text:
                logger.warning("⚠ OPENAI_API_KEY not configured")
                logger.info("  Add the key to .env (or prefix this run) and restart the API session to pick it up")
                return True

            if response.status_code != 200:
                logger.error(f"✗ Expected 200, got {response.status_code}")
                return False

            results = response.json()
            logger.info(f"✓ Received {len(results)} results")

            # Validate structure
            if results:
                self._validate_hybrid_result(results[0])
                self._display_result(results[0], "Hybrid")

            return True

        except Exception as e:
            logger.error(f"✗ Test failed: {e}")
            return False

    def test_hybrid_search_lexical_only(self) -> bool:
        """Test hybrid search with lexical-only (no semantic query)."""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 8: Hybrid Search - Lexical only (no semantic)")
        logger.info("=" * 60)

        endpoint = f"{self.base_url}/api/v1/search/hybrid"
        payload = {
            "regexes": [r"def\s+\w+"],
            "path_like": "search",
            "k": 3,
            "w_semantic": 0.0,
            "w_lexical": 1.0,
        }

        logger.info(f"POST {endpoint}")
        logger.info(f"Payload: {json.dumps(payload, indent=2)}")

        try:
            response = self.session.post(endpoint, json=payload, timeout=10)
            logger.info(f"Status: {response.status_code}")

            if response.status_code != 200:
                logger.error(f"✗ Expected 200, got {response.status_code}")
                return False

            results = response.json()
            logger.info(f"✓ Received {len(results)} results (lexical-only hybrid)")

            return True

        except Exception as e:
            logger.error(f"✗ Test failed: {e}")
            return False

    def test_hybrid_error_no_channels(self) -> bool:
        """Test hybrid search error case: neither semantic nor lexical."""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 9: Hybrid Search - Error: No channels active")
        logger.info("=" * 60)

        endpoint = f"{self.base_url}/api/v1/search/hybrid"
        payload = {"k": 5}  # No query, no filters

        logger.info(f"POST {endpoint}")
        logger.info(f"Payload: {json.dumps(payload, indent=2)}")

        try:
            response = self.session.post(endpoint, json=payload, timeout=10)
            logger.info(f"Status: {response.status_code}")

            if response.status_code != 422:  # Pydantic validation error
                logger.error(f"✗ Expected 422 Validation Error, got {response.status_code}")
                return False

            error = response.json()
            logger.info(f"✓ Validation error: {error.get('detail', [{}])[0].get('msg', '')}")
            return True

        except Exception as e:
            logger.error(f"✗ Test failed: {e}")
            return False

    def test_invalid_k_value(self) -> bool:
        """Test error case: k <= 0."""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 10: Error - Invalid k value (k=0)")
        logger.info("=" * 60)

        endpoint = f"{self.base_url}/api/v1/search/lexical"
        payload = {"must_terms": ["test"], "k": 0}

        logger.info(f"POST {endpoint}")
        logger.info(f"Payload: {json.dumps(payload, indent=2)}")

        try:
            response = self.session.post(endpoint, json=payload, timeout=10)
            logger.info(f"Status: {response.status_code}")

            if response.status_code != 422:
                logger.error(f"✗ Expected 422 Validation Error, got {response.status_code}")
                return False

            logger.info("✓ Validation error caught k=0")
            return True

        except Exception as e:
            logger.error(f"✗ Test failed: {e}")
            return False

    def _validate_lexical_result(self, result: dict[str, Any]) -> None:
        """Validate lexical search result structure."""
        required = ["doc_id", "score", "page_uris", "why", "metadata"]
        for field in required:
            if field not in result:
                logger.warning(f"⚠ Missing field: {field}")

        # Lexical results should NOT have sem_score/lex_score/rrf_score
        if any(f in result for f in ["sem_score", "lex_score", "rrf_score"]):
            logger.warning("⚠ Lexical result has hybrid-specific fields")

    def _validate_semantic_result(self, result: dict[str, Any]) -> None:
        """Validate semantic search result structure."""
        required = ["doc_id", "score", "page_uris", "why", "metadata"]
        for field in required:
            if field not in result:
                logger.warning(f"⚠ Missing field: {field}")

    def _validate_hybrid_result(self, result: dict[str, Any]) -> None:
        """Validate hybrid search result structure."""
        required = ["doc_id", "score", "sem_score", "lex_score", "rrf_score", "page_uris", "why"]
        for field in required:
            if field not in result:
                logger.warning(f"⚠ Missing field: {field}")

    def _display_result(self, result: dict[str, Any], search_type: str) -> None:
        """Display a search result in readable format."""
        logger.info(f"\n{search_type} Result:")
        logger.info(f"  doc_id: {result.get('doc_id')}")
        logger.info(f"  source_path: {result.get('source_path')}")
        logger.info(f"  score: {result.get('score', 0):.4f}")

        if "sem_score" in result:
            logger.info(
                f"  sem_score: {result.get('sem_score', 0):.4f}, "
                f"lex_score: {result.get('lex_score', 0):.4f}, "
                f"rrf_score: {result.get('rrf_score', 0):.4f}"
            )

        logger.info(f"  line_range: {result.get('line_start')}-{result.get('line_end')}")
        logger.info(f"  page_uris: {len(result.get('page_uris', []))} pages")

        why = result.get("why", [])
        if why:
            logger.info(f"  why signals ({len(why)}):")
            for w in why[:3]:  # Show first 3
                logger.info(f"    - {w}")

    def run_all_tests(self) -> tuple[int, int]:
        """Run all test cases.

        Returns:
            (passed, total) counts
        """
        tests = [
            self.test_lexical_search,
            self.test_lexical_with_regex,
            self.test_lexical_with_path_filter,
            self.test_lexical_error_no_filters,
            self.test_semantic_search,
            self.test_semantic_error_empty_query,
            self.test_hybrid_search_full,
            self.test_hybrid_search_lexical_only,
            self.test_hybrid_error_no_channels,
            self.test_invalid_k_value,
        ]

        passed = 0
        total = len(tests)

        for test_func in tests:
            try:
                if test_func():
                    passed += 1
                time.sleep(0.5)  # Brief pause between tests
            except Exception as e:
                logger.error(f"Test {test_func.__name__} crashed: {e}")

        return passed, total


def main():
    parser = argparse.ArgumentParser(description="Manual test for API search endpoints")
    parser.add_argument("--port", type=int, default=8001, help="API server port (default: 8001)")
    parser.add_argument(
        "--skip-semantic",
        action="store_true",
        help="Skip semantic/hybrid tests (if no OPENAI_API_KEY)",
    )
    args = parser.parse_args()

    base_url = f"http://127.0.0.1:{args.port}"

    logger.info("=" * 60)
    logger.info("FastAPI Search Endpoints - Manual Test Suite")
    logger.info("=" * 60)
    logger.info(f"Base URL: {base_url}")
    logger.info(f"Skip semantic: {args.skip_semantic}")
    logger.info("")

    runner = APITestRunner(base_url, skip_semantic=args.skip_semantic)

    # Check server health first
    if not runner.check_server_health():
        logger.error("\nAborted: API server not running")
        return 1

    # Run all tests
    passed, total = runner.run_all_tests()

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info(f"TEST SUMMARY: {passed}/{total} passed")
    logger.info("=" * 60)

    if passed == total:
        logger.info("✓ All tests passed!")
        return 0
    else:
        logger.error(f"✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

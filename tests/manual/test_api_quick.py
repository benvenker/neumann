#!/usr/bin/env python3
"""Quick smoke test for API endpoints (nm-3573.2).

Minimal test script for rapid verification during development.
Just checks that endpoints are reachable and return valid responses.

Usage:
    # Start API server first:
    uvicorn backend.api.app:create_app --factory --reload --port 8001

    # Run quick test:
    python tests/manual/test_api_quick.py
"""

from __future__ import annotations

import sys

import requests

BASE_URL = "http://127.0.0.1:8001"


def test_health():
    """Test health endpoint."""
    print("Testing /healthz...", end=" ")
    r = requests.get(f"{BASE_URL}/healthz", timeout=5)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    print("✓")


def test_lexical():
    """Test lexical search endpoint."""
    print("Testing /api/v1/search/lexical...", end=" ")
    r = requests.post(
        f"{BASE_URL}/api/v1/search/lexical",
        json={"must_terms": ["search"], "k": 3},
        timeout=10,
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    results = r.json()
    assert isinstance(results, list), "Expected list response"
    print(f"✓ ({len(results)} results)")


def test_semantic():
    """Test semantic search endpoint."""
    print("Testing /api/v1/search/semantic...", end=" ")
    r = requests.post(
        f"{BASE_URL}/api/v1/search/semantic",
        json={"query": "vector search", "k": 3},
        timeout=30,
    )

    if r.status_code == 400 and "OPENAI_API_KEY" in r.text:
        print("⊘ (no API key) — add OPENAI_API_KEY to .env or prefix this command, then restart the API session")
        return

    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    results = r.json()
    assert isinstance(results, list), "Expected list response"
    print(f"✓ ({len(results)} results)")


def test_hybrid():
    """Test hybrid search endpoint."""
    print("Testing /api/v1/search/hybrid...", end=" ")
    r = requests.post(
        f"{BASE_URL}/api/v1/search/hybrid",
        json={"must_terms": ["search"], "k": 3},
        timeout=30,
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    results = r.json()
    assert isinstance(results, list), "Expected list response"
    print(f"✓ ({len(results)} results)")


def test_error_cases():
    """Test error handling."""
    print("Testing error cases...", end=" ")

    # No filters for lexical
    r = requests.post(f"{BASE_URL}/api/v1/search/lexical", json={"k": 5}, timeout=5)
    assert r.status_code == 400, "Expected 400 for no filters"

    # Invalid k
    r = requests.post(
        f"{BASE_URL}/api/v1/search/lexical",
        json={"must_terms": ["test"], "k": 0},
        timeout=5,
    )
    assert r.status_code == 422, "Expected 422 for invalid k"

    print("✓")


def main():
    print("API Quick Smoke Test")
    print("=" * 40)

    try:
        test_health()
        test_lexical()
        test_semantic()
        test_hybrid()
        test_error_cases()

        print("\n✓ All quick tests passed!")
        return 0

    except requests.exceptions.ConnectionError:
        print("\n✗ Cannot connect to API server")
        print("Start with: uvicorn backend.api.app:create_app --factory --reload --port 8001")
        return 1

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1

    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

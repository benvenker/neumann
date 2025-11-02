"""
Full-pipeline integration tests for NM-27.

Tests the complete flow: render → summarize → chunk → index → search
using a deterministic fixture corpus and mocked embeddings/summaries.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from chunker import load_page_uris
from config import config
from ids import make_doc_id
from indexer import (
    LEX_PATH_ONLY_BASELINE,
    get_client,
    hybrid_search,
    lexical_search,
    semantic_search,
    upsert_code_chunks,
    upsert_summaries,
)
from main import build_chunk_upsert_items, build_summary_upsert_item
from render_to_webp import RenderConfig, discover_sources, render_file
from summarize import summarize_file

# ============================================================================
# Deterministic Helper Functions
# ============================================================================


def nm27_embed(texts: Sequence[str]) -> list[list[float]]:
    """Deterministic embedding function for testing.

    Returns prototype vectors based on keyword detection:
    - AUTH prototype: texts containing 'auth' or 'authentication'
    - VECTOR prototype: texts containing 'vector store'
    - NEUTRAL prototype: everything else

    All vectors are 1536 dimensions to match text-embedding-3-small.
    """
    auth_vec = [0.1] * 100 + [0.9] * 1436
    vector_vec = [0.9] * 100 + [0.1] * 1436
    neutral = [0.5] * 1536

    out = []
    for t in texts:
        s = (t or "").lower()
        if "vector store" in s:
            out.append(vector_vec)
        elif "auth" in s or "authentication" in s:
            out.append(auth_vec)
        else:
            out.append(neutral)
    return out


def nm27_summary_gen(prompt_plus_text: str) -> str:
    """Deterministic summary generator for testing.

    Produces exactly 210 words with keywords matching the input content.
    Summaries will map to expected embedding prototypes via nm27_embed.
    """
    lower = (prompt_plus_text or "").lower()

    if "vector store" in lower:
        seed = "This summary covers vector store operations and embeddings for semantic search."
    elif "auth" in lower or "authentication" in lower:
        seed = "This summary covers authentication, login flows, and redirect URI handling."
    else:
        seed = "This summary covers general utilities and supporting functions."

    # Build exactly 210 words
    words = seed.split()
    while len(words) < 210:
        words.extend(seed.split())
    return " ".join(words[:210])


# ============================================================================
# Shared Fixture Setup
# ============================================================================


@pytest.fixture
def nm27_corpus_path() -> Path:
    """Return path to the nm27 fixture corpus."""
    return Path(__file__).parent / "fixtures" / "nm27_corpus"


@pytest.fixture
def nm27_ingested(tmp_path: Path, nm27_corpus_path: Path) -> dict[str, Any]:
    """Ingest the nm27 corpus and return paths and doc_id mapping.

    Returns a dict with:
    - out_dir: Path to output directory
    - chroma_path: Path to ChromaDB storage
    - doc_ids: List of doc_ids
    - doc_id_to_src: Mapping of doc_id -> source Path
    - client: ChromaDB client
    """
    out_dir = tmp_path / "out_nm27"
    chroma_path = tmp_path / "chroma_nm27"
    out_dir.mkdir()

    # Render config with reduced DPI/quality for speed
    cfg = RenderConfig(
        input_dir=nm27_corpus_path,
        emit="pages",
        manifest="none",
        dpi=150,
        webp_quality=70,
        asset_root=out_dir.name,
    )

    # Discover sources
    sources = discover_sources(nm27_corpus_path)
    assert len(sources) >= 3, f"Expected at least 3 fixtures, found {len(sources)}"

    # Initialize ChromaDB client
    client = get_client(str(chroma_path))

    # Process each file
    summary_items = []
    chunk_items_all = []
    doc_ids = []
    doc_id_to_src = {}

    for src in sources:
        # Compute canonical doc_id
        doc_id = make_doc_id(src, input_root=nm27_corpus_path)
        doc_ids.append(doc_id)
        doc_id_to_src[doc_id] = src

        # 1. Render
        render_file(src, out_dir, cfg)

        # 2. Load raw text and page URIs
        raw_text = src.read_text(encoding="utf-8", errors="ignore")
        pages_jsonl = out_dir / doc_id / "pages" / "pages.jsonl"
        page_uris = load_page_uris(pages_jsonl)

        # 3. Summarize with deterministic generator
        fs = summarize_file(str(src), raw_text, llm_generate_markdown=nm27_summary_gen)
        # Override doc_id to ensure consistency with renderer
        fs.front_matter.doc_id = doc_id
        summary_item = build_summary_upsert_item(fs, doc_id, page_uris)
        summary_items.append(summary_item)

        # 4. Chunk
        chunk_items = build_chunk_upsert_items(raw_text, src, doc_id, pages_jsonl)
        chunk_items_all.extend(chunk_items)

    # 5. Index
    upsert_summaries(summary_items, client=client, embedding_function=nm27_embed)
    upsert_code_chunks(chunk_items_all, client=client)

    return {
        "out_dir": out_dir,
        "chroma_path": chroma_path,
        "doc_ids": doc_ids,
        "doc_id_to_src": doc_id_to_src,
        "client": client,
        "corpus_path": nm27_corpus_path,
    }


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.integration
def test_nm27_full_pipeline_ingest_and_manifests(nm27_ingested: dict[str, Any]) -> None:
    """Validate render + summarize + chunk + index structure and pages.jsonl schema/URIs."""
    out_dir = nm27_ingested["out_dir"]
    doc_ids = nm27_ingested["doc_ids"]

    for doc_id in doc_ids:
        # Check pages.jsonl exists
        pages_jsonl = out_dir / doc_id / "pages" / "pages.jsonl"
        assert pages_jsonl.exists(), f"pages.jsonl missing for {doc_id}"

        # Parse and validate one row
        lines = pages_jsonl.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) > 0, f"pages.jsonl is empty for {doc_id}"

        row = json.loads(lines[0])
        required_keys = {
            "doc_id",
            "page",
            "uri",
            "sha256",
            "bytes",
            "width",
            "height",
            "source_pdf",
            "source_file",
        }
        assert required_keys.issubset(row.keys()), f"Missing keys in pages.jsonl row: {required_keys - row.keys()}"

        # Validate URI format
        uri = row["uri"]
        assert uri.startswith(str(config.ASSET_BASE_URL)), f"URI doesn't start with ASSET_BASE_URL: {uri}"
        # URI should match pattern: /{out_dir.name}/{doc_id}/pages/{stem}-p{page}.webp
        uri_pattern = rf"/{out_dir.name}/{re.escape(doc_id)}/pages/.*-p\d{{3}}\.webp$"
        assert re.search(uri_pattern, uri), f"URI doesn't match expected pattern: {uri}"


@pytest.mark.integration
def test_nm27_lexical_search_integration(nm27_ingested: dict[str, Any]) -> None:
    """Validate lexical filters (must_terms, regexes, path_like), why signals, and ordering."""
    client = nm27_ingested["client"]

    # Query with all lexical filters targeting auth.ts
    results = lexical_search(
        must_terms=["redirect_uri"],
        regexes=[r"authUser"],
        path_like="auth.ts",
        k=5,
        client=client,
    )

    # Should have at least one result
    assert len(results) > 0, "Expected at least one lexical result"

    # First result should be from auth.ts
    first = results[0]
    assert "auth" in first["doc_id"].lower(), f"Expected auth doc_id, got {first['doc_id']}"

    # Validate why signals
    why = first.get("why", [])
    why_str = " ".join(why).lower()
    assert "redirect_uri" in why_str, f"Expected 'redirect_uri' in why: {why}"
    assert "authuser" in why_str, f"Expected 'authUser' in why: {why}"
    assert "auth.ts" in why_str, f"Expected 'auth.ts' in why: {why}"

    # Validate structure
    assert first["score"] > 0, "Expected positive lexical score"
    assert isinstance(first.get("page_uris"), list), "page_uris should be a list"
    assert isinstance(first.get("line_start"), int), "line_start should be an integer"
    assert isinstance(first.get("line_end"), int), "line_end should be an integer"


@pytest.mark.integration
def test_nm27_semantic_search_integration(nm27_ingested: dict[str, Any]) -> None:
    """Validate semantic search with deterministic embeddings for auth and vector queries."""
    client = nm27_ingested["client"]

    # Query 1: "authentication" should match auth.ts
    auth_results = semantic_search("authentication", k=3, client=client, embedding_function=nm27_embed)
    assert len(auth_results) > 0, "Expected results for 'authentication' query"

    # Find auth doc in results
    auth_doc = None
    for r in auth_results:
        if "auth" in r["doc_id"].lower():
            auth_doc = r
            break
    assert auth_doc is not None, "Expected to find auth.ts in authentication results"

    # Validate structure
    assert 0.0 <= auth_doc["score"] <= 1.0, f"Score out of range: {auth_doc['score']}"
    assert auth_doc["line_start"] is None, "Summaries should have line_start=None"
    assert auth_doc["line_end"] is None, "Summaries should have line_end=None"
    assert isinstance(auth_doc.get("page_uris"), list), "page_uris should be a list"

    why = auth_doc.get("why", [])
    why_str = " ".join(why).lower()
    assert "semantic match" in why_str, f"Expected 'semantic match' in why: {why}"
    assert "authentication" in why_str, f"Expected 'authentication' in why: {why}"

    # Query 2: "vector store" should match vector.md
    vector_results = semantic_search("vector store", k=3, client=client, embedding_function=nm27_embed)
    assert len(vector_results) > 0, "Expected results for 'vector store' query"

    # Find vector doc in results
    vector_doc = None
    for r in vector_results:
        if "vector" in r["doc_id"].lower():
            vector_doc = r
            break
    assert vector_doc is not None, "Expected to find vector.md in 'vector store' results"

    # Validate structure
    assert 0.0 <= vector_doc["score"] <= 1.0, f"Score out of range: {vector_doc['score']}"
    why_vec = " ".join(vector_doc.get("why", [])).lower()
    assert "semantic match" in why_vec, f"Expected 'semantic match' in why: {vector_doc['why']}"


@pytest.mark.integration
def test_nm27_hybrid_search_integration(nm27_ingested: dict[str, Any]) -> None:
    """Validate fusion, weighted scoring, page_uris union, and combined why signals."""
    client = nm27_ingested["client"]

    # Hybrid query targeting auth.ts with both channels
    results = hybrid_search(
        query="authentication",
        must_terms=["redirect_uri"],
        path_like="auth.ts",
        k=5,
        client=client,
        embedding_function=nm27_embed,
    )

    assert len(results) > 0, "Expected at least one hybrid result"

    # Find auth doc
    auth_result = None
    for r in results:
        if "auth" in r["doc_id"].lower():
            auth_result = r
            break
    assert auth_result is not None, "Expected to find auth.ts in hybrid results"

    # Validate dual scoring
    sem_score = auth_result.get("sem_score", 0.0)
    lex_score = auth_result.get("lex_score", 0.0)
    score = auth_result.get("score", 0.0)

    assert sem_score > 0, "Expected positive semantic score"
    assert lex_score > 0, "Expected positive lexical score"

    # Validate weighted sum (0.6 * sem + 0.4 * lex)
    expected_score = 0.6 * sem_score + 0.4 * lex_score
    assert abs(score - expected_score) < 0.01, f"Expected score={expected_score:.3f}, got {score:.3f}"

    # Validate page_uris is a merged list (no duplicates)
    page_uris = auth_result.get("page_uris", [])
    assert isinstance(page_uris, list), "page_uris should be a list"
    assert len(page_uris) == len(set(page_uris)), "page_uris should have no duplicates"

    # line_start/line_end should come from lexical side (not None)
    assert auth_result.get("line_start") is not None, "Expected line_start from lexical"
    assert auth_result.get("line_end") is not None, "Expected line_end from lexical"

    # Why should include both lexical and semantic messages
    why = auth_result.get("why", [])
    why_str = " ".join(why).lower()
    assert "redirect_uri" in why_str or "matched term" in why_str, f"Expected lexical why: {why}"
    assert "semantic match" in why_str or "authentication" in why_str, f"Expected semantic why: {why}"


@pytest.mark.integration
def test_nm27_path_only_baseline_hybrid(nm27_ingested: dict[str, Any]) -> None:
    """Validate path-only baseline contribution to hybrid fusion."""
    client = nm27_ingested["client"]

    # Query with semantic + path-like only (no must_terms/regex)
    results = hybrid_search(
        query="authentication",
        path_like="auth.ts",
        k=5,
        client=client,
        embedding_function=nm27_embed,
    )

    assert len(results) > 0, "Expected at least one result for path-only hybrid"

    # Find auth doc
    auth_result = None
    for r in results:
        if "auth" in r["doc_id"].lower():
            auth_result = r
            break
    assert auth_result is not None, "Expected to find auth.ts in results"

    # Lexical score should be at least the path-only baseline
    lex_score = auth_result.get("lex_score", 0.0)
    assert lex_score >= LEX_PATH_ONLY_BASELINE, f"Expected lex_score >= {LEX_PATH_ONLY_BASELINE}, got {lex_score}"

    # Combined score should reflect both channels
    sem_score = auth_result.get("sem_score", 0.0)
    score = auth_result.get("score", 0.0)
    # Combined should be greater than just semantic (lexical baseline contributed)
    assert score > 0.6 * sem_score, f"Expected combined score > 0.6*{sem_score}, got {score}"

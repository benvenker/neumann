"""Unit tests for language metadata backward compatibility."""

from collections.abc import Sequence

from indexer import (
    get_client,
    lexical_search,
    semantic_search,
    upsert_code_chunks,
    upsert_summaries,
)


def fake_embed(texts: Sequence[str]) -> list[list[float]]:
    """Returns 1536-d zero vectors (avoids API calls)."""
    return [[0.0] * 1536 for _ in texts]


def _make_items_lang():
    """Items with canonical 'lang' key."""
    summary = {
        "id": "doc_lang_ts",
        "document": "Authentication module overview",
        "metadata": {
            "doc_id": "doc_lang_ts",
            "source_path": "app/auth.ts",
            "lang": "ts",
            "page_uris": ["http://x/p.webp"],
        },
    }
    chunk = {
        "id": "doc_lang_ts#L1-2",
        "document": "redirect_uri authUser",
        "metadata": {
            "doc_id": "doc_lang_ts",
            "source_path": "app/auth.ts",
            "lang": "ts",
            "line_start": 1,
            "line_end": 2,
            "page_uris": [],
        },
    }
    return summary, chunk


def _make_items_language():
    """Items with legacy 'language' key."""
    summary = {
        "id": "doc_language_ts",
        "document": "Authentication module overview",
        "metadata": {
            "doc_id": "doc_language_ts",
            "source_path": "app/auth.ts",
            "language": "ts",
            "page_uris": ["http://x/p.webp"],
        },
    }
    chunk = {
        "id": "doc_language_ts#L1-2",
        "document": "redirect_uri authUser",
        "metadata": {
            "doc_id": "doc_language_ts",
            "source_path": "app/auth.ts",
            "language": "ts",
            "line_start": 1,
            "line_end": 2,
            "page_uris": [],
        },
    }
    return summary, chunk


def _make_items_both_keys():
    """Items with both 'lang' and 'language' keys (edge case)."""
    summary = {
        "id": "doc_both_ts",
        "document": "Authentication module overview",
        "metadata": {
            "doc_id": "doc_both_ts",
            "source_path": "app/auth.ts",
            "lang": "ts",
            "language": "ts",
            "page_uris": ["http://x/p.webp"],
        },
    }
    chunk = {
        "id": "doc_both_ts#L1-2",
        "document": "redirect_uri authUser",
        "metadata": {
            "doc_id": "doc_both_ts",
            "source_path": "app/auth.ts",
            "lang": "ts",
            "language": "ts",
            "line_start": 1,
            "line_end": 2,
            "page_uris": [],
        },
    }
    return summary, chunk


def test_language_mapped_from_lang_for_both_channels(tmp_path):
    """Verify metadata.language exposed when data stores 'lang'."""
    client = get_client(str(tmp_path / "chroma_lang"))
    summary, chunk = _make_items_lang()

    upsert_summaries([summary], client=client, embedding_function=fake_embed)
    upsert_code_chunks([chunk], client=client)

    sem = semantic_search("anything", k=3, client=client, embedding_function=fake_embed)
    lex = lexical_search(must_terms=["redirect_uri"], k=3, client=client)

    # Semantic channel
    assert sem and sem[0]["metadata"].get("language") == "ts"
    assert "lang" not in sem[0]["metadata"]

    # Lexical channel
    assert lex and lex[0]["metadata"].get("language") == "ts"
    assert "lang" not in lex[0]["metadata"]


def test_language_mapped_from_legacy_language_for_both_channels(tmp_path):
    """Verify metadata.language exposed when data stores 'language'."""
    client = get_client(str(tmp_path / "chroma_language"))
    summary, chunk = _make_items_language()

    upsert_summaries([summary], client=client, embedding_function=fake_embed)
    upsert_code_chunks([chunk], client=client)

    sem = semantic_search("anything", k=3, client=client, embedding_function=fake_embed)
    lex = lexical_search(must_terms=["redirect_uri"], k=3, client=client)

    # Semantic channel
    assert sem and sem[0]["metadata"].get("language") == "ts"
    assert "lang" not in sem[0]["metadata"]

    # Lexical channel
    assert lex and lex[0]["metadata"].get("language") == "ts"
    assert "lang" not in lex[0]["metadata"]


def test_language_mapped_when_both_keys_present(tmp_path):
    """Verify metadata.language exposed when data has BOTH lang and language."""
    client = get_client(str(tmp_path / "chroma_both"))
    summary, chunk = _make_items_both_keys()

    upsert_summaries([summary], client=client, embedding_function=fake_embed)
    upsert_code_chunks([chunk], client=client)

    sem = semantic_search("anything", k=3, client=client, embedding_function=fake_embed)
    lex = lexical_search(must_terms=["redirect_uri"], k=3, client=client)

    # Semantic channel
    assert sem and sem[0]["metadata"].get("language") == "ts"
    assert "lang" not in sem[0]["metadata"]

    # Lexical channel
    assert lex and lex[0]["metadata"].get("language") == "ts"
    assert "lang" not in lex[0]["metadata"]

"""Unit tests for metadata normalization and hydration."""

from indexer import (
    NORMALIZED_META_LIST_KEYS,
    _normalize_metadata_for_chroma,
    _parse_meta_list,
)


def test_normalize_metadata_for_chroma_lists():
    """Test list normalization to comma-separated strings."""
    meta = {
        "list_field": ["a", "b", "c"],
        "empty_list": [],
        "single_item": ["x"],
    }
    out = _normalize_metadata_for_chroma(meta)
    assert out["list_field"] == "a,b,c"
    assert out["empty_list"] == ""
    assert out["single_item"] == "x"


def test_normalize_metadata_for_chroma_primitives():
    """Test primitives pass through unchanged."""
    meta = {
        "s": "str",
        "i": 1,
        "f": 1.5,
        "b": True,
        "n": None,
    }
    out = _normalize_metadata_for_chroma(meta)
    assert out["s"] == "str"
    assert out["i"] == 1
    assert out["f"] == 1.5
    assert out["b"] is True
    assert out["n"] is None


def test_normalize_metadata_for_chroma_non_primitives():
    """Test non-primitives are stringified."""
    from datetime import datetime

    meta = {
        "d": {"k": "v"},
        "dt": datetime(2025, 1, 1, 12, 0, 0),
    }
    out = _normalize_metadata_for_chroma(meta)
    assert isinstance(out["d"], str)
    assert "{" in out["d"] and "}" in out["d"]
    assert isinstance(out["dt"], str)
    assert "2025" in out["dt"]


def test_normalize_metadata_for_chroma_none_input():
    """Test None input returns empty dict."""
    assert _normalize_metadata_for_chroma(None) == {}
    assert _normalize_metadata_for_chroma({}) == {}


def test_parse_meta_list_from_string():
    """Test comma-separated string hydration."""
    assert _parse_meta_list("a,b,c") == ["a", "b", "c"]
    assert _parse_meta_list(" a , b ,  c ") == ["a", "b", "c"]
    assert _parse_meta_list("") == []
    assert _parse_meta_list("single") == ["single"]


def test_parse_meta_list_from_list():
    """Test list passthrough with deduplication."""
    assert _parse_meta_list(["a", "b", "c"]) == ["a", "b", "c"]
    assert _parse_meta_list(["a", "a", "b"]) == ["a", "b"]
    assert _parse_meta_list(["a", "", "b", ""]) == ["a", "b"]


def test_parse_meta_list_none_and_other():
    """Test None and non-string/list inputs."""
    assert _parse_meta_list(None) == []
    assert _parse_meta_list(123) == []
    assert _parse_meta_list({"k": "v"}) == []


def test_normalized_meta_list_keys_constant():
    """Validate NORMALIZED_META_LIST_KEYS includes expected keys."""
    expected = {
        "product_tags",
        "key_topics",
        "api_symbols",
        "related_files",
        "suggested_queries",
        "page_uris",
    }
    assert set(NORMALIZED_META_LIST_KEYS) == expected


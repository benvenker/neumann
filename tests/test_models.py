from datetime import datetime

import pytest

from backend.models import FileSummary, SummaryFrontMatter, ValidationError


def make_summary_md(words: int) -> str:
    return " ".join([f"word{i}" for i in range(words)])


def test_valid_summary_passes_validation() -> None:
    fm = SummaryFrontMatter(
        doc_id="docs__readme",
        source_path="README.md",
        language="markdown",
        product_tags=["neumann"],
        last_updated=datetime.utcnow(),
        key_topics=["rendering", "tiles"],
        api_symbols=[],
        related_files=["render_to_webp.py"],
        suggested_queries=["how to change tile size"],
    )
    fs = FileSummary(front_matter=fm, summary_md=make_summary_md(250))
    text = fs.to_yaml()
    assert text.startswith("---\n") and "summary_md" not in text.split("---\n")[1]
    assert fs.front_matter.doc_id == "docs__readme"


def test_short_summary_fails_validation() -> None:
    fm = SummaryFrontMatter(
        doc_id="d",
        source_path="f.py",
        language="python",
    )
    with pytest.raises(ValidationError):
        FileSummary(front_matter=fm, summary_md=make_summary_md(50))


def test_to_yaml_serialization_contains_expected_fields() -> None:
    fm = SummaryFrontMatter(
        doc_id="abc",
        source_path="src/module.py",
        language="python",
        product_tags=["core"],
        key_topics=["summaries"],
        api_symbols=["render_to_webp"],
        related_files=["render_to_webp.py"],
        suggested_queries=["tile overlap"],
    )
    fs = FileSummary(front_matter=fm, summary_md=make_summary_md(210))
    s = fs.to_yaml()
    # Front matter block then body
    parts = s.split("---\n")
    assert len(parts) >= 3
    fm_yaml = parts[1]
    assert "doc_id: abc" in fm_yaml
    assert "source_path: src/module.py" in fm_yaml

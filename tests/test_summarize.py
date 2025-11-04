from pathlib import Path

from summarize import (
    detect_language_from_extension,
    generate_doc_id_from_path,
    save_summary_md,
    summarize_file,
)


def make_body(words: int) -> str:
    return " ".join([f"w{i}" for i in range(words)])


def test_doc_id_generation() -> None:
    assert generate_doc_id_from_path("src/pkg/file.py") == "src__pkg__file.py"
    assert generate_doc_id_from_path("README.md") == "README.md"


def test_language_detection() -> None:
    assert detect_language_from_extension("foo.py") == "python"
    assert detect_language_from_extension("bar.ts") == "typescript"
    assert detect_language_from_extension("baz.unknown") == "text"


def test_summarize_generates_valid_summary(tmp_path: Path) -> None:
    source = "src/module.py"
    text = "print('hello')\n"

    def fake_llm(_: str) -> str:
        return make_body(210)

    fs = summarize_file(source, text, llm_generate_markdown=fake_llm)
    out = tmp_path / "module.summary.md"
    p = save_summary_md(out, fs)
    assert p.exists()
    content = p.read_text(encoding="utf-8")
    assert content.startswith("---\n")
    assert "doc_id:" in content and "language: python" in content
    assert fs.front_matter.min_summary_words is not None
    assert fs.front_matter.max_summary_words is not None
    assert fs.front_matter.source_word_count is not None


def test_summarize_raises_on_short_body() -> None:
    source = "docs/readme.md"
    text = "Some content"

    def short_llm(_: str) -> str:
        return make_body(60)

    import pytest

    from models import ValidationError

    with pytest.raises(ValidationError):
        summarize_file(source, text, llm_generate_markdown=short_llm)


import json
import pathlib
import tempfile

from render_to_webp import RenderConfig, render_file


def read_jsonl(path: pathlib.Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_pages_jsonl_emitted_with_required_fields():
    with tempfile.TemporaryDirectory() as tmpdir:
        input_dir = pathlib.Path(tmpdir) / "input"
        output_dir = pathlib.Path(tmpdir) / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        test_file = input_dir / "demo.md"
        test_file.write_text("# Title\n\nHello world.", encoding="utf-8")

        cfg = RenderConfig(input_dir=input_dir, emit="pages", manifest="none")
        render_file(test_file, output_dir, cfg)

        pages_dir = output_dir / "demo.md" / "pages"
        jpath = pages_dir / "pages.jsonl"
        assert jpath.exists(), "pages.jsonl must be emitted in pages/"

        rows = read_jsonl(jpath)
        assert len(rows) >= 1
        row = rows[0]
        for key in [
            "doc_id",
            "page",
            "uri",
            "sha256",
            "bytes",
            "width",
            "height",
            "source_pdf",
            "source_file",
        ]:
            assert key in row
        assert row["uri"].startswith("http://") or row["uri"].startswith("https://")


def test_uri_generation_format_matches_base_url():
    import re

    from config import config

    with tempfile.TemporaryDirectory() as tmpdir:
        input_dir = pathlib.Path(tmpdir) / "input"
        output_dir = pathlib.Path(tmpdir) / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        test_file = input_dir / "uri.md"
        test_file.write_text("Hello", encoding="utf-8")

        cfg = RenderConfig(input_dir=input_dir, emit="pages")
        render_file(test_file, output_dir, cfg)

        pages_dir = output_dir / "uri.md" / "pages"
        row = read_jsonl(pages_dir / "pages.jsonl")[0]
        assert row["uri"].startswith(str(config.ASSET_BASE_URL))
        assert re.search(r"/out/uri.md/pages/uri-p\d{3}\.webp$", row["uri"]) is not None


def test_dimensions_and_bytes_match_actual_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        input_dir = pathlib.Path(tmpdir) / "input"
        output_dir = pathlib.Path(tmpdir) / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        test_file = input_dir / "dims.md"
        test_file.write_text("# A\nB", encoding="utf-8")

        cfg = RenderConfig(input_dir=input_dir, emit="pages")
        render_file(test_file, output_dir, cfg)

        pages_dir = output_dir / "dims.md" / "pages"
        row = read_jsonl(pages_dir / "pages.jsonl")[0]
        wp = pages_dir / next(iter(p for p in (pages_dir.glob("*.webp"))))
        on_disk = wp.stat().st_size
        assert row["bytes"] == on_disk
        from PIL import Image
        with Image.open(wp) as im:
            w, h = im.size
        assert row["width"] == w and row["height"] == h

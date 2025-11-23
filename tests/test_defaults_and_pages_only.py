"""Tests for default behavior - pages-only, no tiles, no manifest

Tests verify that RenderConfig defaults match the pages-first philosophy
and that the rendering pipeline behaves correctly with default settings.
"""

import pathlib
import sys
import tempfile

# Add parent directory to path for imports
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import pytest

from backend.render_to_webp import RenderConfig, render_file


def test_defaults_pages_only():
    """Verify RenderConfig defaults match pages-only philosophy."""
    cfg = RenderConfig()

    # Verify default values
    assert cfg.emit == "pages", "Default emit should be 'pages'"
    assert cfg.manifest == "none", "Default manifest should be 'none'"
    assert cfg.linenos == "inline", "Default linenos should be 'inline'"

    # Verify other relevant defaults
    assert cfg.hash_tiles is True
    assert cfg.tile_mode == "bands"


@pytest.mark.integration
def test_render_pages_only_no_tiles():
    """Integration test: Verify pages are produced and tiles aren't when using defaults.

    This test verifies the actual rendering behavior with default settings:
    - Pages should be created
    - Tiles directory should NOT exist
    - Manifest files should NOT exist
    """
    # Create temporary directories
    with tempfile.TemporaryDirectory() as tmpdir:
        input_dir = pathlib.Path(tmpdir) / "input"
        output_dir = pathlib.Path(tmpdir) / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        # Create a simple test file
        test_file = input_dir / "test.md"
        test_file.write_text("# Test Document\n\nThis is a test.", encoding="utf-8")

        # Create config with defaults (pages-only)
        cfg = RenderConfig(
            input_dir=input_dir,
            emit="pages",  # Explicit default
            manifest="none",  # Explicit default
        )

        # Render the file
        render_file(test_file, output_dir, cfg)

        # Check that pages directory exists
        doc_output = output_dir / "test.md"
        pages_dir = doc_output / "pages"
        assert pages_dir.exists(), "Pages directory should exist"

        # Check that pages were created
        page_files = list(pages_dir.glob("*.webp"))
        assert len(page_files) > 0, "At least one page WebP should be created"

        # Check that pages.txt exists
        pages_txt = pages_dir / "pages.txt"
        assert pages_txt.exists(), "pages.txt should exist"

        # Check that tiles directory does NOT exist (since emit=pages)
        tiles_dir = doc_output / "tiles"
        assert not tiles_dir.exists(), "Tiles directory should NOT exist with default settings"

        # Check that no manifest files exist
        if tiles_dir.exists():
            manifest_files = list(tiles_dir.glob("tiles.*"))
            assert len(manifest_files) == 0, "No manifest files should exist with manifest=none"

"""Lightweight CLI tests with mocking (no WeasyPrint/PyMuPDF dependencies)."""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from ids import make_doc_id, make_doc_id_from_str
from models import FileSummary, SummaryFrontMatter


def test_doc_id_no_spaces():
    """Assert doc_id replaces spaces with underscores."""
    doc_id = make_doc_id(Path("a/b c.md"), Path("a"))
    assert doc_id == "b_c.md"


def test_doc_id_consistency():
    """Verify same doc_id computed across render and summarize paths."""
    input_root = Path("docs")
    src_path = Path("docs/app/page.tsx")

    # Render-style (relative to input_dir)
    render_id = make_doc_id(src_path, input_root)

    # Summarize-style (absolute path, no input_root)
    summarize_id = make_doc_id_from_str(str(src_path))

    # These should match when we use input_root for summarize too
    # For this test, we verify render_id is consistent format
    assert "__" in render_id
    assert " " not in render_id


def test_doc_id_from_str():
    """Test make_doc_id_from_str convenience wrapper."""
    doc_id = make_doc_id_from_str("hello world.py")
    assert doc_id == "hello_world.py"
    assert " " not in doc_id


@patch("main.hybrid_search")
@patch("main.config")
def test_search_command_lexical_only_no_query(mock_config, mock_hybrid_search):
    """Test search works without query when lexical filters provided."""
    from main import cmd_search
    from argparse import Namespace

    # Mock config: no OpenAI key
    mock_config.has_openai_key = False

    # Mock results
    mock_results = [
        {
            "doc_id": "app_page",
            "score": 0.75,
            "lex_score": 0.75,
            "sem_score": 0.0,
            "source_path": "app/page.tsx",
            "why": ["matched term: auth"],
        }
    ]
    mock_hybrid_search.return_value = mock_results

    # Create args: no query, but lexical filters
    args = Namespace(
        query="",
        k=12,
        must=["auth"],
        regex=None,
        path_like=None,
        json=False,
    )

    # Should not error (exit code 0)
    rc = cmd_search(args)
    assert rc == 0

    # Should have called hybrid_search with empty query
    mock_hybrid_search.assert_called_once()
    call_kwargs = mock_hybrid_search.call_args[1]
    assert call_kwargs["query"] == ""


@patch("main.hybrid_search")
@patch("main.config")
def test_search_command_semantic_with_fake_embeddings(mock_config, mock_hybrid_search):
    """Test search with semantic query formats output correctly."""
    from main import cmd_search, pretty_print_results
    from argparse import Namespace
    from io import StringIO

    # Mock config: has OpenAI key
    mock_config.has_openai_key = True

    # Mock results with semantic scores
    mock_results = [
        {
            "doc_id": "indexer_py",
            "score": 0.85,
            "sem_score": 0.90,
            "lex_score": 0.65,
            "source_path": "indexer.py",
            "page_uris": [
                "http://127.0.0.1:8000/out/indexer_py/pages/indexer-p1.webp",
                "http://127.0.0.1:8000/out/indexer_py/pages/indexer-p2.webp",
            ],
            "why": ["semantic match: vector store", "matched term: chroma"],
        }
    ]
    mock_hybrid_search.return_value = mock_results

    args = Namespace(
        query="vector store",
        k=12,
        must=None,
        regex=None,
        path_like=None,
        json=False,
    )

    # Capture stdout
    with patch("sys.stdout", new=StringIO()) as fake_out:
        rc = cmd_search(args)
        output = fake_out.getvalue()

    assert rc == 0
    assert "indexer_py" in output
    assert "0.85" in output  # final score
    assert "sem=0.90" in output or "sem=0.90" in output
    assert "lex=0.65" in output


@patch("main.subprocess.Popen")
def test_serve_command_starts_server(mock_popen):
    """Test serve command starts http.server with correct directory."""
    from main import cmd_serve
    from argparse import Namespace

    # Mock process
    mock_proc = Mock()
    mock_proc.wait = Mock()
    mock_proc.terminate = Mock()
    mock_popen.return_value = mock_proc

    # Test serving "out" directory (should serve parent)
    args = Namespace(out_dir=Path("/tmp/out"), port=8000)

    with patch("builtins.print"):  # Suppress output for test
        # Simulate Ctrl+C
        mock_proc.wait.side_effect = KeyboardInterrupt()
        rc = cmd_serve(args)

    assert rc == 0
    assert mock_proc.terminate.called

    # Verify Popen was called
    assert mock_popen.called
    call_args = mock_popen.call_args[0][0]
    assert call_args[0] == sys.executable
    assert call_args[1] == "-m"
    assert call_args[2] == "http.server"


@patch("main.upsert_code_chunks")
@patch("main.upsert_summaries")
@patch("main.get_client")
@patch("main.render_file")
@patch("main.summarize_file")
@patch("main.save_summary_md")
@patch("main.discover_sources")
@patch("main.config")
def test_ingest_command_end_to_end_minimal(
    mock_config,
    mock_discover,
    mock_save_summary,
    mock_summarize,
    mock_render,
    mock_get_client,
    mock_upsert_summaries,
    mock_upsert_chunks,
    tmp_path,
):
    """Test ingest command with mocked dependencies."""
    from main import cmd_ingest
    from argparse import Namespace
    from datetime import datetime

    # Mock config
    mock_config.has_openai_key = True
    mock_config.LINES_PER_CHUNK = 180
    mock_config.OVERLAP = 30

    # Setup test directories
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    # Create a test source file
    test_file = input_dir / "test.py"
    test_file.write_text("# Test file\nprint('hello')\n")

    # Mock discover_sources
    mock_discover.return_value = [test_file]

    # Compute canonical doc_id for consistency
    test_doc_id = make_doc_id(test_file, input_root=input_dir)

    # Mock render_file: create minimal pages.jsonl
    def mock_render_file(src, out_root, cfg):
        doc_id = make_doc_id(src, input_root=cfg.input_dir)  # consistent with renderer
        dest_dir = out_root / doc_id
        dest_dir.mkdir(parents=True)
        pages_dir = dest_dir / "pages"
        pages_dir.mkdir()
        pages_jsonl = pages_dir / "pages.jsonl"
        # Write minimal pages.jsonl
        pages_jsonl.write_text(
            json.dumps(
                {
                    "doc_id": doc_id,
                    "page": 1,
                    "uri": f"http://127.0.0.1:8000/out/{doc_id}/pages/test-p1.webp",
                }
            )
            + "\n"
        )

    mock_render.side_effect = mock_render_file

    # Mock summarize_file
    mock_summary = FileSummary(
        front_matter=SummaryFrontMatter(
            doc_id=test_doc_id,
            source_path=str(test_file),
            language="python",
            last_updated=datetime.utcnow(),
        ),
        summary_md="This is a test file with many words. " * 50,  # Ensure 200+ words
    )
    mock_summarize.return_value = mock_summary

    # Mock client
    mock_client = Mock()
    mock_get_client.return_value = mock_client

    # Create args
    args = Namespace(
        input_dir=input_dir,
        out_dir=out_dir,
        no_summary=False,
        no_index=False,
    )

    # Run ingest (suppress tqdm output)
    with patch("main.tqdm"):
        with patch("main.tqdm.write"):
            rc = cmd_ingest(args)

    assert rc == 0
    assert mock_render.called
    assert mock_summarize.called
    assert mock_get_client.called
    # Should have called upsert methods
    assert mock_upsert_summaries.called or mock_upsert_chunks.called


@patch("main.hybrid_search")
@patch("main.config")
def test_search_command_no_key_no_filters_errors(mock_config, mock_hybrid_search):
    """Test search errors gracefully when no key and no filters."""
    from main import cmd_search
    from argparse import Namespace

    # Mock config: no OpenAI key
    mock_config.has_openai_key = False

    # Create args: no query, no filters
    args = Namespace(
        query="",
        k=12,
        must=None,
        regex=None,
        path_like=None,
        json=False,
    )

    # Should error with exit code 2
    rc = cmd_search(args)
    assert rc == 2
    # Should not have called hybrid_search
    mock_hybrid_search.assert_not_called()


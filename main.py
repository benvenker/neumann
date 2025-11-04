#!/usr/bin/env python3
"""
Neumann CLI: Orchestrate render → summarize → chunk → index pipeline.

Commands:
  ingest: Render, summarize, chunk, and index documents
  search: Run hybrid search (semantic + lexical)
  serve:  Start HTTP server to serve output directory
"""

import argparse
import contextlib
import json
import subprocess
import sys
import time
from datetime import timezone
from pathlib import Path
from typing import Any

from tqdm import tqdm

from chunker import chunk_file_by_lines, load_page_uris
from config import config
from embeddings import embed_texts
from ids import make_doc_id
from indexer import get_client, get_collections, hybrid_search, upsert_code_chunks, upsert_summaries
from models import FileSummary
from render_to_webp import RenderConfig, discover_sources, render_file
from summarize import detect_language_from_extension, save_summary_md, summarize_file

# Constants for output formatting
MAX_WHY_LINES = 3
MAX_PAGE_URIS = 3


def compute_doc_id(src: Path, input_root: Path) -> str:
    """Compute doc_id using canonical ids.make_doc_id.

    Args:
        src: Source file path
        input_root: Root directory for input files

    Returns:
        doc_id string with spaces replaced by underscores
    """
    return make_doc_id(src, input_root)


def build_summary_upsert_item(fs: FileSummary, doc_id: str, page_uris: list[str]) -> dict[str, Any]:
    """Build a summary upsert item for ChromaDB.

    Args:
        fs: FileSummary object with front_matter and summary_md
        doc_id: Document ID (must match render output)
        page_uris: List of page image URIs from pages.jsonl

    Returns:
        Dict with id, document, and metadata keys
    """
    meta = fs.front_matter.model_dump()
    # Override doc_id to ensure consistency (front_matter uses different computation)
    meta["doc_id"] = doc_id
    meta["page_uris"] = page_uris
    # Canonicalize language -> lang
    if "lang" not in meta and "language" in meta:
        meta["lang"] = meta.pop("language")
    elif "lang" in meta and "language" in meta:
        meta.pop("language", None)
    # Ensure last_updated is ISO string with proper UTC timezone
    if isinstance(meta.get("last_updated"), str):
        pass  # Already string
    else:
        from datetime import datetime

        if isinstance(fs.front_matter.last_updated, datetime):
            dt = fs.front_matter.last_updated
        else:
            dt = datetime.utcnow().replace(tzinfo=timezone.utc)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        meta["last_updated"] = dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    return {
        "id": doc_id,
        "document": fs.summary_md,
        "metadata": meta,
    }


def build_chunk_upsert_items(raw_text: str, src_path: Path, doc_id: str, pages_jsonl: Path) -> list[dict[str, Any]]:
    """Build code chunk upsert items from raw text.

    Args:
        raw_text: Raw file contents
        src_path: Source file path
        doc_id: Document ID
        pages_jsonl: Path to pages.jsonl file

    Returns:
        List of dicts with id, document, and metadata keys
    """
    chunks = chunk_file_by_lines(
        text=raw_text,
        pages_jsonl_path=pages_jsonl,
        per_chunk=config.LINES_PER_CHUNK,
        overlap=config.OVERLAP,
    )
    lang = detect_language_from_extension(str(src_path))

    items: list[dict[str, Any]] = []
    for ch in chunks:
        cid = f"{doc_id}#L{ch['line_start']}-{ch['line_end']}"
        meta = {
            "doc_id": doc_id,
            "source_path": str(src_path),
            "lang": lang,
            "line_start": ch["line_start"],
            "line_end": ch["line_end"],
            "page_uris": ch["page_uris"],
        }
        items.append({"id": cid, "document": ch["text"], "metadata": meta})

    return items


def pretty_print_results(results: list[dict[str, Any]]) -> None:
    """Pretty-print search results to stdout.

    Args:
        results: List of result dicts from hybrid_search
    """
    for i, r in enumerate(results, start=1):
        score = r.get("score", 0.0)
        sem_score = r.get("sem_score", 0.0)
        lex_score = r.get("lex_score", 0.0)
        doc_id = r.get("doc_id", "")
        print(f"{i:2d}. score={score:.3f} (sem={sem_score:.2f} lex={lex_score:.2f}) {doc_id}")

        sp = r.get("source_path")
        if sp:
            print(f"    {sp}")

        uris = r.get("page_uris") or []
        if isinstance(uris, str):
            s = uris.strip()
            uris = (
                [u.strip() for u in s.split(",")] if "," in s else [s]
            ) if s else []
        if uris:
            shown = uris[:MAX_PAGE_URIS]
            more = len(uris) - len(shown)
            uri_str = ", ".join(shown)
            if more > 0:
                uri_str += f" (+{more} more)"
            print(f"    pages: {uri_str}")

        why = r.get("why") or []
        for w in why[:MAX_WHY_LINES]:
            print(f"    - {w}")

        print()


def cmd_ingest(args: argparse.Namespace) -> int:
    """Ingest command: render → summarize → chunk → index.

    Args:
        args: Parsed arguments with input_dir, out_dir, no_summary, no_index

    Returns:
        Exit code (0 on success, non-zero on failure)
    """
    input_dir: Path = args.input_dir.resolve()
    out_dir: Path = args.out_dir.resolve()
    asset_root_input = getattr(args, "asset_root", None)
    asset_root: str = asset_root_input or out_dir.name

    if not input_dir.exists():
        print(f"Error: Input directory does not exist: {input_dir}", file=sys.stderr)
        return 1

    if not input_dir.is_dir():
        print(f"Error: Input path is not a directory: {input_dir}", file=sys.stderr)
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)

    # Warn only if user explicitly set mismatched asset_root
    if asset_root_input and asset_root_input != out_dir.name:
        print(
            f"Warning: --asset-root '{asset_root_input}' does not match output directory name '{out_dir.name}'. "
            f"URIs in pages.jsonl will point to '/{asset_root_input}/...'. Ensure your server serves that path.",
            file=sys.stderr,
        )

    # Discover sources
    sources = discover_sources(input_dir)
    if not sources:
        print("No supported files found.", file=sys.stderr)
        return 1

    # Build render config with computed asset_root
    render_cfg = RenderConfig(input_dir=input_dir, asset_root=asset_root)

    # Initialize client if indexing
    client = None
    db_path_used = None
    if not args.no_index:
        # Use --db-path if provided, otherwise use config default
        db_path_arg = getattr(args, "db_path", None)
        db_path_used = str(Path(db_path_arg).resolve()) if db_path_arg else config.CHROMA_PATH
        print(f"Using ChromaDB at: {db_path_used}")
        client = get_client(path=db_path_used if db_path_arg else None)

    # Statistics
    rendered = 0
    summarized = 0
    chunked = 0
    indexed_summaries = 0
    indexed_chunks = 0
    errors = 0

    total_sources = len(sources)

    def _rel_path(path: Path, root: Path) -> str:
        try:
            return str(path.relative_to(root))
        except ValueError:
            return str(path)

    # Process each file with progress bar
    with tqdm(total=total_sources, desc="Ingesting") as pbar:
        for idx, src in enumerate(sources, start=1):
            file_start = time.perf_counter()
            rel_src = _rel_path(src, input_dir)
            tqdm.write(f"\n[{idx}/{total_sources}] {rel_src}")
            try:
                doc_id = compute_doc_id(src, input_dir)

                # 1. Render
                stage_start = time.perf_counter()
                render_file(src, out_dir, render_cfg)
                rendered += 1
                render_dur = time.perf_counter() - stage_start
                tqdm.write(f"  render: {render_dur:.2f}s -> {doc_id}/pages")

                # 2. Load raw text and page URIs
                raw_text = src.read_text(encoding="utf-8", errors="ignore")
                pages_jsonl = out_dir / doc_id / "pages" / "pages.jsonl"
                page_uris = load_page_uris(pages_jsonl)

                # 3. Summarize (if enabled and OpenAI key available)
                summary_item = None
                if not args.no_summary and config.has_openai_key:
                    stage_start = time.perf_counter()
                    try:
                        fs = summarize_file(str(src), raw_text)
                        # Override doc_id to ensure consistency with renderer
                        fs.front_matter.doc_id = doc_id
                        summary_path = out_dir / doc_id / "summary.summary.md"
                        save_summary_md(summary_path, fs)
                        summary_item = build_summary_upsert_item(fs, doc_id, page_uris)
                        summarized += 1
                        words = len(fs.summary_md.split())
                        summary_dur = time.perf_counter() - stage_start
                        tqdm.write(
                            f"  summary: {words} words in {summary_dur:.2f}s -> {summary_path}"
                        )
                    except Exception as e:
                        tqdm.write(f"[warn] Failed to summarize {src}: {e}")
                elif args.no_summary:
                    tqdm.write("  summary: skipped (--no-summary)")
                elif not config.has_openai_key:
                    tqdm.write("  summary: skipped (OPENAI_API_KEY not configured)")

                # 4. Chunk
                stage_start = time.perf_counter()
                chunk_items = build_chunk_upsert_items(raw_text, src, doc_id, pages_jsonl)
                chunked += len(chunk_items)
                chunk_dur = time.perf_counter() - stage_start
                tqdm.write(f"  chunk: {len(chunk_items)} chunks in {chunk_dur:.2f}s")

                # 5. Index (if enabled)
                if client and not args.no_index:
                    stage_start = time.perf_counter()
                    try:
                        if summary_item and config.has_openai_key:
                            upsert_summaries([summary_item], client=client, embedding_function=embed_texts)
                            indexed_summaries += 1

                        if chunk_items:
                            upsert_code_chunks(chunk_items, client=client)
                            indexed_chunks += len(chunk_items)
                        index_dur = time.perf_counter() - stage_start
                        summary_desc = "summary + " if summary_item and config.has_openai_key else ""
                        tqdm.write(
                            f"  index: {summary_desc}{len(chunk_items)} chunks in {index_dur:.2f}s"
                        )
                    except Exception as e:
                        tqdm.write(f"[warn] Failed to index {src}: {e}")
                elif args.no_index:
                    tqdm.write("  index: skipped (--no-index)")

            except Exception as e:
                tqdm.write(f"[error] {src}: {e}")
                errors += 1
            finally:
                pbar.update(1)
                total_dur = time.perf_counter() - file_start
                tqdm.write(f"  total: {total_dur:.2f}s")

    # Print summary
    print("\nIngest complete:")
    print(f"  Rendered: {rendered}")
    print(f"  Summarized: {summarized}")
    print(f"  Chunks: {chunked}")
    if not args.no_index:
        print(f"  Indexed summaries: {indexed_summaries}")
        print(f"  Indexed chunks: {indexed_chunks}")

        # Verify collection counts in ChromaDB
        if client:
            try:
                summaries_coll, code_coll = get_collections(client)
                summary_count = summaries_coll.count()
                code_count = code_coll.count()
                print("\nChromaDB collection counts:")
                print(f"  search_summaries: {summary_count} documents")
                print(f"  search_code: {code_count} chunks")
            except Exception as e:
                print(f"  Warning: Could not verify collection counts: {e}", file=sys.stderr)
    if errors > 0:
        print(f"  Errors: {errors}")

    return 0


def cmd_search(args: argparse.Namespace) -> int:
    """Search command: Run hybrid search and format results.

    Args:
        args: Parsed arguments with query, k, must, regex, path_like, json, db_path

    Returns:
        Exit code (0 on success, non-zero on failure)
    """
    query = (args.query or "").strip()
    run_semantic = config.has_openai_key and bool(query)

    # Use --db-path if provided, otherwise use config default
    db_path_arg = getattr(args, "db_path", None)
    db_path_used = str(Path(db_path_arg).resolve()) if db_path_arg else config.CHROMA_PATH
    print(f"Using ChromaDB at: {db_path_used}")

    # Create client with explicit path
    client = get_client(path=db_path_used if db_path_arg else None)

    try:
        if run_semantic:
            # Full hybrid search with semantic + lexical
            results = hybrid_search(
                query=query,
                k=args.k,
                must_terms=args.must or None,
                regexes=args.regex or None,
                path_like=args.path_like,
                client=client,
                embedding_function=embed_texts,
            )
        else:
            # No OpenAI key - check if we can do lexical-only
            if not (args.must or args.regex or args.path_like):
                print(
                    "Semantic search requires OPENAI_API_KEY. "
                    "Provide lexical filters (--must/--regex/--path-like) or set the key.",
                    file=sys.stderr,
                )
                return 2

            # Lexical-only mode (empty query disables semantic channel)
            results = hybrid_search(
                query="",
                k=args.k,
                must_terms=args.must or None,
                regexes=args.regex or None,
                path_like=args.path_like,
                client=client,
            )
    except Exception as e:
        print(f"Search failed: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        if not results:
            print("No results.")
        else:
            pretty_print_results(results)

    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    """Serve command: Start HTTP server to serve output directory.

    Args:
        args: Parsed arguments with out_dir, port, and asset_root

    Returns:
        Exit code (0 on success, non-zero on failure)
    """
    root = args.out_dir.resolve()
    asset_root = getattr(args, "asset_root", None) or "out"
    serve_root = root

    # Adjust directory based on asset_root to match URI scheme
    if root.name == asset_root:
        serve_root = root.parent
        print(
            f"Detected '{asset_root}' directory. Serving parent '{serve_root}' "
            f"so URIs like {config.ASSET_BASE_URL}/{asset_root}/... resolve."
        )
    elif (root / asset_root).exists():
        serve_root = root
    else:
        print(
            f"Warning: URIs in manifests point to '/{asset_root}/...' "
            f"but '{asset_root}' directory not found under {root}",
            file=sys.stderr,
        )

    print(f"Serving {serve_root} at http://127.0.0.1:{args.port} (Ctrl+C to stop)")
    print(f"Configured ASSET_BASE_URL: {config.ASSET_BASE_URL}")

    try:
        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "http.server",
                str(args.port),
                "--directory",
                str(serve_root),
            ]
        )
        try:
            proc.wait()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            proc.terminate()
            with contextlib.suppress(KeyboardInterrupt):
                proc.wait()
    except OSError as e:
        print(f"Failed to start server: {e}", file=sys.stderr)
        return 1

    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser with subcommands.

    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog="neumann",
        description="Neumann CLI: ingest, search, serve",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ingest subcommand
    ingest_parser = subparsers.add_parser("ingest", help="Render → summarize → chunk → index")
    ingest_parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing source files",
    )
    ingest_parser.add_argument(
        "--out-dir",
        type=Path,
        required=True,
        help="Output root directory (contains 'out')",
    )
    ingest_parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Skip summarization/upsert summaries",
    )
    ingest_parser.add_argument(
        "--no-index",
        action="store_true",
        help="Skip indexing into Chroma",
    )
    ingest_parser.add_argument(
        "--asset-root",
        type=str,
        default=None,
        help="Root path segment embedded in pages.jsonl URIs (defaults to out_dir.name).",
    )
    ingest_parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help="ChromaDB storage path (overrides CHROMA_PATH from config). Will be resolved to absolute.",
    )
    ingest_parser.epilog = (
        "Examples:\n"
        "  neumann ingest --input-dir ./docs --out-dir ./out\n"
        "  neumann ingest --input-dir ./docs --out-dir ./out --no-summary\n"
        "  neumann ingest --input-dir ./docs --out-dir ./out --db-path /abs/path/to/chroma_data\n"
    )

    # search subcommand
    search_parser = subparsers.add_parser("search", help="Run hybrid search")
    search_parser.add_argument(
        "query",
        type=str,
        nargs="?",
        default="",
        help="Natural language query (optional; use lexical filters for lexical-only search)",
    )
    search_parser.add_argument("--k", type=int, default=12, help="Number of results to return (default: 12)")
    search_parser.add_argument(
        "--must",
        action="append",
        help="Lexical term that must match (repeatable)",
    )
    search_parser.add_argument(
        "--regex",
        action="append",
        help="Regex pattern (repeatable)",
    )
    search_parser.add_argument(
        "--path-like",
        type=str,
        default=None,
        help="Substring to match in source path",
    )
    search_parser.add_argument("--json", action="store_true", help="Output raw JSON")
    search_parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help="ChromaDB storage path (overrides CHROMA_PATH from config). Will be resolved to absolute.",
    )
    search_parser.epilog = (
        "Examples:\n"
        "  neumann search 'vector store' --k 5\n"
        "  neumann search '' --must chroma --path-like indexer.py\n"
        "  neumann search 'embeddings' --db-path /abs/path/to/chroma_data\n"
    )

    # serve subcommand
    serve_parser = subparsers.add_parser("serve", help="Start http.server to serve output")
    serve_parser.add_argument(
        "out_dir",
        type=Path,
        help="Directory to serve. If it is 'out', parent will be served to match '/out/...' URIs.",
    )
    serve_parser.add_argument(
        "--asset-root",
        type=str,
        default=None,
        help="Root path segment used in asset URIs (e.g., 'out', or custom). Determines which directory level to serve so '/{asset_root}/...' resolves.",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to listen on (default: 8000)",
    )
    serve_parser.epilog = (
        "Examples:\n"
        "  neumann serve ./  # serves current dir; pages under ./out at http://127.0.0.1:8000/out/...\n"
        "  neumann serve ./out --port 8000  # will serve parent to keep /out/... URIs working\n"
    )

    return parser


def main() -> None:
    """Main entry point for CLI."""
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "ingest":
        rc = cmd_ingest(args)
    elif args.command == "search":
        rc = cmd_search(args)
    elif args.command == "serve":
        rc = cmd_serve(args)
    else:
        parser.print_help()
        rc = 2

    sys.exit(rc)


if __name__ == "__main__":
    main()

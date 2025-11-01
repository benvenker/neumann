# Neumann

A Python CLI tool that renders Markdown and code files to PDF, then converts them to WebP page images. Pages-first by default, with optional tile generation for hybrid search applications.

## Features

- **Multi-format support**: Markdown (.md, .markdown, .mdx) and code files (.py, .js, .ts, .go, .rs, .java, .c, .cpp, .sh, .json, .yml, .html, .css, etc.)
- **Syntax highlighting**: Powered by Pygments with customizable color schemes
- **High-quality rendering**: WeasyPrint for PDF generation, configurable DPI and WebP quality
- **Pages-first philosophy**: Generates full-page WebP images by default (tiles are optional)
- **Optional tile generation**: Split pages into overlapping tiles for efficient image search
- **Content hashing**: SHA-256 checksums for each tile (optional)
- **Flexible manifests**: JSONL, JSON, or TSV formats for tile metadata (optional)
- **Compact line numbers**: Inline line numbers for code files by default (table-style also available)

## System Dependencies

WeasyPrint requires Cairo, Pango, and GDK-PixBuf:

### macOS
```bash
brew install cairo pango gdk-pixbuf libffi
```

### Ubuntu/Debian
```bash
sudo apt-get install libcairo2 libpango-1.0-0 libgdk-pixbuf2.0-0 libffi-dev
```

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for fast, modern Python dependency management:

```bash
# Create virtual environment
uv venv

# Install with development dependencies
uv pip install -e ".[dev]"

# Or just runtime dependencies
uv pip install -e .
```

### With direnv (recommended)

If you have [direnv](https://direnv.net/) installed, the virtual environment will activate automatically:

```bash
# Allow direnv for this directory
direnv allow
```

## Usage

### CLI Overview

Neumann provides a unified CLI with three main commands:

- **`neumann ingest`**: Full pipeline (render → summarize → chunk → index)
- **`neumann search`**: Hybrid search (semantic + lexical)
- **`neumann serve`**: HTTP server for output directory

For renderer-only usage (legacy), use **`neumann-render`** instead of `neumann`.

### Ingest: Full Pipeline

The `ingest` command processes files through the entire pipeline:

```bash
# Basic ingest (requires OPENAI_API_KEY for summaries)
neumann ingest --input-dir ./docs --out-dir ./out

# Skip summarization (no OpenAI key needed)
neumann ingest --input-dir ./docs --out-dir ./out --no-summary

# Skip indexing (useful for testing rendering)
neumann ingest --input-dir ./docs --out-dir ./out --no-index

# Custom asset root (match output directory name)
neumann ingest --input-dir ./docs --out-dir ./output --asset-root output
```

By default, `asset_root` is derived from `out_dir.name`, so URIs in `pages.jsonl` align with your chosen output directory.

This creates:
- WebP page images in `<out_dir>/<doc_id>/pages/`
- Summary files in `<out_dir>/<doc_id>/summary.summary.md`
- Indexed summaries and code chunks in ChromaDB

### Search: Hybrid Search

Search combines semantic and lexical matching:

```bash
# Semantic search (requires OPENAI_API_KEY)
neumann search "vector store" --k 5

# Lexical-only search (no OpenAI key needed)
neumann search --must chroma --path-like indexer.py

# Hybrid search (semantic + lexical)
neumann search "authentication" --must redirect_uri --path-like auth.ts

# JSON output for programmatic use
neumann search "query" --json
```

### Serve: HTTP Server

Start a local HTTP server to serve rendered output:

```bash
# Serve output directory (auto-detects 'out' directory)
neumann serve ./out

# Custom port
neumann serve ./out --port 8080

# Custom asset root
neumann serve ./out --asset-root out

# Serve parent directory (for custom output names)
neumann serve ./

# Serve with custom asset root
neumann serve ./output --asset-root output
```

The `serve` command automatically detects directory structure to match URI schemes. Use `--asset-root` to explicitly set the root path segment used in asset URIs, which determines which directory level to serve so `/asset_root/...` resolves correctly.

### Renderer-Only: Legacy Command

For renderer-only workflows (no summarization/indexing), use `neumann-render`:

```bash
# Basic rendering
neumann-render --input-dir ./docs --out-dir ./out

# With tiles
neumann-render --input-dir ./docs --out-dir ./out --emit both --manifest jsonl

# Custom asset root (for URI customization)
neumann-render --input-dir ./docs --out-dir ./output --asset-root output
```

### URI Configuration and Asset Serving

URIs in `pages.jsonl` are constructed as:
```
{ASSET_BASE_URL}/{asset_root}/{doc_id}/pages/{filename}
```

By default:
- `ASSET_BASE_URL`: `http://127.0.0.1:8000` (set via `.env` or environment)
- `asset_root`: Defaults to `out_dir.name` in `ingest` command, or `out` in `neumann-render` (configurable via `--asset-root`)

URIs are now constructed using `asset_root`, which defaults to `out_dir.name` in the `ingest` command. This ensures URIs align with your chosen output directory structure.

**Important**: For URIs to resolve correctly:
1. Use an output directory and let `asset_root` default to its name, OR
2. Explicitly set `--asset-root` to match your serving setup, OR
3. Use `neumann serve` on the parent directory (auto-detects `out` directory)

Example: If `out_dir` is `./output`, URIs will default to `/output/...` (matching the directory name). To override:
- Use `--asset-root out` in the `ingest` command, OR
- Serve parent directory: `neumann serve ./` (serves parent, so `/out/...` or `/output/...` resolves from root)

### Configuration

Key environment variables (set in `.env` or export):
- `OPENAI_API_KEY`: Required for summarization and semantic search
- `ASSET_BASE_URL`: Base URL for asset URIs (default: `http://127.0.0.1:8000`)
- `CHROMA_PATH`: Path to ChromaDB storage (default: `./chroma_data`)

### Renderer Options (neumann-render)

- `--input-dir`: Directory containing Markdown and/or code files (required)
- `--out-dir`: Output directory for PDFs and WebP files (required)
- `--asset-root`: Root path segment for asset URIs (default: `out`)
- `--page-width-px`: Page width in pixels (default: 1200)
- `--body-font-size`: Base font size for body text (default: 15)
- `--code-font-size`: Font size for code blocks (default: 14)
- `--line-height`: Line height multiplier (default: 1.4)
- `--pygments-style`: Pygments color scheme (default: "friendly")
- `--extra-css-path`: Optional path to additional CSS file
- `--dpi`: Rasterization DPI for PDF to image conversion (default: 200)
- `--webp-quality`: WebP quality 0-100 (default: 90)
- `--webp-lossless`: Use lossless WebP encoding (larger files)
- `--tile-size`: Tile edge length in pixels (default: 1024)
- `--tile-overlap`: Fractional overlap between tiles 0.0-0.5 (default: 0.10)
- `--emit`: Output type: `pages`, `tiles`, or `both` (default: pages)
- `--manifest`: Manifest format: `jsonl`, `json`, `tsv`, or `none` (default: none)
- `--no-hash-tiles`: Disable SHA-256 hashing for tiles

## Output Structure

### Default (Pages Only)

```
out/
├── document__example.md/
│   ├── example.pdf
│   ├── pages/
│   │   ├── example-p001.webp
│   │   ├── example-p002.webp
│   │   ├── pages.txt
│   │   └── pages.jsonl
│   └── summary.summary.md  (if summarization enabled)
```

### With Tiles (--emit both or --emit tiles)

```
out/
├── document__example.md/
│   ├── example.pdf
│   ├── pages/
│   │   ├── example-p001.webp
│   │   ├── example-p002.webp
│   │   ├── pages.txt
│   │   └── pages.jsonl
│   ├── tiles/
│   │   ├── example-p001-x0-y0.webp
│   │   ├── example-p001-x0-y922.webp
│   │   ├── ...
│   │   └── tiles.jsonl  (only if --manifest is specified)
│   └── summary.summary.md
```

**Note**: Chunking expects `pages/pages.jsonl` to exist. If rendering with `--emit tiles` only (renderer-only workflow), `pages_dir` is removed and chunking will not find `pages.jsonl`. Ensure your ingest render stage emits pages (default behavior).

### Manifest Format (JSONL example)

```json
{
  "doc_id": "document__example.md",
  "page": 1,
  "tile_idx": 0,
  "tile_path": "/path/to/tile.webp",
  "page_path": "/path/to/page.webp",
  "bbox": {"x0": 0, "y0": 0, "x1": 1024, "y1": 1024},
  "tile_px": 1024,
  "overlap": 0.1,
  "source_pdf": "/path/to/document.pdf",
  "source_file": "/path/to/document.md",
  "sha256": "abc123..."
}
```

## Development

### Developer Tools

This project uses modern Python tooling for an efficient development workflow:

- **uv**: Fast Python package manager (replaces pip/poetry)
- **ruff**: Lightning-fast linter and formatter
- **mypy**: Static type checking
- **pytest**: Testing framework
- **ast-grep**: Structural code search and refactoring (AST-based pattern matching)
- **tmux**: Terminal multiplexer for background processes

### Code Quality

```bash
# Format code
ruff format .

# Lint
ruff check .

# Type checking
mypy render_to_webp.py
```

### Running Tests

```bash
pytest
```

### Background Processes with tmux

For long-running processes (dev servers, batch jobs), use tmux with descriptive session names:

```bash
# Create a named session
tmux new -s neumann-api

# List active sessions
tmux ls

# Attach to a session
tmux attach -t neumann-api

# Detach: Press Ctrl+b, then d
```

Sessions follow the naming pattern: `neumann-<purpose>` (e.g., `neumann-api`, `neumann-worker`)

## Doc ID Format

Document IDs (`doc_id`) are computed from file paths:
- Relative to input directory (or anchor-stripped for absolute paths)
- Spaces replaced with underscores
- Path separators replaced with double underscores

Example: `docs/app/auth page.tsx` → `app__auth_page.tsx`

This ensures consistency across render output, summaries, and search index.

## Performance Considerations

The current `ingest` pipeline reads entire files into memory for summarization and chunking. This approach is acceptable for most use cases but may increase memory usage for very large files.

**Current behavior**:
- Files are read completely into memory before processing
- Memory usage scales with file size
- Suitable for typical code and documentation files (< 1MB)

**Future improvements**:
- Streaming chunker to process files line-by-line without full memory load
- Parallel batch processing for large document collections

For production workloads with very large files (> 10MB), consider using `--no-summary` to reduce memory pressure, or splitting documents into smaller files.

## Roadmap

- [x] Hybrid search with text and image embeddings
- [x] ChromaDB integration for vector storage
- [ ] Image embeddings (CLIP/SigLIP)
- [ ] OCR support for image-based PDFs
- [ ] Batch processing with parallel workers
- [ ] Web UI for search and preview

## License

MIT

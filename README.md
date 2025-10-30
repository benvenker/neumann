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

### Basic Example

By default, renders pages only (no tiles, no manifest):

```bash
python render_to_webp.py \
  --input-dir ./docs \
  --out-dir ./output
```

This creates WebP page images suitable for preview and basic search. Tiles are optional and only generated when explicitly requested.

### Optional: Generate Tiles for Search

To generate overlapping tiles for image embedding and hybrid search:

```bash
python render_to_webp.py \
  --input-dir ./docs \
  --out-dir ./output \
  --emit both \
  --manifest jsonl
```

### Full Example with Options

```bash
python render_to_webp.py \
  --input-dir ./my_docs \
  --out-dir ./out \
  --page-width-px 1200 \
  --body-font-size 15 \
  --code-font-size 14 \
  --line-height 1.45 \
  --dpi 200 \
  --webp-quality 90 \
  --tile-size 1024 \
  --tile-overlap 0.10 \
  --emit both \
  --manifest jsonl
```

### Options

- `--input-dir`: Directory containing Markdown and/or code files (required)
- `--out-dir`: Output directory for PDFs and WebP files (required)
- `--page-width-px`: Page width in pixels (default: 1200)
- `--body-font-size`: Base font size for body text (default: 15)
- `--code-font-size`: Font size for code blocks (default: 14)
- `--line-height`: Line height multiplier (default: 1.45)
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
output/
├── document__example.md/
│   ├── example.pdf
│   └── pages/
│       ├── example-p001.webp
│       ├── example-p002.webp
│       └── pages.txt
```

### With Tiles (--emit both or --emit tiles)

```
output/
├── document__example.md/
│   ├── example.pdf
│   ├── pages/
│   │   ├── example-p001.webp
│   │   ├── example-p002.webp
│   │   └── pages.txt
│   └── tiles/
│       ├── example-p001-x0-y0.webp
│       ├── example-p001-x0-y922.webp
│       ├── ...
│       └── tiles.jsonl  (only if --manifest is specified)
```

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

## Roadmap

- [ ] Hybrid search with text and image embeddings
- [ ] ChromaDB integration for vector storage
- [ ] OCR support for image-based PDFs
- [ ] Batch processing with parallel workers
- [ ] Web UI for search and preview

## License

MIT

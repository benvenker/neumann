# Neumann

Photographic memory for AI agents.

Neumann turns your docs, code, and knowledge base into **page images + rich text chunks** that agents can actually see. It runs a full ingestion pipeline (render → summarize → chunk → embed → index) and exposes **hybrid search** over ChromaDB (semantic + lexical) so a text query can come back with:

- Relevant summaries and code snippets
- The **exact pages or tiles as images** where that content lives
- Metadata your UI or agent can use to drive follow‑up calls

You can think of it as an opinionated “memory card” maker for agents: point it at a repo or docs directory, and it builds a searchable visual corpus you can plug into CLIs, UIs, or agent runtimes.

## What Neumann Does

- **Renders source → pages → tiles**
  - Markdown, code, and more rendered to PDF and then WebP page images
  - Optional overlapping tiles for fine‑grained visual retrieval
- **Builds an agent‑friendly index**
  - YAML‑front‑matter summaries
  - Line‑based text chunks tied to pages
  - Embeddings stored in Chroma (`search_summaries`, `search_code`)
- **Supports hybrid search via ChromaDB**
  - Semantic search using OpenAI embeddings
  - Lexical/FTS search over code and text
  - Hybrid fusion (0.6 semantic / 0.4 lexical by default)
- **Returns images, not just text**
  - Search results carry page and tile URIs
  - Easy to render “filmstrips” or screenshots in your UI
- **Ships as both CLI and API**
  - `neumann` CLI for ingest/search/serve
  - FastAPI scaffold under `api/` for HTTP and agent integrations

Under the hood it’s still “just” a Python CLI, but the design goal is clear: **give agents photographic recall of the systems they work on.**

## Core Pipeline

At a high level:

```text
source files → render_to_webp.py → pages/*.webp (+ optional tiles/*.webp)
             → summarize.py (YAML+body)
             → chunker.py (line-based windows)
             → embeddings.py (OpenAI)
             → indexer.py (ChromaDB)
             → hybrid search (semantic + lexical)
```

Downstream consumers (CLI, API, agents) never have to know about PDF, WebP, or chunking details—they just ask Neumann to ingest, then query for what they need.

## Quickstart

### 1. System Dependencies

WeasyPrint requires Cairo, Pango, and GDK-PixBuf:

#### macOS
```bash
brew install cairo pango gdk-pixbuf libffi
```

#### Ubuntu/Debian
```bash
sudo apt-get install libcairo2 libpango-1.0-0 libgdk-pixbuf2.0-0 libffi-dev
```

### 2. Installation

This project uses [uv](https://github.com/astral-sh/uv) for fast, modern Python dependency management:

```bash
# Create virtual environment
uv venv

# Install with development dependencies
uv pip install -e ".[dev]"

# Or just runtime dependencies
uv pip install -e .
```

#### With direnv (recommended)

If you have [direnv](https://direnv.net/) installed, the virtual environment will activate automatically:

```bash
# Allow direnv for this directory
direnv allow
```

### 3. Ingest + Search in Two Commands

Assuming you have an `OPENAI_API_KEY` in `.env` or your environment:

```bash
# 1) Ingest a docs or code directory
neumann ingest --input-dir ./docs --out-dir ./out

# 2) Ask a question, combine semantic + lexical filters
neumann search "hybrid search" --must chroma --path-like indexer.py --k 5
```

This will:

- Render documents to page images under `./out/<doc_id>/pages/`
- Generate `.summary.md` files with YAML front matter
- Chunk text, create embeddings, and index into ChromaDB
- Return results that include:
  - summary text
  - chunk excerpts
  - `page_uris` you can render as images in your UI

For UIs or agents, you can also use the FastAPI service under `api/` (see **FastAPI Service** below).

## CLI Overview

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

### FastAPI Service (Preview)

A new FastAPI scaffold is available under the `api/` package. This provides a foundation for HTTP API endpoints that will expose search and document capabilities to UI clients.

**Starting the API server**:

```bash
# Run with uvicorn (development mode)
uvicorn backend.api.app:app --reload --port 8001

# Or use the factory function
uvicorn backend.api.app:create_app --factory --reload --port 8001
```

**Configuration**:

The API uses two additional environment variables:

- **`OUTPUT_DIR`** (default: `./out`): Filesystem path for rendered output (pages/tiles). This is where the API will look for document assets and manifests.
  
- **`API_CORS_ORIGINS`**: Allowed CORS origins for the API. Accepts comma-separated string or JSON array format:
  ```bash
  # Comma-separated
  export API_CORS_ORIGINS="http://localhost:3000,http://127.0.0.1:5173"
  
  # JSON array
  export API_CORS_ORIGINS='["http://localhost:3000","http://127.0.0.1:5173"]'
  ```
  
  If not set, CORS middleware is disabled (secure-by-default for local usage).

**Endpoints**:

Currently available:
- `/healthz` - Health check endpoint
- `/docs` - Interactive API documentation (OpenAPI/Swagger)
- `/openapi.json` - OpenAPI schema

**Search endpoints** (nm-3573.2):
- **POST `/api/v1/search/lexical`** - FTS and regex search over code chunks
- **POST `/api/v1/search/semantic`** - Vector similarity search over summaries (requires `OPENAI_API_KEY`)
- **POST `/api/v1/search/hybrid`** - Combined semantic + lexical with weighted fusion

**Examples**:

```bash
# Lexical search: Find "vector" in indexer.py
curl -s http://127.0.0.1:8001/api/v1/search/lexical \
  -H 'Content-Type: application/json' \
  -d '{"must_terms": ["vector"], "path_like": "indexer.py", "k": 5}'

# Semantic search: Natural language query (requires OPENAI_API_KEY)
curl -s http://127.0.0.1:8001/api/v1/search/semantic \
  -H 'Content-Type: application/json' \
  -d '{"query": "vector store retrieval", "k": 5}'

# Hybrid search: Combine semantic query with regex filter
curl -s http://127.0.0.1:8001/api/v1/search/hybrid \
  -H 'Content-Type: application/json' \
  -d '{"query": "authentication", "regexes": ["redirect_uri"], "k": 5}'
```

**Error codes**:
- **400 Bad Request**: Missing `OPENAI_API_KEY` for semantic/hybrid, invalid `k`, empty queries, no filters provided
- **502 Bad Gateway**: Upstream ChromaDB or embedding service errors

**Upcoming endpoints** (tracked in Beads):
- **nm-3573.3**: `/api/v1/docs` - Document pages and chunks endpoints  
- **nm-3573.4**: `/api/v1/config` - Configuration and service info

**Running alongside static assets**:

The API server and static asset server can run side-by-side in separate tmux sessions:

```bash
# Terminal 1: Start asset server
tmux new -s neumann-assets
neumann serve ./out --port 8000
# Detach: Ctrl+b, then d

# Terminal 2: Start API server
tmux new -s neumann-api
uvicorn backend.api.app:app --reload --port 8001
# Detach: Ctrl+b, then d

# List sessions
tmux ls

# Attach to a session
tmux attach -t neumann-api
```

This preview scaffold introduces the FastAPI foundation without changing existing CLI behavior. Full endpoint implementation is tracked via the nm-3573 epic in Beads.

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
- `OUTPUT_DIR`: Filesystem path for rendered output (default: `./out`)
- `API_CORS_ORIGINS`: Allowed CORS origins for FastAPI (comma-separated or JSON array)

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

## Metadata Normalization

Neumann stores list-like metadata fields in ChromaDB as comma-separated strings and rehydrates them to lists on read.

**Known list-like keys** (defined in `NORMALIZED_META_LIST_KEYS`):
- `product_tags`
- `key_topics`
- `api_symbols`
- `related_files`
- `suggested_queries`
- `page_uris`

**Caveat**: If your metadata values contain commas, they may split incorrectly on hydration. This is acceptable for the POC; a robust serialization method (e.g., JSON encoding) is planned for the future (see Beads issue).

**Example**:
```python
# Ingestion writes:
metadata = {"page_uris": ["uri1", "uri2"]}  # stored as "uri1,uri2"

# Search returns:
result["metadata"]["page_uris"]  # ["uri1", "uri2"] (rehydrated)
```

## Language Metadata

The canonical metadata key for language is **`lang`**.

- **Ingestion**: All new documents store only `lang` (not `language`)
- **Retrieval**: Search results expose `metadata.language` for backward compatibility, sourced from either `lang` or `language`
- **Migration**: Existing documents with `language` continue to work; no data migration required

This unification simplifies the codebase while maintaining API compatibility.

## CLI Output Formatting

The `neumann search` command pretty-prints results, including page URIs:

- Handles `page_uris` as either a list or comma-separated string
- Displays up to 3 URIs with a "+N more" indicator for additional URIs
- Gracefully handles empty or malformed URI data

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

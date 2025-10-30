# Neumann - Project Context

## Project Overview

Neumann is a document processing pipeline that converts text files (Markdown, code) into searchable image tiles. The ultimate goal is to build a hybrid search system that combines:
- **Text search**: Traditional keyword and semantic search on document content
- **Visual search**: Image embeddings for visual similarity search
- **Hybrid search**: Combined text + image retrieval using ChromaDB

## Current Status

**Phase 1: Document → Image Pipeline** ✓ (Current)
- Single-file CLI script (`render_to_webp.py`)
- Markdown/code → HTML → PDF (WeasyPrint) → WebP pages
- Emits `pages.jsonl` for every run (pages-first default)
- Tiling and tile manifests are optional and off by default

## Architecture

### Current Structure (Single Script)
```
neumann/
├── .beads/                  # Beads issue tracking (git-tracked)
├── render_to_webp.py       # Main CLI script
├── pyproject.toml           # Modern Python project config (PEP 621)
├── .python-version          # Python 3.10
├── .envrc                   # direnv auto-activation
├── README.md                # User documentation
└── CLAUDE.md                # This file (context for Claude)
```

Renderer (`render_to_webp.py`): Builds page images and writes `pages/pages.jsonl` with HTTP `uri` values derived from `ASSET_BASE_URL`. Tiles are generated only when `--emit tiles|both` is selected; tile manifests are written only when `--manifest` is not `none`.

Defaults: `emit=pages`, `manifest=none`, `linenos=inline`, `tile_mode=bands`, `tile_overlap=0.10`. `pages.jsonl` is always emitted. Tile output and manifests are opt-in.

### Future Structure (as project grows)
```
neumann/
├── src/neumann/
│   ├── __init__.py
│   ├── cli.py               # CLI entry point
│   ├── render/
│   │   ├── pdf.py           # PDF generation
│   │   ├── webp.py          # WebP conversion
│   │   └── tiles.py         # Tile generation
│   ├── search/
│   │   ├── embeddings.py    # Text & image embeddings
│   │   ├── chroma.py        # ChromaDB integration
│   │   └── hybrid.py        # Hybrid search logic
│   └── utils/
│       ├── hash.py          # Content hashing
│       └── manifest.py      # Manifest generation
├── tests/
│   ├── test_render.py
│   ├── test_search.py
│   └── fixtures/
└── docs/
    └── CLAUDE.md            # Detailed architecture docs
```

## Technology Stack

### Core Dependencies
- **WeasyPrint** (62.3): HTML → PDF rendering with Cairo backend
- **PyMuPDF** (1.24.8): PDF → image rasterization
- **Pillow** (10.4.0): Image manipulation and WebP encoding
- **Pygments** (2.18.0): Syntax highlighting for code files
- **Markdown** (3.6): Markdown parsing with extensions
- **pydantic-settings**: Configuration loading for `config.Config`

### Development Tools
- **uv**: Modern Python package manager (fast pip/poetry replacement)
- **direnv**: Auto-activate virtual environment on directory entry
- **ruff**: Fast Python linter and formatter (replaces black, isort, flake8)
- **mypy**: Static type checking
- **pytest**: Testing framework
- **ast-grep**: Structural code search and refactoring (AST-based pattern matching)
- **tmux**: Terminal multiplexer for background sessions and dev servers

### Future Dependencies
- **ChromaDB**: Vector database for embeddings
- **sentence-transformers**: Text embeddings (e.g., all-MiniLM-L6-v2)
- **CLIP** or **SigLIP**: Image embeddings
- **FastAPI**: Web API for search service
- **Pydantic**: Data validation for API models

## Design Decisions

### Why single script for now?
- Fast prototyping and iteration
- Easy to understand and modify
- Can be refactored into package structure later
- Follows "start simple, grow complex" principle

### Why WeasyPrint over alternatives?
- Native PDF generation (no browser automation needed)
- Excellent CSS support for styling
- Deterministic rendering (same input → same output)
- Open source with active maintenance

Alternatives considered:
- **Playwright/Chromium**: Heavy dependency, requires browser
- **ReportLab**: Low-level API, harder to style
- **wkhtmltopdf**: Unmaintained, Qt WebKit dependency

### Tiling modes and overlap
- Two modes: `bands` (default, full-width horizontal bands; height set by `--band-height`) and `grid` (square tiles; size set by `--tile-size`).
- `--tile-overlap` applies to both modes (default 10%).
- Tile hashing is enabled by default; disable with `--no-hash-tiles`.
- Rationale: overlapping tiles prevent content from being split across tile boundaries and improve recall.

### Manifests and locations
- Pages manifest: `pages/pages.jsonl` (always written). Each record includes page metadata and `uri` built as `{ASSET_BASE_URL}/out/{doc_id}/pages/{file}.webp`.
- Tile manifests: written only when tiling is enabled and `--manifest` ≠ `none`. Formats supported: JSONL, JSON, TSV.

### Configuration
Configuration is provided by `config.Config` (pydantic-settings), which reads environment variables and `.env`. Key settings include `ASSET_BASE_URL`, `CHROMA_PATH`, and chunking defaults (e.g., `tile_overlap`). The renderer uses `ASSET_BASE_URL` to build HTTP `uri` fields in `pages/pages.jsonl`.

### Summarization artifacts
`summarize.py` and `models.py` produce `.summary.md` files consisting of YAML front matter plus a 200–400 word body (enforced by tests). The default generator is a stub used for tests; model providers can be integrated later. An example artifact lives in `output_summaries/`.

### Indexing and search (separate step)
`indexer.py` initializes Chroma and two collections: `search_summaries` and `search_code`, and exposes upsert helpers. It is not wired into the renderer CLI; indexing is a separate step/module at present.

### Why JSONL for manifests?
For tile manifests (when enabled):
- Streaming-friendly (process one record at a time)
- Easy to append new tiles
- Simple to import into databases
- Still human-readable (unlike binary formats)

### Tests codify defaults
Tests enforce pages-first defaults, `pages.jsonl` emission with HTTP `uri`s, syntax highlighting behavior, summary constraints, and Chroma collection setup.

## Project Management

### Issue Tracking with Beads

**IMPORTANT**: This project uses **Beads (bd)** for issue tracking and project management, NOT GitHub Issues or other systems.

The following workflows are operational guidance and do not affect runtime behavior.

#### Why Beads?
- Local-first issue tracking (lives in `.beads/` directory)
- Git-based synchronization
- Dependency tracking between issues
- AI-friendly CLI and MCP integration
- Lightweight and fast

#### Beads MCP Tools

Use these MCP tools for issue management (available via `mcp__plugin_beads_beads__*`):
- `set_context`: Set workspace root (call this first!)
- `list`: List issues with filters (status, priority, type, assignee)
- `show`: Show detailed issue information
- `create`: Create new issues (bug, feature, task, epic, chore)
- `update`: Update issue status, priority, description, etc.
- `close`: Mark issues as completed
- `ready`: Find tasks with no blockers (ready to work on)
- `blocked`: Show blocked issues and their dependencies
- `dep`: Add dependencies between issues
- `stats`: Get project statistics

#### Workflow

1. **Starting new work**:
   ```bash
   # Initialize beads (first time only)
   /beads:init nm

   # Find ready tasks
   /beads:ready

   # Create new issue
   /beads:create "Add ChromaDB integration" feature 2
   ```

2. **Working on issues**:
   ```bash
   # Claim and start work
   /beads:update nm-123 --status in_progress --assignee ProductThor

   # Show details
   /beads:show nm-123
   ```

3. **Completing work**:
   ```bash
   # Close issue
   /beads:close nm-123 "Implemented and tested"

   # Check stats
   /beads:stats
   ```

4. **Managing dependencies**:
   ```bash
   # nm-124 blocks nm-125
   /beads:dep blocks nm-124 nm-125

   # Find blocked issues
   /beads:blocked
   ```

#### Integration with AI Workflow

When working on this project:
- **Always check `/beads:ready`** before starting new work
- **Create issues** for bugs, features, or tasks you discover
- **Update issue status** as you progress (`in_progress` → `closed`)
- **Link related issues** with dependencies when one blocks another
- **Use issue IDs in commits** (e.g., "Fix rendering bug (nm-42)")

## Development Workflow

### Initial Setup
```bash
# System dependencies (macOS)
brew install cairo pango gdk-pixbuf libffi

# Python environment
uv venv
uv pip install -e ".[dev]"

# direnv (optional but recommended)
direnv allow
```

### Code Quality Checks
```bash
# Format code
ruff format .

# Lint (auto-fix when possible)
ruff check . --fix

# Type checking
mypy render_to_webp.py

# Run tests
pytest
```

### Background Services & tmux

**IMPORTANT**: Use **tmux** for all long-running processes and dev servers. This keeps processes running even if the terminal disconnects and makes it easy to monitor background tasks.

#### When to Use tmux
- Running development servers (FastAPI, Flask, etc.)
- Long-running batch processes (embedding generation, bulk rendering)
- Workers or daemons that need to run continuously
- Any process that should persist beyond the current shell session

#### Naming Convention
**Always use descriptive, project-specific session names:**
- Format: `neumann-<purpose>` (e.g., `neumann-api`, `neumann-worker`, `neumann-embeddings`)
- Use lowercase with hyphens
- Be specific about what's running in the session

#### Workflow

**1. Creating a new tmux session:**
```bash
# Create and attach to a named session
tmux new -s neumann-api

# When starting a session, ALWAYS inform the user:
# "Started tmux session 'neumann-api' for the FastAPI development server"
```

**2. Detaching from a session (keep it running):**
```bash
# Press: Ctrl+b, then d
# Or use: tmux detach
```

**3. Listing active sessions:**
```bash
tmux ls
# Example output:
# neumann-api: 1 windows (created Wed Oct 29 14:30:00 2025)
# neumann-worker: 1 windows (created Wed Oct 29 14:45:00 2025)
```

**4. Attaching to an existing session:**
```bash
tmux attach -t neumann-api
# Or shorthand: tmux a -t neumann-api
```

**5. Killing a session:**
```bash
tmux kill-session -t neumann-api
```

#### Best Practices
- **Always inform the user** when you create a tmux session, including:
  - The session name
  - What's running in it
  - How to attach to it
- **Check for existing sessions** with `tmux ls` before creating new ones
- **Use descriptive names** so the user knows what each session is for
- **One purpose per session** (don't mix API server + worker in same session)
- **Clean up** unused sessions with `tmux kill-session` when done

#### Example Usage

```bash
# Starting a FastAPI dev server in tmux
tmux new -s neumann-api
uvicorn main:app --reload --port 8000

# Inform user:
# "Started tmux session 'neumann-api' running FastAPI on port 8000"
# "Attach with: tmux attach -t neumann-api"
# "Detach with: Ctrl+b, then d"
```

### Git Workflow
- Commits use ProductThor account (ProductThor@users.noreply.github.com)
- Always update CLAUDE.md when making significant architectural changes
- Keep README.md in sync with CLAUDE.md for user-facing changes

## Future Roadmap

### Phase 2: Embedding Generation
- Add text embeddings using sentence-transformers
- Add image embeddings using CLIP/SigLIP
- Store embeddings in ChromaDB with tile metadata

### Phase 3: Search API
- FastAPI web service
- Text search endpoint (keyword + semantic)
- Image search endpoint (visual similarity)
- Hybrid search endpoint (combined text + image)

### Phase 4: UI & UX
- Web UI for uploading documents
- Real-time search results with tile preview
- Document viewer with highlighted matches
- API documentation with OpenAPI/Swagger

### Phase 5: Scale & Performance
- Parallel processing with multiprocessing/Ray
- Batch embedding generation
- Caching layer (Redis)
- Monitoring and observability

## Common Tasks

### Add a new file type
1. Add extension to `SUPPORTED_MD` or `SUPPORTED_CODE` in `render_to_webp.py`
2. For code files, Pygments will auto-detect the lexer
3. For Markdown variants, may need to adjust parser config

### Change tile size or overlap
```bash
python render_to_webp.py \
  --input-dir ./docs \
  --out-dir ./out \
  --tile-size 512 \      # Smaller tiles (512x512)
  --tile-overlap 0.20    # More overlap (20%)
```

### Customize styling
```bash
# Create custom.css with your styles
echo "body { font-family: 'Times New Roman'; }" > custom.css

python render_to_webp.py \
  --input-dir ./docs \
  --out-dir ./out \
  --extra-css-path custom.css
```

### CLI usage
You can invoke via `python render_to_webp.py …` or the script entry `neumann` defined in `pyproject.toml`. Prefer `neumann` for consistency with packaging.

### Examples: enabling tiles and manifests
```bash
# Generate pages only (default)
neumann --input-dir ./docs --out-dir ./out

# Generate tiles (bands) and tile manifest (JSONL)
neumann --input-dir ./docs --out-dir ./out \
  --emit both --tile-mode bands --band-height 512 \
  --manifest jsonl

# Generate tiles (grid) with 20% overlap
neumann --input-dir ./docs --out-dir ./out \
  --emit both --tile-mode grid --tile-size 512 --tile-overlap 0.20
```

### Debug rendering issues
- Check the intermediate PDF in output directory
- Use `--dpi 300` for higher resolution
- Try different `--pygments-style` options (monokai, github, etc.)

## Notes

- Python 3.10+ is required (`.python-version` file specifies 3.10)
- Virtual environment is in `.venv/` (auto-activated with direnv)
- Output can be large (~1MB per page with tiles)
- WeasyPrint requires system libraries (Cairo, Pango)
- Type hints are enforced by mypy in dev mode

## Questions or Issues?

When working on this project:
1. **Always check this file first** for context and patterns
2. **Update this file** when making architectural changes
3. **Keep README.md in sync** with user-facing changes
4. **Use uv for dependencies** (not pip or poetry)
5. **Follow ruff formatting** (120 char line length)
6. **Add type hints** for all new functions
7. **Use ast-grep** for structural code search and refactoring
8. **Use tmux** for dev servers and long-running processes (with descriptive session names)

For package documentation, use Context7 MCP to fetch latest docs:
- WeasyPrint: `/FedericoCeratto/weasyprint`
- ChromaDB: `/chroma-core/chroma`
- FastAPI: `/tiangolo/fastapi`

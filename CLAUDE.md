# Neumann - Project Context

## Project Overview

Neumann is a document processing pipeline that converts text files (Markdown, code) into searchable image tiles. The ultimate goal is to build a hybrid search system that combines:
- **Text search**: Traditional keyword and semantic search on document content
- **Visual search**: Image embeddings for visual similarity search
- **Hybrid search**: Combined text + image retrieval using ChromaDB

## Current Status

**Phase 1: Document → Image Pipeline** ✓ (Current)
- Single-file CLI script (`render_to_webp.py`)
- Converts Markdown and code files to PDF using WeasyPrint
- Renders PDFs to high-quality WebP images
- Generates overlapping tiles for efficient image search
- Produces JSONL/JSON/TSV manifests with tile metadata and SHA-256 hashes

## Architecture

### Current Structure (Single Script)
```
neumann/
├── render_to_webp.py       # Main CLI script
├── pyproject.toml           # Modern Python project config (PEP 621)
├── .python-version          # Python 3.13.2
├── .envrc                   # direnv auto-activation
├── README.md                # User documentation
└── CLAUDE.md                # This file (context for Claude)
```

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

### Development Tools
- **uv**: Modern Python package manager (fast pip/poetry replacement)
- **direnv**: Auto-activate virtual environment on directory entry
- **ruff**: Fast Python linter and formatter (replaces black, isort, flake8)
- **mypy**: Static type checking
- **pytest**: Testing framework

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

### Why WebP?
- Better compression than JPEG/PNG (smaller files)
- Supports both lossy and lossless modes
- Native support in modern browsers
- Efficient for tile-based storage

### Why overlapping tiles?
- Prevents content from being split across tile boundaries
- Improves search recall (same content appears in multiple tiles)
- Default 10% overlap balances storage vs. recall

### Why JSONL for manifests?
- Streaming-friendly (process one record at a time)
- Easy to append new tiles
- Simple to import into databases
- Still human-readable (unlike binary formats)

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

### Debug rendering issues
- Check the intermediate PDF in output directory
- Use `--dpi 300` for higher resolution
- Try different `--pygments-style` options (monokai, github, etc.)

## Notes

- Python 3.13.2 is required (`.python-version` file)
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

For package documentation, use Context7 MCP to fetch latest docs:
- WeasyPrint: `/FedericoCeratto/weasyprint`
- ChromaDB: `/chroma-core/chroma`
- FastAPI: `/tiangolo/fastapi`

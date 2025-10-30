# Neumann Implementation Plan - Single-File CLI with Pages & Tiles

## Overview

This plan details the implementation of a single-file Python CLI (`render_to_webp.py`) that converts Markdown and code files to PDF, then to WebP images with support for both full pages and overlapping tiles.

## Key Features

### Default Behavior
- **Emits pages only** by default (`--emit {pages,tiles,both}`; default: `pages`)
- **No manifest generated** by default (`--manifest {jsonl,json,tsv,none}`; default: `none`)
- **Tile hashing enabled** when tiles are generated (SHA-256), with `--no-hash-tiles` to disable
- **Pages-first philosophy**: Start simple with pages, add tiles only when needed for search/embedding

### Supported Input Formats

**Markdown:**
- `.md`, `.markdown`, `.mdx`

**Code Files:**
- JavaScript/TypeScript: `.js`, `.ts`, `.tsx`, `.jsx`
- Python: `.py`
- Systems: `.go`, `.rs`, `.java`, `.c`, `.cpp`, `.h`, `.hpp`, `.cs`
- Shell: `.sh`, `.bash`, `.zsh`
- Config: `.json`, `.yml`, `.yaml`, `.toml`
- Web: `.html`, `.css`

## Technical Architecture

### Pipeline Flow
```
Input Files (MD/Code)
  ↓
HTML Generation (with syntax highlighting)
  ↓
PDF Generation (WeasyPrint)
  ↓
WebP Page Rasterization (PyMuPDF + Pillow)
  ↓
Tile Generation (with configurable overlap)
  ↓
SHA-256 Hashing (optional)
  ↓
Manifest Generation (JSONL/JSON/TSV)
```

### Dependencies

**Core Processing:**
- `weasyprint==62.3` - HTML → PDF rendering with Cairo backend
- `pymupdf==1.24.8` - PDF → image rasterization
- `pillow==10.4.0` - Image manipulation and WebP encoding
- `pygments==2.18.0` - Syntax highlighting for code files
- `markdown==3.6` - Markdown parsing with extensions

**System Requirements:**
- Python 3.10+
- macOS: `brew install cairo pango gdk-pixbuf libffi`
- Ubuntu: `sudo apt-get install libcairo2 libpango-1.0-0 libgdk-pixbuf2.0-0 libffi-dev`

## CLI Interface

### Basic Usage (Pages Only - Default)
```bash
python render_to_webp.py \
  --input-dir ./my_docs \
  --out-dir ./out
```

### With Tiles (Explicit Opt-In)
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

### Configuration Options

**Page Styling:**
- `--page-width-px` - Page width in pixels (default: 1200)
- `--body-font-size` - Body text size (default: 15)
- `--code-font-size` - Code block text size (default: 14)
- `--line-height` - Line height multiplier (default: 1.45)
- `--pygments-style` - Syntax highlighting theme (default: "friendly")
- `--extra-css-path` - Path to additional CSS file

**Rendering Quality:**
- `--dpi` - Rasterization DPI (default: 200; recommended: 200-220)
- `--webp-quality` - WebP quality 0-100 (default: 90)
- `--webp-lossless` - Use lossless WebP encoding (larger files)

**Tiling:**
- `--tile-size` - Tile edge length in pixels (default: 1024)
- `--tile-overlap` - Fractional overlap 0.0-0.5 (default: 0.10)

**Output Control:**
- `--emit` - Output mode: `pages`, `tiles`, or `both` (default: pages)
- `--manifest` - Manifest format: `jsonl`, `json`, `tsv`, or `none` (default: none)
- `--no-hash-tiles` - Disable SHA-256 hashing (enabled by default when tiles are generated)

## Data Structures

### Tile Manifest Record (JSON)
```json
{
  "doc_id": "path__to__document",
  "page": 1,
  "tile_idx": 0,
  "tile_path": "/path/to/tile.webp",
  "page_path": "/path/to/page.webp",
  "bbox": {"x0": 0, "y0": 0, "x1": 1024, "y1": 1024},
  "tile_px": 1024,
  "overlap": 0.10,
  "source_pdf": "/path/to/source.pdf",
  "source_file": "/path/to/original.md",
  "sha256": "abc123..."
}
```

### Output Directory Structure
```
out/
├── path__to__doc1/
│   ├── doc1.pdf
│   ├── pages/
│   │   ├── doc1-p001.webp
│   │   ├── doc1-p002.webp
│   │   └── pages.txt
│   └── tiles/
│       ├── doc1-p001-x0-y0.webp
│       ├── doc1-p001-x0-y924.webp
│       ├── tiles.jsonl (or .json, .tsv)
│       └── ...
```

## Implementation Components

### 1. HTML Generation
- **Markdown to HTML**: Python-Markdown with extensions (fenced_code, codehilite, tables, toc, sane_lists, attr_list)
- **Code to HTML**: Pygments with auto-detection of language lexer
- **CSS Styling**: Embedded print-optimized CSS with configurable fonts and sizes

### 2. PDF Generation
- WeasyPrint HTML renderer with Cairo backend
- Deterministic rendering (same input → same output)
- A4 page size with 24px margins

### 3. Image Rasterization
- PyMuPDF for PDF → pixel data conversion
- Configurable DPI scaling (72 DPI base × scale factor)
- RGB color space (no alpha channel)

### 4. Tile Generation
- Sliding window approach with configurable overlap
- Edge case handling for images smaller than tile size
- Maintains spatial metadata (bounding boxes)

### 5. Content Hashing
- SHA-256 for each tile (1MB read chunks)
- Optional (can be disabled with `--no-hash-tiles`)
- Enables deduplication and change detection

### 6. Manifest Generation
- **JSONL**: One JSON object per line (streaming-friendly)
- **JSON**: Single array of all records (human-readable)
- **TSV**: Tab-separated values (database import)
- **None**: Skip manifest generation

## Design Decisions

### Why Single-File Script?
- Fast prototyping and iteration
- Easy to understand and modify
- Can be refactored into package structure later
- Follows "start simple, grow complex" principle

### Why Pages-Only by Default?
- **Simplicity first**: Most users want page images for preview/browsing, not search
- **Storage efficiency**: Tiles generate many files (can be 10-50x more files per document)
- **Progressive enhancement**: Users can opt into tiles when they need search/embedding
- **Faster default**: Pages-only rendering is faster (no tiling overhead)
- **Clear intent**: Making tiles explicit ensures users understand the additional storage/compute cost

### Why Hash by Default?
- Enables deduplication across documents
- Supports change detection (re-render only modified content)
- Minimal performance overhead (~10% increase)
- Future-proofs for caching and incremental updates

### Why 10% Overlap?
- Prevents content split across tile boundaries
- Improves search recall (same content in multiple tiles)
- Balances storage cost vs. recall improvement
- Overlap is configurable for experimentation

### Why JSONL for Manifests?
- Streaming-friendly (process one record at a time)
- Easy to append new tiles without parsing entire file
- Simple to import into databases (e.g., ChromaDB, PostgreSQL)
- Still human-readable (unlike binary formats)

## Future Enhancements

### Phase 2 Integration Points
- Manifest can be directly imported into ChromaDB
- `tile_path` and `sha256` enable efficient embedding storage
- `bbox` coordinates support spatial search queries
- `page_path` provides full-page context for results

### Potential Improvements
- Parallel processing with multiprocessing for batch jobs
- Incremental rendering (skip unchanged files)
- PDF metadata extraction (author, title, creation date)
- OCR support for scanned documents
- Vector format preservation (SVG diagrams, math)

## Testing Strategy

### Unit Tests
- HTML generation for Markdown variants
- Code highlighting for all supported languages
- Tile generation edge cases (small images, overlap=0)
- Manifest format validation

### Integration Tests
- End-to-end pipeline for sample documents
- Output directory structure validation
- Hash consistency across runs
- Manifest record completeness

### Performance Benchmarks
- Rendering speed (pages per second)
- Memory usage for large documents
- Tile generation overhead
- Hash computation cost

## References

### Documentation
- WeasyPrint: https://doc.courtbouillon.org/weasyprint/
- PyMuPDF: https://pymupdf.readthedocs.io/
- Pygments: https://pygments.org/docs/
- Python-Markdown: https://python-markdown.github.io/

### Similar Tools
- `pandoc` - Universal document converter (no tiling)
- `wkhtmltopdf` - HTML to PDF (unmaintained)
- `playwright` - Browser automation (heavy dependency)

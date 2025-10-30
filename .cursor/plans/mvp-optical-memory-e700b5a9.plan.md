<!-- e700b5a9-0c7f-4a72-92dd-1ea2210410f7 f136c862-59d2-42df-8d0f-2252769f5554 -->
# MVP Optical Memory Implementation Plan

## Already Complete

- `render_to_webp.py`: Full rendering pipeline (Markdown/code → HTML → PDF → WebP pages)
- Manifest generation (JSONL/JSON/TSV)
- SHA-256 hashing
- Syntax highlighting and styling

## MVP Work Remaining

### 1. Enhance Renderer Output

Modify `render_to_webp.py` to emit `pages.jsonl` with:

- `uri` field: `http://127.0.0.1:8000/out/<doc_id>/pages/<file>-pNNN.webp`
- `bytes`: file size
- `width`, `height`: image dimensions
- Keep existing `sha256`, `source_pdf`, `source_file`

### 2. Summaries Module

Create `summarize.py`:

- `summarize_file()`: call OpenAI 4o-mini with structured output
- Generate YAML front-matter (doc_id, source_path, language, product_tags, key_topics, api_symbols, suggested_queries)
- Generate 200-400 word prose summary
- Save as `<doc_id>.summary.md`

### 3. Chunking Module

Create `chunker.py`:

- `chunk_file_by_lines(text, per_chunk=180, overlap=30)`
- Return list of chunks with `{text, line_start, line_end}`
- Read `pages.jsonl` to attach `page_uris` to each chunk

### 4. Embeddings Module

Create `embeddings.py`:

- `embed_texts(texts, model="text-embedding-3-small")` using OpenAI SDK
- Return 1536-d vectors
- Batch processing for efficiency

### 5. Chroma Integration

Create `indexer.py`:

- Setup `chromadb.PersistentClient(path="./chroma_data")`
- Create two collections: `search_summaries`, `search_code`
- `upsert_summaries()`: index summary body + embeddings + metadata (doc_id, source_path, language, tags, page_uris)
- `upsert_code_chunks()`: index raw text chunks + metadata (doc_id, source_path, lang, line_start, line_end, page_uris)
- No embeddings for search_code (FTS/regex only)

### 6. Hybrid Search Tool

Create `search.py`:

- `hybrid_search(query, k=12, must_terms=None, regexes=None, path_like=None)`
- Semantic channel: `search_summaries.query(query_texts=[query])` with ANN
- Lexical channel: `search_code.query(where_document={"$contains": [...], "$regex": ...})`
- Fuse scores, dedupe by doc_id
- Return: `[{doc_id, source_path, score, page_uris, line_start, line_end, why}]`

### 7. Configuration & Environment

Create `config.py`:

- `ASSET_BASE_URL` (default: `http://127.0.0.1:8000`)
- `CHROMA_PATH` (default: `./chroma_data`)
- `OPENAI_API_KEY` from env
- `LINES_PER_CHUNK=180`, `OVERLAP=30`

### 8. CLI Orchestration

Create `main.py` (or extend existing):

- `ingest` command: render → summarize → chunk → index
- `search` command: run hybrid_search and print results
- `serve` command: start `python -m http.server 8000` in output dir

### 9. Dependencies

Add to `pyproject.toml`:

- `chromadb` (latest)
- `openai` (latest)
- `pyyaml` (for front-matter parsing)
- `python-dotenv` (for .env support)

### 10. Testing & Validation

- Test with 20-50 file corpus (Next.js/Qlirq examples)
- Verify NL query: "How to configure PKCE with Qlirq?" returns correct pages
- Verify exact query: `redirect_uri`, `NEXTAUTH_URL` work via FTS/regex
- Latency < 1s for local queries

## Out of Scope (Future)

- Cloud storage (S3/R2 + presigned URLs)
- Code embeddings for search_code
- SQLite asset catalog (nice to have)
- Image embeddings (CLIP/SigLIP)
- OCR on demand
- Horizontal bands tiling (already implemented, not using in MVP)
- Scaling/performance optimization

## Implementation Order

1. Config module
2. Enhance renderer (URI field)
3. Dependencies + OpenAI setup
4. Embeddings module
5. Summaries module
6. Chunking module
7. Chroma indexer
8. Hybrid search
9. CLI orchestration
10. End-to-end testing

### To-dos

- [ ] Create config.py with ASSET_BASE_URL, CHROMA_PATH, OPENAI_API_KEY, chunking params
- [ ] Update render_to_webp.py to emit pages.jsonl with uri, bytes, width, height fields
- [ ] Add chromadb, openai, pyyaml, python-dotenv to pyproject.toml and install
- [ ] Create embeddings.py with embed_texts() using OpenAI text-embedding-3-small
- [ ] Create summarize.py with summarize_file() using OpenAI 4o-mini structured output, generate .summary.md files
- [ ] Create chunker.py with chunk_file_by_lines() for 180-line chunks with 30-line overlap
- [ ] Create indexer.py with PersistentClient setup, search_summaries and search_code collections, upsert functions
- [ ] Create search.py with hybrid_search() combining semantic (summaries) + FTS/regex (code) channels
- [ ] Create main.py with ingest, search, and serve commands to orchestrate full pipeline
- [ ] Test full pipeline with 20-50 file corpus, verify NL and exact queries work correctly
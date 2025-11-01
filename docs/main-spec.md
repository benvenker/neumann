Below is a clean, combined **functional + technical spec** for your MVP “optical memory” datastore, including the **image storage/URI plan**. It’s written so you can hand it to a fresh chat (or a teammate) and get an execution plan without reopening all the design threads.

---

## 0) Goal & scope

Build a local-first datastore that lets an agent:

* **Ingest** a folder of source files (code/markdown/etc.), render **page WebPs** (no tiling in MVP).
* Optionally **summarize** each file into a structured, short, retrieval‑oriented summary.
* **Index** two channels in Chroma:
  **A)** semantic NL over summaries, **B)** exact/regex over raw file **line-chunks**.
* **Search (hybrid)**: run semantic + exact/regex, fuse results, and return **page WebP URIs** (plus file path, line ranges, and “why” it matched).

> Notes:
> • HTML→PDF via **WeasyPrint** (`HTML(...).write_pdf()`), then PDF→WebP with **PyMuPDF** (`page.get_pixmap(dpi=…)`) + **Pillow**. We’re relying on the official APIs for both. ([CourtBouillon Docs][1])
> • Chroma supports vector queries plus **full‑text** (`$contains`) and **`$regex`** through `where_document`—we’ll use both. ([Chroma Docs][2])
> • If you test **Chroma Cloud**, keep each record’s `document` under **16,384 bytes** (chunking solves this). Self‑hosted is looser, but “small document per embedding” is still the guidance for performance. ([Chroma Docs][3])

---

## 1) Functional specification

### 1.1 Ingest & render (pages‑only)

* Input: directory of text files (.md/.mdx/.ts/.tsx/.js/.py/.json/.yml/…).
* Process:

  1. Convert Markdown/code to HTML with syntax highlighting and tight, high‑contrast CSS.
  2. **WeasyPrint** render to **PDF**.
  3. **PyMuPDF** rasterize each PDF page to **WebP** at ~200 DPI (tunable).
  4. Emit a **`pages.jsonl` manifest** per source with `doc_id`, `page`, `uri` (see §3), `sha256`, `bytes`, `width`, `height`, `source_pdf`, `source_file`.
* Output: `out/<doc_id>/pages/<file>-pNNN.webp` + `pages.jsonl`.
  *Rationale:* WeasyPrint’s `HTML(...).write_pdf()` is the direct way to go from HTML to PDF; PyMuPDF’s `Page.get_pixmap(dpi=…)` is the direct way to rasterize at a target resolution. ([CourtBouillon Docs][1])

### 1.2 (Optional) Summaries

* For each source file, generate a **single, structured summary**: YAML front‑matter + 200–400‑word body.
* The body will be embedded and indexed for **natural‑language** retrieval; the YAML fields are stored in metadata for filtering.

### 1.3 Chunk raw files by **lines**

* Split each file into **180 lines** with **30‑line overlap** (tunable).
* Keep `line_start`, `line_end`, `source_path`, `lang`, and attach the file’s `page_uris` from `pages.jsonl`.
* Store the **raw text** in Chroma’s `document` to enable **full‑text** and **regex** matching (no embeddings required in MVP). Chroma’s `where_document` supports both `$contains` and `$regex`. ([Chroma Docs][2])

### 1.4 Index

* **Collection A — `search_summaries`**

  * `document`: summary body (prose).
  * **Embedding**: OpenAI `text‑embedding‑3‑small` (1536‑dim). ([OpenAI Platform][4])
  * `metadata`: flattened fields from YAML + `page_uris`.
* **Collection B — `search_code`**

  * `document`: raw chunk text (lines).
  * `metadata`: `{source_path, lang, line_start, line_end, doc_id, page_uris}`.
  * (Embeddings optional; start FTS/regex‑only.)

### 1.5 Search (tool/MCP surface)

* Input: `query: str`, `k: int`, optional `must_terms: list[str]`, `regexes: list[str]`, `path_like: str`.
* Steps:

  1. **Semantic** over `search_summaries` (top‑k).
  2. **Lexical** over `search_code` with `where_document`: `$contains` for keywords + `$regex` for identifiers/IDs; optional `where` on `source_path`.
  3. **Fuse** scores using weighted sum (0.6 semantic + 0.4 lexical by default), with RRF as tie-breaker; group by `(doc_id)`, map to **page_uris**, and return hits with "why" signals and transparent score breakdown.
* Output (per hit): `{doc_id, source_path, score, page_uris, line_start?, line_end?, why[]}`.

**Lexical search implementation details:**

The lexical channel uses Chroma's `where_document` filter with `$contains` (AND logic for multiple terms) and `$regex` (OR logic for multiple patterns). Path filtering (`path_like`) is done client-side after retrieval because ChromaDB metadata filters don't support substring matching. Fetch strategy scales with path filtering: `fetch_limit = k * 3` when `path_like` is provided to account for selective filtering. Results include "why" signals explaining which terms, regexes, or path filters matched.

### 1.6 Context packing for the agent

* The tool returns **only URIs** of **page WebPs** (and pointers). The agent attaches those images as context in its next model call.

---

## 2) Technical specification

### 2.1 Components

* **Renderer** (Python): HTML→PDF (WeasyPrint), PDF→WebP (PyMuPDF + Pillow). ([CourtBouillon Docs][1])
* **Summarizer** (Python): small hosted LLM; writes `.summary.md`.
* **Indexer** (Python): builds Chroma collections from `pages.jsonl`, summaries, and line‑chunks.
* **Search tool** (Python): hybrid query + fusion; returns page URIs + pointers.

### 2.2 Data artifacts

**A) `pages.jsonl`** (one line per page)

```json
{"doc_id":"path__to__file.ts","page":1,
 "uri":"http://127.0.0.1:8000/out/path__to__file.ts/pages/file-p001.webp",
 "sha256":"…","bytes":123456,"width":1280,"height":960,
 "source_pdf":"…/file.pdf","source_file":"repo/path/to/file.ts"}
```

**B) `*.summary.md`** (per file)

```yaml
---
doc_id: path__to__file.ts
source_path: repo/path/to/file.ts
language: ts
product_tags: [Next.js, Qlirq, auth]
last_updated: 2025-10-20
key_topics: [PKCE, callback, App Router, env vars]
api_symbols: [createAuthClient, redirect_uri, pkce_verifier]
related_files: [repo/path/a.ts]
suggested_queries:
  - How do I configure PKCE with Qlirq in Next.js?
---
# Summary
(200–400 words of concise prose)
```

**C) Chroma collections**

* `search_summaries`:

  * `id = doc_id`
  * `document = summary body`
  * `embedding = text-embedding-3-small (1536‑d)`
  * `metadata =` flattened YAML + `page_uris[]`
* `search_code`:

  * `id = f"{doc_id}:chunk_{i}"`
  * `document = raw text (lines)`
  * `metadata = {source_path, lang, line_start, line_end, doc_id, page_uris[]}`

*(Both `query` and `get` support `where`/`where_document`, so you can combine vector search with FTS/regex filters.)* ([Chroma Docs][5])

### 2.3 Image storage & URIs

**Local (dev) — Files + local HTTP server**

* Keep assets on disk under `out/…`.
* Serve with a one‑liner: `python -m http.server 8000`.

  * Use only for development; Python docs warn `http.server` is **not for production**. ([Python documentation][6])
* Store the **HTTP URI** in all manifests/metadata so the agent can fetch without directory logic.

**Optional local catalog — SQLite**

* Maintain `assets.sqlite` as an **asset manifest** (URIs, hashes, sizes, WxH, kind=page/tile, `doc_id`, `page`).
* Benefits: fast lookups/joins, integrity checks; zero infra (single file).
* FTS is SQLite **FTS5** (nice if you later want a tiny auxiliary search). ([SQLite][7])

**Cloud (prod) — Object storage + signed URLs**

* Upload assets to S3/R2; return **HTTPS URIs** (optionally **presigned**). Presigned URLs grant time‑limited access to S3 objects without changing bucket policy. ([AWS Documentation][8])
* **Cloudflare R2** is **S3‑compatible** and supports **presigned URLs** via S3 signing flow. ([Cloudflare Docs][9])
* Keep the same metadata fields; only the URI base changes.

**Avoid data URIs for large pages**

* `data:` URLs embed bytes inline, which bloats payloads and breaks caching; use them only for very small assets. ([MDN Web Docs][10])

### 2.4 APIs / function signatures (Python)

**Renderer**

```python
def render_folder_to_pages(input_dir: str, out_dir: str, *, dpi=200) -> None:
    """Writes PDFs and page WebPs; emits pages.jsonl with uri/sha256/bytes/w,h."""
```

**Summaries**

```python
def summarize_file(source_path: str, text: str) -> dict:
    """Returns {front_matter..., summary_md} (structured output)."""
```

**Chunking**

```python
def chunk_file_by_lines(text: str, lines_per_chunk=180, overlap=30) -> list[dict]:
    """[{text, line_start, line_end}, ...]"""
```

**Indexing (Chroma)**

```python
def index_summaries(summaries_dir: str, chroma_path="./chroma_data") -> None: ...
def index_code(root_dir: str, pages_glob: str, chroma_path="./chroma_data") -> None: ...
```

**Hybrid search (tool/MCP)**

```python
def hybrid_search(query: str, k=12,
                  must_terms: list[str] | None = None,
                  regexes: list[str] | None = None,
                  path_like: str | None = None) -> list[dict]:
    """Return ranked {doc_id, source_path, page_uris, line_start?, line_end?, why[], score}."""
```

### 2.5 Configuration

* `ASSET_BASE_URL`: e.g., `http://127.0.0.1:8000` (dev) → `https://cdn.example.com` (prod).
* `OPENAI_API_KEY` for embeddings/summaries.
* Chroma: local `PersistentClient(path=./chroma_data)` in MVP; consider Cloud later (watch 16‑KB doc cap). ([Chroma Docs][3])

### 2.6 Dependencies

* **Rendering**: `weasyprint` (HTML→PDF), `pymupdf` (PDF→pixmap), `Pillow` (WebP save). ([CourtBouillon Docs][1])
* **Index/Search**: `chromadb`. (Docs cover `query`/`get` and `where_document` FTS/regex.) ([Chroma Docs][5])
* **Embeddings**: `openai` (use `text-embedding-3-small`, 1536 dim). ([OpenAI Platform][4])
* **Summaries**: any small hosted LLM; OpenAI small (e.g., 4o‑mini) is fine—use structured outputs if you want strict JSON.
* **Optional**: `sqlite3` (asset catalog), `tiktoken` (token estimation), `pyyaml` (front matter), `pydantic` (validation).

---

## 3) Pipelines (concise)

**A) Rendering**
`source files → HTML → WeasyPrint.write_pdf() → PyMuPDF.get_pixmap(dpi=200) → Pillow.save(..., "WEBP") → pages.jsonl (with http URIs)` ([CourtBouillon Docs][1])

**B) Summaries (optional)**
`file text → small LLM → .summary.md (YAML + body) → embed body (1536‑d) → upsert to search_summaries` ([OpenAI Platform][4])

**C) Chunk + index raw text**
`file text → line chunks (180/30) → upsert to search_code (document = raw text; metadata = line_start/end, page_uris)`
*(If Chroma Cloud, chunking also keeps docs <16 KB.)* ([Chroma Docs][3])

**D) Query (hybrid)**

* `summaries.query(query_texts=[q])` → semantic candidates.
* `search_code.query(where_document={"$contains":[…], "$and":[{"$regex":…}]}, where={"source_path":{"$contains": path_like}})` → exact candidates.
* Fuse, dedupe by `(doc_id)`, return **page URIs** + pointers. ([Chroma Docs][5])

---

## 4) Operational notes

* **Dev server**: `python -m http.server 8000` is perfect for local testing, **not** production. Use object storage + CDN (S3/R2 + presigned URLs) when you move past local. ([Python documentation][6])
* **Image format**: Keep WebP; Pillow’s `Image.save(..., "WEBP", quality=90)` is standard and supported. ([Pillow (PIL Fork)][11])
* **Performance**: Smaller records work better; this is also Chroma’s recommended shape for scaling. ([Chroma Docs][12])
* **Security**: Presigned URLs give time‑limited access without exposing credentials. ([AWS Documentation][8])

---

## 5) Acceptance criteria (MVP)

* Given 20–50 files (Next.js + Qlirq auth examples), **hybrid_search**:

  * NL: “How to configure PKCE with Qlirq in Next.js App Router?” returns relevant file **page URIs** in top‑5.
  * Exact: `redirect_uri`, `NEXTAUTH_URL`, `pkce_verifier` return code pages with correct `line_start/end`.
* Latency (local): < 1s for top‑10.
* Returned payloads are **URIs only** (no raw text in prompts); agent can attach those images directly.
* If testing Chroma Cloud, all `document` fields respect **16 KB** max. ([Chroma Docs][3])

---

## 6) Roadmap (post‑MVP)

1. Add embeddings to `search_code` for semantic‑on‑code (still keep FTS/regex).
2. Add **bands tiling** (page slices) if you want smaller vision payloads.
3. On‑demand **OCR** (only when quoting exact strings).
4. Optional **image embeddings** (SigLIP/CLIP) for cross‑modal text→image retrieval.
5. Swap local server for **S3/R2 + presigned URLs**; keep the same `uri` field so the agent code doesn’t change. ([AWS Documentation][8])

---

### One‑screen handoff (what to build next)

* **Renderer** writes **`pages.jsonl`** with **HTTP `uri`** fields (local server) + hash/size/WxH.
* **Summaries** (optional): generate `.summary.md`; embed body with **text‑embedding‑3‑small (1536‑d)**; upsert to `search_summaries`. ([OpenAI Platform][4])
* **Chunker**: 180/30 line chunks; upsert to `search_code` with `document = raw text` so **FTS/regex** work. ([Chroma Docs][2])
* **Search tool**: run semantic + FTS/regex, fuse, return **page URIs** + pointers.
* **Local asset server**: `python -m http.server 8000` (dev), plan for S3/R2 presigned URLs in prod. ([Python documentation][6])

If you want, I’ll turn this spec into a minimal repo scaffold (folders, `pyproject.toml`, CLI entrypoints) that implements just the IO contracts and leaves the internals stubbed for your new chat to fill in.

[1]: https://doc.courtbouillon.org/weasyprint/stable/api_reference.html?utm_source=chatgpt.com "API Reference - WeasyPrint 66.0 documentation - CourtBouillon"
[2]: https://docs.trychroma.com/docs/querying-collections/full-text-search?utm_source=chatgpt.com "Full Text Search and Regex - Chroma Docs"
[3]: https://docs.trychroma.com/cloud/quotas-limits?utm_source=chatgpt.com "Quotas & Limits - Chroma Docs"
[4]: https://platform.openai.com/docs/guides/embeddings?utm_source=chatgpt.com "Vector embeddings - OpenAI API"
[5]: https://docs.trychroma.com/docs/querying-collections/query-and-get?utm_source=chatgpt.com "Query and Get Data from Chroma Collections"
[6]: https://docs.python.org/3/library/http.server.html?utm_source=chatgpt.com "HTTP servers — Python 3.14.0 documentation"
[7]: https://sqlite.org/fts5.html?utm_source=chatgpt.com "SQLite FTS5 Extension"
[8]: https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html?utm_source=chatgpt.com "Download and upload objects with presigned URLs"
[9]: https://developers.cloudflare.com/r2/api/s3/api/?utm_source=chatgpt.com "S3 API compatibility · Cloudflare R2 docs"
[10]: https://developer.mozilla.org/en-US/docs/Web/URI/Reference/Schemes/data?utm_source=chatgpt.com "data: URLs - URIs - MDN Web Docs - Mozilla"
[11]: https://pillow.readthedocs.io/en/stable/handbook/tutorial.html?utm_source=chatgpt.com "Tutorial - Pillow (PIL Fork) 12.0.0 documentation"
[12]: https://docs.trychroma.com/guides/deploy/performance?utm_source=chatgpt.com "Performance - Chroma Docs"


Absolutely—here’s a consolidated **functional + technical spec** that merges the ingestion/indexing plan with a clean, URI‑based image storage approach. I’ve kept it implementation-ready but light on code so you can hand it straight to your planning agent.

---

## 1) Goal & scope

Build an MVP “optical memory” datastore for agents:

* **Ingest** source files → render **PDF → page WebP images** (no tiling for MVP).
* **Summaries‑first**: optionally generate a **structured summary** per file (YAML front‑matter + short prose) using a small LLM.
* **Light chunking**: split raw file text into **line‑based chunks** (e.g., 180 lines with 30 overlap).
* **Index** two Chroma collections:

  * `search_summaries`: **semantic** (OpenAI embeddings) + filterable metadata.
  * `search_code`: **exact match** (full‑text and regex on raw text), embeddings optional later.
    Chroma supports full‑text via `$contains` and regex via `$regex` in `where_document`. Under the hood this is backed by SQLite **FTS5**. ([Chroma Docs][1])
* **Search (tool/MCP)**: run a **hybrid** query (semantic over summaries + exact/regex over chunks), fuse results, and return **URIs** to page WebPs plus pointers (file path, page, line range).
* **Image storage**: develop locally on disk but **serve as HTTP URIs**, with a clean upgrade path to **S3 / Cloudflare R2 presigned URLs** later. ([Python documentation][2])

---

## 2) Functional specification

### Ingestion & rendering

* Accept a directory of Markdown / code / text files (ignore binaries).
* Render each file to **HTML → PDF → page WebP images**. Use WeasyPrint’s `HTML(...).write_pdf()` and PyMuPDF to rasterize pages to images. (WeasyPrint turns HTML/CSS into PDF; PyMuPDF creates Pixmaps you can save as WebP.) ([CourtBouillon Docs][3])
* Emit a **pages manifest** per file with metadata + **URI** for each page image.

### Summaries (optional but recommended now)

* For every source file, produce a **structured summary** (YAML front‑matter + 200–400 word prose).
* Use a **small, cheap LLM** with structured output; index the **summary body** semantically.

### Chunking (line‑based, light)

* Split raw file text into **chunks of ~180 lines with 30‑line overlap**.
* Store `line_start`/`line_end` and the file’s page URIs (from the pages manifest).

### Indexing (Chroma)

* `search_summaries`

  * **Embeddings**: OpenAI **`text-embedding-3-small`** (1536‑dim vectors).
  * **Document**: summary body text; **metadata**: front‑matter fields + `page_uris`. ([OpenAI Platform][4])
* `search_code`

  * **Document**: raw text chunk (enables exact match); **metadata**: `{path, lang, line_start, line_end, page_uris}`.
  * Query with **full‑text `$contains`** and **`$regex`**; add embeddings later if/when needed. (On **Chroma Cloud**, keep each document ≤ **16,384 bytes**—chunking ensures compliance.) ([Chroma Docs][1])

### Hybrid search (tool/MCP)

* Input: `query`, `k`, optional `must_terms[]`, `regexes[]`, `path_like`.
* Steps:

  1. **Semantic channel**: ANN over `search_summaries`.
  2. **Lexical channel**: FTS/regex over `search_code`.
  3. **Fusion**: combine scores, dedupe by `(doc_id, page)`.
  4. **Return**: **page WebP URIs** + pointers (`path`, `page`, `line_start/end`) + short “why”.

### Image storage & access (URIs end‑to‑end)

* **Dev**: serve the output folder via Python’s **`http.server`**; store the HTTP URL as the page’s `uri` in your manifests and Chroma metadata. (Great for local dev; not production.) ([Python documentation][2])
* **Asset catalog (optional)**: keep a tiny **SQLite** table of assets (id, doc_id, page, `uri`, `sha256`, bytes, width/height) as a manifest.
* **Prod upgrade**: upload images to **S3** or **Cloudflare R2** and return **presigned URLs** (temporary HTTPS links) instead of local HTTP URIs. R2 implements S3‑compatible presigned URLs; S3 presigned URLs grant time‑limited access without client creds. ([AWS Documentation][5])
* **Don’t inline large images** using `data:` URLs—these are best for **small** assets; you lose CDN caching and bloat payloads. ([MDN Web Docs][6])

---

## 3) Technical specification

### 3.1 Data artifacts

**A) Pages manifest** (`pages.jsonl` per source file)
One JSON object per page:

```json
{
  "doc_id": "src__auth__module.ts",
  "page": 1,
  "uri": "http://127.0.0.1:8000/out/src__auth__module.ts/pages/src__auth__module-p001.webp",
  "sha256": "<hex>",
  "bytes": 187432,
  "width": 1280,
  "height": 980,
  "source_pdf": "out/src__auth__module.ts/src__auth__module.pdf",
  "source_file": "src/auth/module.ts"
}
```

**B) Summary files** (`*.summary.md`)
YAML front‑matter + summary body (index the body semantically). Example keys:

```yaml
doc_id, source_path, language, product_tags[], last_updated,
key_topics[], api_symbols[], related_files[], suggested_queries[]
```

**C) Line chunks** (in‑memory items for upsert)

```json
{
  "id": "src__auth__module.ts:chunk_0007",
  "document": "<raw text lines [361..540]>",
  "metadata": {
    "doc_id": "src__auth__module.ts",
    "source_path": "src/auth/module.ts",
    "lang": "ts",
    "line_start": 361,
    "line_end": 540,
    "page_uris": [".../file-p001.webp", "..."]
  }
}
```

**D) (Optional) SQLite `assets` table** (local manifest)

```sql
CREATE TABLE assets (
  id TEXT PRIMARY KEY,          -- e.g., sha256 or doc_id:page
  doc_id TEXT NOT NULL,
  page INTEGER NOT NULL,
  kind TEXT CHECK(kind IN ('page','tile')) NOT NULL,
  uri TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  bytes INTEGER,
  width INTEGER, height INTEGER,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX assets_doc_page ON assets(doc_id, page);
```

> Chroma resource note: HNSW vector index is in memory; documents/metadata persist to disk. Plan capacity accordingly. ([Chroma Cookbook][7])

---

### 3.2 Collections in Chroma

**`search_summaries`**

* `id`: `doc_id`
* `document`: summary body (prose)
* `embedding`: **OpenAI `text-embedding-3-small` (1536‑d)**
* `metadata`: `{doc_id, source_path, language, product_tags[], last_updated, page_uris[]}`
  (This collection is used with ANN + optional metadata filters.) ([OpenAI Platform][4])

**`search_code`**

* `id`: `doc_id:chunk_{i}`
* `document`: raw text chunk (enables exact and regex searches)
* `metadata`: `{doc_id, source_path, lang, line_start, line_end, page_uris[]}`
* Use `where_document: {"$contains": "...", "$regex": "..."}` and `where` (metadata) to pre‑filter; Chroma’s query interface supports combining these with vector queries if/when you add embeddings. ([Chroma Docs][1])

> **Cloud constraint**: On **Chroma Cloud**, **Maximum document bytes = 16,384** per record—line chunking ensures compliance. ([Chroma Docs][8])

---

### 3.3 Core module surfaces (Python)

Keep files small and composable; examples below are **signatures**, not implementations.

**Renderer** (you already have this)

```python
def render_pages(input_dir: str, out_dir: str, base_url: str) -> None:
    """
    HTML → PDF → WebP pages, writes pages.jsonl with URIs built from base_url.
    Uses WeasyPrint write_pdf() and PyMuPDF Pixmap to save WebP.
    """
```

(WeasyPrint `write_pdf()` API; PyMuPDF Pixmap usage.) ([CourtBouillon Docs][3])

**Summarizer** (optional first pass; small LLM)

```python
def summarize_file(source_path: str, text: str) -> dict:
    """
    Returns: dict matching JSON schema (front-matter + 'summary_md').
    Write to <doc_id>.summary.md.
    """
```

**Chunker** (line‑based)

```python
def chunk_file_by_lines(text: str, per_chunk: int = 180, overlap: int = 30) -> list[dict]:
    """
    Returns [{"text": str, "line_start": int, "line_end": int}, ...]
    """
```

**Embeddings**

```python
def embed_texts(texts: list[str], model: str = "text-embedding-3-small") -> list[list[float]]:
    """Returns 1536-d vectors for summaries (OpenAI embeddings)."""
```

(OpenAI embedding dims for `text-embedding-3-small`.) ([OpenAI Platform][4])

**Indexing**

```python
def upsert_summaries(collection, items: list[dict]) -> None
def upsert_code_chunks(collection, items: list[dict]) -> None
```

**Hybrid search (tool/MCP)**

```python
def hybrid_search(
    query: str,
    k: int = 12,
    must_terms: list[str] | None = None,   # FTS exact terms
    regexes: list[str] | None = None,      # e.g., r"\bauth\b", r"redirect_uri"
    path_like: str | None = None           # metadata filter (substring)
) -> list[dict]:
    """
    Returns ranked page hits:
    [{ "doc_id", "source_path", "score", "page_uris":[...],
       "why":[...], "line_start":int|None, "line_end":int|None }]
    """
```

(Chroma query + `where_document` for **$contains / $regex**.) ([Chroma Docs][1])

---

### 3.4 Image storage: environments & URIs

**Dev (local)**

* Serve `out/` with Python’s `http.server` (e.g., `python -m http.server 8000`) and build URIs as `http://127.0.0.1:8000/out/...`. Note: `http.server` is convenient but **not** for production. ([Python documentation][2])

**(Optional) SQLite asset catalog**

* Populate the `assets` table from `pages.jsonl` (and later `tiles.jsonl` if you add tiling). This isn’t required but makes integrity checks and joins trivial.

**Prod (cloud)**

* Upload images to **S3** (or **Cloudflare R2**). Return **presigned URLs** (time‑limited HTTPS links) at query time or store them short‑lived in Chroma metadata. R2 implements S3‑compatible presigned URLs on its S3 endpoint. ([AWS Documentation][5])
* Avoid `data:` URLs for large assets—fine for **small** inline data, but inefficient for big page images (worse caching, larger payloads). ([MDN Web Docs][6])

---

## 4) Dependencies

* **Python**: `weasyprint`, `pymupdf` (PyMuPDF), `Pygments`, `chromadb`, `openai`, `pyyaml`, optionally `tiktoken`, `pydantic`.
* **System (rendering)**: WeasyPrint depends on Cairo/Pango; install per OS. (WeasyPrint docs.) ([CourtBouillon Docs][3])
* **Chroma**: local PersistentClient or Cloud; for Cloud, mind quotas (e.g., **16 KB doc bytes** limit). ([Chroma Docs][8])
* **OpenAI**: embeddings via official SDK; use `text-embedding-3-small` for summaries. ([OpenAI Platform][4])

---

## 5) Configuration & environment

* `ASSET_BASE_URL` (dev: `http://127.0.0.1:8000`) → used to build page `uri`s.
* `CHROMA_PATH` (local) or Cloud endpoint / API key.
* `OPENAI_API_KEY`.
* Chunk sizes: `LINES_PER_CHUNK=180`, `OVERLAP=30`.
* Embedding model: `text-embedding-3-small` (1536‑d). ([OpenAI Platform][4])

---

## 6) Acceptance criteria

* **Ingestion**: for a 20–50 file seed corpus, each source has a PDF, **page WebPs**, and a `pages.jsonl` with **valid URIs**.
* **Indexing**: `search_summaries` has one record per file (embedded); `search_code` has line chunks with raw text and `page_uris`.
* **Search**:

  * NL query (“How to configure PKCE with Qlirq in Next.js App Router?”) returns correct pages via the **summaries** channel.
  * Exact query (`redirect_uri`, `NEXTAUTH_URL`, `\bauth\b`) returns correct pages via the **FTS/regex** channel.
  * Results include **URIs** that resolve (dev: local HTTP; prod: presigned).
* **Latency**: local hybrid search in ≲1 s (excludes model time).
* **Cloud readiness**: no single document in Chroma Cloud exceeds **16 KB** if you choose Cloud. ([Chroma Docs][8])

---

## 7) Post‑MVP roadmap (non‑blocking)

* Add embeddings to `search_code` (semantic‑on‑code).
* Re‑enable **tiling** (horizontal bands) for smaller, zoomed‑in page payloads.
* **OCR on demand** for exact quotes (top pages only).
* Move images to **S3/R2** with **presigned URLs** + CDN in front. ([AWS Documentation][5])

---

If you’d like, I can turn this into a repo scaffold (folders, `pyproject.toml`, and CLI stubs) in the new chat; this spec already contains the module surfaces and data shapes your planning agent will need.

[1]: https://docs.trychroma.com/docs/querying-collections/full-text-search?utm_source=chatgpt.com "Full Text Search and Regex - Chroma Docs"
[2]: https://docs.python.org/3/library/http.server.html?utm_source=chatgpt.com "HTTP servers — Python 3.14.0 documentation"
[3]: https://doc.courtbouillon.org/weasyprint/stable/api_reference.html?utm_source=chatgpt.com "API Reference - WeasyPrint 66.0 documentation - CourtBouillon"
[4]: https://platform.openai.com/docs/guides/embeddings?utm_source=chatgpt.com "Vector embeddings - OpenAI API"
[5]: https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html?utm_source=chatgpt.com "Download and upload objects with presigned URLs"
[6]: https://developer.mozilla.org/en-US/docs/Web/URI/Reference/Schemes/data?utm_source=chatgpt.com "data: URLs - URIs - MDN Web Docs - Mozilla"
[7]: https://cookbook.chromadb.dev/core/resources/?utm_source=chatgpt.com "Resource Requirements"
[8]: https://docs.trychroma.com/cloud/quotas-limits?utm_source=chatgpt.com "Quotas & Limits - Chroma Docs"

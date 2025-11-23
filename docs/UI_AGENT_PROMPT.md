# Role: Senior UX/UI Engineer & Frontend Architect (Gemini 3 Pro Persona)

**Objective**: Build a high-density, "Quick & Dirty" but professional **Inspection Dashboard** for the Neumann search pipeline.
**Target Audience**: Developers/Engineers debugging search quality.
**Vibe**: "Linear" meets "Notion". Clean Light Mode, dense data, high contrast, minimal borders, white background to match documents.

---

## 1. Context & Goal
We have a hybrid search engine (Neumann) that indexes code and markdown. We need a Single Page Application (SPA) to inspect search results.
- **The Problem**: We need to verify if the "text match" (snippet) aligns with the "visual match" (WebP image) and why a document was ranked #1.
- **The Stack**: Next.js 14+ (App Router), Tailwind CSS, Lucide Icons, Shadcn UI.
- **The Backend**: A local FastAPI server at `http://localhost:8000`.

## 2. Data Shape (The "Source of Truth")

The UI **MUST** strictly adhere to this JSON structure.

### A. Search Response (`POST /api/v1/search/hybrid`)
The core list of results.
```json
[
  {
    "doc_id": "chroma__docs__cip__CIP-10112023_Authorization.md",
    "source_path": "/Users/ben/code/neumann/docs/chroma/docs/cip/CIP-10112023_Authorization.md",
    "score": 0.6924,
    "sem_score": 0.0,
    "lex_score": 0.6924,
    "rrf_score": 0.0164,
    "lex_term_hits": 16,
    "lex_regex_hits": 0,
    "page_uris": [
      "http://127.0.0.1:8000/out/chroma__docs__cip__CIP-10112023_Authorization.md/pages/CIP-10112023_Authorization-p001.webp",
      "http://127.0.0.1:8000/out/chroma__docs__cip__CIP-10112023_Authorization.md/pages/CIP-10112023_Authorization-p002.webp"
    ],
    "line_start": 1,
    "line_end": 180,
    "why": [
      "matched term: 'def' x4",
      "matched term: 'class' x12"
    ],
    "metadata": {
      "language": "markdown",
      "last_updated": "2025-11-03T08:10:16.198829Z",
      "product_tags": ["Chroma", "Authorization", "RBAC"],
      "key_topics": ["Multi-user Authorization", "Stateless Server Architecture"],
      "api_symbols": ["ServerAuthorizationProvider", "ChromaAuthzMiddleware"]
    }
  },
  {
    "doc_id": "chroma_docs__full-text-search.md",
    "source_path": "/Users/ben/code/neumann/test_data/chroma_docs/full-text-search.md",
    "score": 0.4333,
    "sem_score": 0.4333,
    "lex_score": 0.0,
    "rrf_score": 0.0164,
    "lex_term_hits": 0,
    "lex_regex_hits": 0,
    "page_uris": [
      "http://127.0.0.1:8000/out/chroma_docs__full-text-search.md/pages/full-text-search-p001.webp"
    ],
    "line_start": null,
    "line_end": null,
    "why": [
      "semantic match to query: 'search pipeline'",
      "distance=1.308"
    ],
    "metadata": {
      "language": "markdown",
      "last_updated": "2025-11-23T01:06:54.965205Z",
      "product_tags": ["Full Text Search", "Regular Expressions"],
      "key_topics": ["Full-text search operators", "Regex filtering"]
    }
  }
]
```

### B. Chunks Response (`GET /api/v1/docs/{doc_id}/chunks`)
For deep inspection.
```json
[
  {
    "chunk_id": "app__api__chat__route.ts#L1-L150",
    "doc_id": "app__api__chat__route.ts",
    "text": "import { createUIMessageStream } from \"ai\";\nimport { NextRequest, NextResponse } from \"next/server\";\n...",
    "source_path": "/Users/ben/code/neumann/test_data/app/api/chat/route.ts",
    "line_start": 1,
    "line_end": 150
  }
]
```

### C. Config Response (`GET /api/v1/config`)
Bootstrapping data.
```json
{
  "asset_base_url": "/api/v1/assets",
  "has_openai_key": true
}
```

---

## 3. UI Requirements (The "Vibe Coding" Part)

**Current Status**: The project is scaffolded, and the layout is solid (see "Base State" below).
**Goal**: Iterate on the existing components to wire up real data and polish the scoring visualization.

### A. Layout & Base State (Keep This)
- **Split View**: Sidebar (35%) / Main (65%).
- **Styling**: Zinc-50 to Zinc-900 scale, high density, clean white background.

### B. Component Refinements

#### 1. `ResultList` (Sidebar)
- **Refinement**: Upgrade the Score Visualization.
- **Badge Row**: Keep `Total` | `Sem` | `Lex` (or `Key`).
- **Interaction**: Implement a **HoverCard / Tooltip** on the **Total Score** badge.
  - **Content**: Show the full breakdown equation dynamically:
    ```
    Total = (Sem × w_sem) + (Lex × w_lex)
    -------------------------------------
    Semantic: 0.XX  (Weight: 0.6)
    Lexical:  0.XX  (Weight: 0.4)
      ↳ Keywords: 16
      ↳ Regex:    2
    ```
  - **Visuals**: Use a clean, tabular layout inside the tooltip. Small text (text-xs), high contrast.

#### 2. `InspectorPanel` (Main) -> "Visual" Tab
- **Refinement**: Wire up Real Images.
- **Logic**:
  1. On mount, fetch configuration from `GET /api/v1/config`.
  2. Store `asset_base_url` (e.g., `/api/v1/assets`).
  3. Render images using: `<img src={`${config.asset_base_url}/${result.doc_id}/pages/${page_filename}`} />`.
     *   *Note*: extracting `page_filename` from the full URI in `page_uris` might be needed, or just replace the base if the API returns full local URLs. (Actually, API returns full URLs, so just use them if they are accessible, or re-base them if needed).

#### 3. `InspectorPanel` -> "Text Context" Tab
- **Refinement**: Auto-scroll.
- **Logic**: If `result.line_start` is not null, auto-scroll the text view to that line number on load. Highlight the range.

## 4. Implementation Instructions for Gemini

1.  **Review**: Check `frontend/src` for existing components.
2.  **Update Models**: Ensure TypeScript interfaces match the new JSON shape (add `lex_term_hits`, `lex_regex_hits`).
3.  **Wire Config**: Create a hook or context to fetch/store `GET /config`.
4.  **Refine Components**:
    - Update `ResultCard` with the new Tooltip.
    - Update `VisualViewer` to use real image URLs.
5.  **Verify**: Ensure the "Why" strings and new lexical counts appear correctly.

**Deliverable**: Polished UI with working image rendering and transparent scoring math.

```
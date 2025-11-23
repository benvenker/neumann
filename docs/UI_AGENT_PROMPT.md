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

Act as an agentic coder. Break this down into:
1.  **Scaffolding**: Setup Next.js, Tailwind, Shadcn.
2.  **Components**: Build the specific layout below.
3.  **State**: Manage `query`, `must_terms`, `weights`, and `selectedResult`.

### Layout: Split View (Fixed Height)
- **Sidebar (35%)**: Scrollable list of results.
- **Main Panel (65%)**: Inspector details.

### Component Specs

#### 1. `ControlBar` (Header)
- **Input**: "Search query..." (large, auto-focus).
- **Advanced**:
  - `Must Terms`: Input for comma-separated tokens (e.g., "logger, error").
  - `Regex`: Input for raw regex string.
  - **Sliders**: `w_semantic` (0.6) vs `w_lexical` (0.4). VISUALIZE this trade-off (e.g., "More Meaning <-> More Exact").

#### 2. `ResultList` (Sidebar)
- **Density**: Compact.
- **Card Design**:
  - **Top**: `source_path` (Mono font, truncated).
  - **Middle**: Badges for scores.
    - `Total` (Zinc-900), `Sem` (Blue-600), `Lex` (Green-600).
    - **New**: If `lex_term_hits > 0`, show a small "Type" icon with count (e.g., 'T: 2').
    - **New**: If `lex_regex_hits > 0`, show a small "Regex" icon with count (e.g., 'R: 1').
  - **Bottom**: The first `why` reason (e.g., "matched term 'foo'").
  - **Visual**: 48px square thumbnail of the page (use `page_uris[0]`).
- **Active State**: Highlight selected card background (e.g., Zinc-100).

#### 3. `InspectorPanel` (Main)
- **Header**: Large filename + Full path + "Why" reasons as tags.
- **Tabs**:
  - **Tab A: "Visual" (Clean View)**:
    - **Content**: Render the full WebP image(s) in a vertical scroll list.
    - **No Overlays**: Just the clean document image.
  - **Tab B: "Text Context" (Interactive)**:
    - **Content**: Render the *full file text* (mock it for now, or use the chunk text if that's all we have).
    - **Interaction**: When a chunk from the list (see below) is clicked, scroll to and highlight that section in the text view (yellow background).
  - **Tab C: "Chunks List"**:
    - **Content**: A list of all chunks for this doc.
    - **Detail**: Show the first 2-3 lines of text for *each* chunk so it's not empty.
    - **Action**: Clicking a chunk row jumps to the "Text Context" tab and highlights it.
  - **Tab D: "Raw JSON"**: `<pre>` dump of the result object.

## 4. Implementation Instructions for Gemini

1.  **Initialize**: `npx create-next-app@latest frontend --typescript --tailwind --eslint`.
2.  **Dependencies**: `npm install lucide-react clsx tailwind-merge`.
3.  **Shadcn**: Install `card`, `tabs`, `slider`, `badge`, `input`, `button`.
4.  **Mock Data**: Create a `data.ts` with the JSON example above. Ensure `chunk.text` has actual content.
5.  **Styling**: **LIGHT MODE ONLY**. Use `zinc-50` to `zinc-900` scale. Clean white backgrounds.

**Deliverable**: A fully functional, "vibe-coded" dashboard. Start by scaffolding the project.

```
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

### A. Search Response (`POST /api/v1/hybrid`)
The core list of results.
```json
[
  {
    "doc_id": "src_utils_logger_py",
    "source_path": "src/utils/logger.py",
    "score": 0.925,               // Combined score (0-1)
    "sem_score": 0.88,            // Semantic vector score
    "lex_score": 1.0,             // Lexical score
    "rrf_score": 0.15,            // Rank fusion score
    "page_uris": [
      "/api/v1/assets/src_utils_logger_py/pages/src_utils_logger_py-p001.webp"
    ],
    "line_start": 12,             // Highlight start (nullable)
    "line_end": 45,               // Highlight end (nullable)
    "why": [
      "matched term: 'Logger' x4",
      "matched regex: 'def log_error' x1",
      "semantic match to query: 'error handling'"
    ],
    "metadata": {
      "language": "python",
      "last_updated": "2025-11-20T14:00:00Z"
    }
  }
]
```

### B. Chunks Response (`GET /api/v1/{doc_id}/chunks`)
For deep inspection.
```json
[
  {
    "chunk_id": "src_utils_logger_py#L1-L50",
    "text": "class Logger:\n    def __init__(self):...",
    "line_start": 1,
    "line_end": 50
  }
]
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
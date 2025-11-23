# Neumann Inspection Dashboard - UI Implementation Plan

## 1. Goal
Build a high-density **Inspection Dashboard** to evaluate the Neumann search pipeline. This tool is for developers to inspect:
1.  **Search Quality**: Why did a document rank #1? (Scores: Semantic vs Lexical vs RRF).
2.  **Data Integrity**: Does the text chunk actually match the visual page? Is the syntax highlighting correct?
3.  **Pipeline Verification**: Are regexes matching the right patterns? Are file paths correct?

## 2. Technical Stack
- **Framework**: Next.js 14+ (App Router).
- **Styling**: Tailwind CSS + Shadcn UI (for rapid, professional density).
- **API**: Connects to local FastAPI backend (`http://localhost:8000`).
- **State**: URL-driven state (search query, selected result ID) for shareability.

## 3. Data Models & API Interaction

### A. Search Endpoint (`POST /api/v1/hybrid`)
The UI will primarily consume the Hybrid Search endpoint.

**Request Payload:**
```json
{
  "query": "vector storage",
  "must_terms": ["chroma"],
  "regexes": ["class \\w+Client"],
  "k": 20,
  "w_semantic": 0.6,
  "w_lexical": 0.4
}
```

**Response Data (The "Result" Object):**
This is the core data structure the UI must render.

```json
[
  {
    "doc_id": "backend_indexer_py",
    "source_path": "backend/indexer.py",
    "score": 0.85,          // Combined weighted score
    "sem_score": 0.72,      // Semantic component
    "lex_score": 0.45,      // Lexical component
    "rrf_score": 0.12,      // Reciprocal Rank Fusion score (tie-breaker)
    "page_uris": [
      "/out/backend_indexer_py/pages/backend_indexer_py-p001.webp"
    ],
    "line_start": 45,       // Line number context (if lexical match)
    "line_end": 180,
    "why": [
      "matched term: 'chroma' x2",
      "matched regex: r'class \\w+Client' x1",
      "semantic match to query: 'vector storage'"
    ],
    "metadata": {
      "language": "python",
      "last_updated": "2025-11-20T10:00:00Z"
    }
  }
]
```

### B. Document Details (`GET /api/v1/{doc_id}/chunks`)
Used for the "Deep Inspection" view to see *all* chunks in a file, not just the match.

**Response Data:**
```json
[
  {
    "chunk_id": "backend_indexer_py#L1-L50",
    "text": "def get_client()...",
    "line_start": 1,
    "line_end": 50
  }
]
```

## 4. UI Components & Layout

The app is a **single-page split view** (Left Sidebar: List, Right Panel: Inspector).

### Component 1: `ControlBar` (Top)
*   **Inputs**:
    *   `QueryInput` (Text): "Search query..."
    *   `MustTermsInput` (Tags Input): Add keywords that *must* exist (e.g., `["Config", "init"]`).
    *   `RegexInput` (Text): Optional regex pattern.
*   **Toggles**:
    *   `Semantic/Lexical Sliders`: Two sliders to adjust `w_semantic` (0.0-1.0) and `w_lexical`. Defaults to 0.6/0.4.
*   **Action**: "Run Search" button (or auto-debounce).

### Component 2: `ResultList` (Left Sidebar - 35% width)
A scrollable list of `ResultCard` items.

*   **`ResultCard` Data Mapping**:
    *   **Title**: `{source_path}` (Truncate beginning if long).
    *   **Badges**:
        *   `Total: {score.toFixed(3)}` (Primary Color)
        *   `Sem: {sem_score.toFixed(2)}` (Blue)
        *   `Lex: {lex_score.toFixed(2)}` (Green)
    *   **Snippet**: `{why[0]}` (e.g., "matched term: 'chroma' x2").
    *   **Visual**: Small thumbnail of `page_uris[0]` (if available).
    *   **Interaction**: Click sets `selectedResult` in state.

### Component 3: `InspectorPanel` (Right Main Area - 65% width)
Displays details for the `selectedResult`.

*   **Header**: Full `source_path`, `doc_id`, and all `why` reasons listed as bullet points.
*   **Tab 1: "Match Context" (Default)**
    *   **Layout**: Split vertical (Text Top, Image Bottom) or Side-by-Side.
    *   **Sub-component: `CodeBlock`**:
        *   Shows the matched text snippet (or full file if we fetch it).
        *   **Highlight**: If `line_start`/`line_end` exist, highlight those lines in yellow.
        *   **Line Numbers**: Display distinct line numbers.
    *   **Sub-component: `VisualPreview`**:
        *   Renders the WebP image from `page_uris`.
        *   **Overlay**: If `line_start` is known, draw a semi-transparent red box over the estimated vertical region of the page (e.g., `top: (line_start / total_lines) * 100%`).
*   **Tab 2: "Raw Data"**
    *   `<pre>` block showing the full JSON response for this result. Useful for checking exact scoring math.
*   **Tab 3: "All Chunks"**
    *   Fetches `/api/v1/{doc_id}/chunks`.
    *   Lists every chunk in the file to see how the file was split. Good for debugging "Why didn't this match?".

## 5. Mockup Data Example for Designer

Use this JSON to visualize the state:

```json
// State: selectedResult
{
  "doc_id": "src_utils_logger_py",
  "source_path": "src/utils/logger.py",
  "score": 0.925,
  "sem_score": 0.88,
  "lex_score": 1.0,
  "page_uris": ["/api/v1/assets/src_utils_logger_py/pages/src_utils_logger_py-p001.webp"],
  "line_start": 12,
  "line_end": 45,
  "why": [
    "matched term: 'Logger' x4",
    "matched regex: 'def log_error' x1",
    "semantic match to query: 'error handling utilities'"
  ],
  "chunk_text": "class Logger:\n    def __init__()...
    def log_error(self, msg)..."
}
```

## 6. Implementation Notes
- **Image Serving**: The backend currently saves to `./out`. The API needs to serve this directory at `/api/v1/assets` so the frontend can load `<img src="/api/v1/assets/..." />`.
- **Line Highlighting**: Since we don't have exact pixel coordinates, we will estimate the highlighting on the image based on `line_start / total_lines_in_file` (requires `total_lines` metadata, might need to estimate or fetch).

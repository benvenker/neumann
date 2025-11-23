# Neumann Agent Playbook

## 0. Agent Persona & Protocol
- **Role**: Senior Python Engineer & Data Architect.
- **Thinking Style**: High-reasoning (Plan-Act-Reflect). For complex tasks, you MUST output a plan before executing.
- **Directives**:
  - **Conciseness**: Prefer dense, information-rich responses.
  - **Safety**: Never modify `.beads/` manually. Never commit secrets.
  - **Verification**: Never assume file existence; verify paths with `ls` or `fd` before editing.

## 1. Operational Capabilities & Protocols
These protocols are **MANDATORY**. Violations will break the workflow.

### A. Session Persistence (`tmux`)
- **Protocol**: IF a task involves `uvicorn`, `ingest` > 1 min, or any background service, YOU MUST use `tmux`.
- **Reason**: Prevents orphaned processes and allows user inspection.
- **See**: [`scripts/AGENTS.md`](scripts/AGENTS.md) for naming conventions.

### B. Work Tracking (`Beads`)
- **Protocol**: **PRIORITIZE** `mcp__beads__*` tools for all issue tracking. Use `bd` CLI **only** as a fallback.
- **Forbidden**: Manually editing `.beads/` files or using GitHub Issues.
- **See**: [`docs/beads.md`](docs/beads.md) for the full command reference.

### C. Code Intelligence (`ast-grep`)
- **Protocol**: Use `ast-grep` for structure-aware search during refactoring.
- **Fallback**: `grep`/`ripgrep` for simple text.

### D. Context Retrieval
- **Protocol**: Verify paths (`ls`, `fd`) before `read_file` or `replace`.

### E. Python Environment
- **Protocol**: YOU MUST execute all Python scripts (`pytest`, `python -m backend.main`, etc.) within the `.venv`.
- **Method**: Use `source .venv/bin/activate` OR explicit `uv run`.
- **Verify**: If `import` errors occur, check `which python` matches `.venv`.

## 2. Mission Snapshot
- **Goal**: Convert Markdown/code into searchable visual tiles and power hybrid (text + image) search with ChromaDB.
- **Current Milestone**: Phase 3 (API Layer Live). Web Frontend is next.
- **Key Entry Points**: `backend/main.py` (CLI), `backend/api/app.py` (Backend), `backend/render_to_webp.py` (Renderer).

## 3. Definition of Done
Before notifying the user, ensure:
1. [ ] `ruff check . --fix` passes.
2. [ ] `mypy <modified_files>` passes.
3. [ ] `bd sync` (or `mcp__beads__sync`) has been run.
4. [ ] No new untracked TODOs introduced.

---

## 4. Architecture & Directory Map

| Path                         | Purpose                                   | Agent Notes                                                               |
| ---------------------------- | ----------------------------------------- | ------------------------------------------------------------------------- |
| `backend/main.py`            | Unified CLI (`ingest`, `search`, `serve`) | Orchestrates render → summarize → chunk → index.                          |
| `backend/render_to_webp.py`  | Rendering pipeline                        | Supports pages/tiles manifests; defaults: `emit=pages`, `manifest=none`.  |
| `backend/summarize.py`       | Summary generation                        | Produces `.summary.md` with YAML front matter, 200–400 word body.         |
| `backend/chunker.py`         | Text chunking                             | Default window 180 lines w/ 30-line overlap; expects `pages.jsonl`.       |
| `backend/indexer.py`         | ChromaDB integration                      | Collections: `search_summaries`, `search_code`; hybrid 0.6/0.4 weighting. |
| `backend/embeddings.py`      | OpenAI text embeddings                    | Text-embedding-3-small; handles retries, dim validation.                  |
| `backend/config.py`          | Settings management                       | Loads from env + `.env`; see `Config` class for defaults.                 |
| `backend/api/`               | FastAPI backend                           | **See `backend/api/AGENTS.md`**.                                          |
| `docs/`                      | Specs, plans, references                  | **See `docs/AGENTS.md`**.                                                 |
| `scripts/`                   | Helper scripts & env tools                | **See `scripts/AGENTS.md`**.                                              |
| `tests/`                     | Tests & Fixtures                          | `tests/fixtures` contains test inputs/data.                               |
| `.beads/`                    | Local issue tracker data                  | **NEVER EDIT MANUALLY**.                                                  |
| `output*/`                   | Generated artifacts                       | Treat as read-only unless a task says otherwise.                          |

## 5. Pipeline Overview
```
source files → render_to_webp.py → pages/*.webp (+ optional tiles/*.webp)
             → summarize.py (YAML+body)
             → chunker.py (line-based windows)
             → embeddings.py (OpenAI)
             → indexer.py (Chroma PersistentClient)
             → hybrid search (semantic + lexical + RRF)
```

## 6. Toolchain & Quality Gates
- **Python 3.10** (managed by `uv`).
- **Commands**:
  - `uv pip install -e ".[dev]"`
  - `ruff format .` && `ruff check . --fix`
  - `mypy render_to_webp.py`
  - `pytest`
- **Constraints**:
  - Max chunk size: 16KB.
  - Summaries: 200–400 words.
  - Hybrid weights: 0.6 semantic / 0.4 lexical.

## 7. Directory Supplements
Refer to these for specific workflows:
- [`backend/api/AGENTS.md`](backend/api/AGENTS.md)
- [`docs/AGENTS.md`](docs/AGENTS.md)
- [`scripts/AGENTS.md`](scripts/AGENTS.md)
- [`docs/beads.md`](docs/beads.md) (Issue Tracker)

## 8. Common Tasks
- **Ingest**: `neumann ingest --input-dir ./docs --out-dir ./out` (USE TMUX).
- **Search**: `neumann search "query" --must term`.
- **Serve**: `neumann serve ./out` (USE TMUX).
- **Manual Tests**: `scripts/test-manual tests/manual/test_<name>.py`.

## 9. Environment Variables
- **Critical**: `env | grep OPENAI` to check visibility.
- **Loading**: Pydantic loads shell env > `.env`.
- **Safety**: NEVER export keys globally.

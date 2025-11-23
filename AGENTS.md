# Neumann Agent Playbook

Welcome! This is the operational handbook for autonomous or semi-autonomous agents working inside the Neumann repository. It refreshes and restructures the information from `CLAUDE.md` so you can move quickly without missing project conventions.

---

## CLI & Utility Tools

These CLI tools are available in the workspace shell:

- **ast-grep** — structure-aware code search; perfect for locating syntax patterns when plain text search is too noisy.
- **gh** — GitHub CLI for issues, pulls, and repo metadata; use it alongside RepoPrompt for quick history or README access.
- **bd** — We track work in Beads instead of Markdown. Run `bd quickstart` to see how
- **tmux** — run long-lived commands like `pnpm test`, `pnpm test:watch`, or extra dev servers in separate panes; keep shared output visible for yourself and the user, and pair with Chrome DevTools MCP for live debugging. Default to launching any process that depends on external services (APIs, MCP servers, watchers) inside a tmux session so it persists and remains observable.

Combine utilities as needed. For example, ast-grep can highlight call sites before you open them via RepoPrompt, and gh can fetch upstream README files when bd or Context7 lacks coverage.



## 1. Mission Snapshot
- **Goal**: Convert Markdown/code into searchable visual tiles and power hybrid (text + image) search with ChromaDB.
- **Current Milestone (November 2, 2025)**: Phase 2 in progress – embeddings and hybrid search are live; API/UI layers are upcoming.
- **Primary Entry Points**: `main.py` (CLI orchestrator), `render_to_webp.py` (renderer), `summarize.py`, `indexer.py`, `chunker.py`.
- **Must Do Before Work**:
  1. Check outstanding tasks with `bd ready --json` (CLI) or MCP `ready()` function.
  2. Claim or create an issue (epic/task/bug) before editing.
  3. Run long-lived processes inside tmux (see §6).

---

## 2. Architecture & Directory Map

| Path                         | Purpose                                   | Agent Notes                                                               |
| ---------------------------- | ----------------------------------------- | ------------------------------------------------------------------------- |
| `main.py`                    | Unified CLI (`ingest`, `search`, `serve`) | Orchestrates render → summarize → chunk → index.                          |
| `render_to_webp.py`          | Rendering pipeline                        | Supports pages/tiles manifests; defaults: `emit=pages`, `manifest=none`.  |
| `summarize.py` & `models.py` | Summary generation & schemas              | Produces `.summary.md` with YAML front matter, 200–400 word body.         |
| `chunker.py`                 | Text chunking                             | Default window 180 lines w/ 30-line overlap; expects `pages.jsonl`.       |
| `indexer.py`                 | ChromaDB integration                      | Collections: `search_summaries`, `search_code`; hybrid 0.6/0.4 weighting. |
| `embeddings.py`              | OpenAI text embeddings                    | Text-embedding-3-small; handles retries, dim validation.                  |
| `config.py`                  | Settings management                       | Loads from env + `.env`; see `Config` class for defaults.                 |
| `docs/`                      | Specs, plans, references                  | See `docs/AGENTS.md` for authoring rules.                                 |
| `tests/`                     | Automated & manual tests                  | See `tests/AGENTS.md` before adding or updating tests.                    |
| `.beads/`                    | Local issue tracker data                  | Never edit manually; use Beads CLI commands.                              |
| `output*/`, `test_*`         | Generated artifacts/fixtures              | Treat as read-only unless a task says otherwise.                          |

Future roadmap: expect migration into `src/neumann/` package structure (documented in CLAUDE legacy). Update both `AGENTS.md` and `CLAUDE.md` when architecture shifts.

---

## 3. Pipeline Overview
```
source files → render_to_webp.py → pages/*.webp (+ optional tiles/*.webp)
             → summarize.py (YAML+body)
             → chunker.py (line-based windows)
             → embeddings.py (OpenAI)
             → indexer.py (Chroma PersistentClient)
             → hybrid search (semantic + lexical + RRF)
```

Key behaviors to remember:
- `pages.jsonl` is always emitted unless `--emit tiles` explicitly. Downstream steps require it.
- Tile manifests write only when tiling + `--manifest` ≠ `none`. Formats: JSONL, JSON, TSV.
- Document IDs come from `ids.make_doc_id()` and are shared across render, summaries, and index.

---

## 4. Toolchain & Quality Gates
- **Python 3.10** (see `.python-version`); dependencies managed with **uv**.
 - Core libs: WeasyPrint 66.0, PyMuPDF 1.24.8, Pillow 10.4.0, Pygments 2.18.0, Markdown 3.6, ChromaDB 1.3.0, OpenAI 2.6.1, Pydantic 2.12.3, pydantic-settings 2.11.0.
- Dev tooling: `ruff` (formatter & linter), `mypy`, `pytest`, `ast-grep`, `tmux`.
- Standard commands:
  - `uv pip install -e ".[dev]"` (first setup).
  - `ruff format .` then `ruff check . --fix`.
  - `mypy render_to_webp.py` (type-critical modules).
  - `pytest` (full suite) or targeted modules.
- When modifying dependencies or architecture, mirror updates in `README.md` and `CLAUDE.md`.

---

## 5. Issue & Epic Handling with Beads
**Beads is mandatory.** GitHub Issues or ad-hoc trackers are forbidden.

**IMPORTANT:** The Beads MCP server works for Cursor agent but **does NOT work for Codex CLI**. Use the appropriate method for your agent:
- **Cursor agent (MCP)**: Use MCP tools (see "Using MCP Tools" below)
- **Codex CLI**: Use CLI commands directly via `bd` in the shell (see "Using CLI Commands" below)

### Initialization
If the project hasn't been initialized yet (you'll see "database not found"), run:
```bash
bd init --quiet  # Non-interactive setup for agents (auto-installs git hooks, no prompts)
```

### Using MCP Tools (Cursor Agent)

The Beads MCP server provides native integration for Cursor agent. All tools use the prefix `mcp__beads__*` or `mcp__plugin_beads_beads__*`.

**Essential MCP functions:**
- `set_context(workspace_root)` - Set workspace root (call this first!)
- `ready(limit, priority, assignee)` - Find tasks with no blockers
- `create(title, issue_type, priority, description, labels)` - Create new issues
- `update(issue_id, status, priority, assignee)` - Update issue properties
- `close(issue_id, reason)` - Mark issues as completed
- `show(issue_id)` - Show detailed issue information
- `list(status, priority, issue_type, assignee)` - List issues with filters
- `dep(issue_id, depends_on_id, dep_type)` - Add dependencies between issues
- `blocked()` - Show blocked issues and their dependencies
- `stats()` - Get project statistics

**Example MCP workflow:**
1. Set context: `set_context(workspace_root="/Users/ben/code/neumann")`
2. Find ready work: `ready(limit=10)`
3. Claim task: `update(issue_id="nm-a1b2", status="in_progress")`
4. Complete: `close(issue_id="nm-a1b2", reason="Implemented and tested")`

### Using CLI Commands (Codex CLI)

When MCP is not available (e.g., Codex CLI), use `bd` CLI commands directly:

**Finding ready work:**
```bash
bd ready --json                    # List unblocked issues (JSON for programmatic use)
bd ready --limit 20                # Limit results
bd ready --priority 1              # Filter by priority
```

**Creating issues:**
```bash
bd create "Issue title" -t bug -p 1 --json
bd create "Issue title" -t feature -p 1 -d "Description" --json
bd create "Issue title" -t epic -p 1 -l label1,label2 --json  # With labels
```

**Issue types:** `bug`, `feature`, `task`, `epic`, `chore`  
**Priorities:** `0` (critical) → `4` (backlog). Default: `2` (medium)

**Updating issues:**
```bash
bd update <id> --status in_progress --json
bd update <id> --priority 1 --json
bd update <id> --assignee ProductThor --json
```

**Closing issues:**
```bash
bd close <id> --reason "Completed implementation" --json
```

**Managing dependencies:**
```bash
bd dep add <dependent-id> <blocker-id>                    # Hard blocker (default)
bd dep add <dependent-id> <related-id> --type related    # Soft relationship
bd dep add <child-id> <parent-id> --type parent-child    # Epic/subtask
bd dep add <discovered-id> <parent-id> --type discovered-from  # Found during work
bd dep tree <id>                                          # Visualize dependencies
```

**Dependency types:**
- `blocks` (default) - Hard blocker; affects ready work queue
- `related` - Soft relationship; informational only
- `parent-child` - Epic/subtask hierarchy
- `discovered-from` - Track issues found during work

**Labels (flexible categorization):**
```bash
bd label add <id> backend,urgent --json
bd label remove <id> urgent --json
bd label list <id> --json
bd list --label backend,auth                           # AND filtering (must have all)
bd list --label-any frontend,backend                   # OR filtering (any match)
```

**Critical workflow: Always sync at end of agent sessions:**

For **CLI users** (Codex CLI):
```bash
bd sync  # Forces immediate export, commit, pull, import, push
```

For **MCP users** (Cursor agent):
```bash
# Use the sync MCP function if available, or fall back to CLI
bd sync
```

This ensures all changes are committed and pushed immediately (bypasses 30-second debounce).

### Issue IDs
- **Hash-based** (e.g., `nm-a1b2`, `nm-f14c`) - Not sequential! Prevents collisions when multiple agents/branches work concurrently.
- Epic children use dotted notation: `nm-a3f8e9.1`, `nm-a3f8e9.2`

### Branch Switching & Troubleshooting

**Common Issue: "Deleted" files in git status**
If you see `deleted: .beads/beads.base.jsonl` or similar in `git status`:
1. These are internal temporary files used for 3-way merging. They should **never** be committed.
2. If they were previously committed, remove them: `git rm .beads/beads.base.* .beads/beads.left.*`
3. Ensure they are in `.gitignore`.

**Switching Branches**
When switching branches, `issues.jsonl` may change. Beads will automatically detect this and import the new state.
1. **Before switching**: Run `bd sync` to save your work to `issues.jsonl`.
2. **After switching**: Run `bd ready` or `bd list` to trigger an auto-import of the new branch's state.
3. **Conflict**: If you get a merge conflict in `issues.jsonl`, treat it like any other text file conflict. Resolve it, then run `bd import issues.jsonl` to update the local database.

### Workflow Reminders
- Always attach commits to an issue ID (`nm-###`).
- Use epics for multi-stage initiatives and link dependent issues.
- Do not modify `.beads/` manually; rely on CLI commands above.
- **Always run `bd sync` at the end of agent sessions** to flush changes.
- Check `bd ready` before starting new work to find unblocked tasks.

### Getting Help
```bash
bd list --json                    # List all issues
bd show <id> --json               # View issue details
bd stats                          # Project statistics
bd blocked                        # See blocked issues
```

For comprehensive Beads documentation:
- **Detailed reference**: [`docs/beads.md`](docs/beads.md) - Complete CLI command reference and workflow patterns for Neumann project
- **Upstream docs**: [Beads README](https://github.com/steveyegge/beads/blob/main/README.md) and [Beads AGENTS.md](https://github.com/steveyegge/beads/blob/main/AGENTS.md)


---

## 6. tmux Usage Policy
- Use tmux for servers, long ingestion runs, or background jobs.
- Session naming: `neumann-<purpose>` (e.g., `neumann-api`, `neumann-render`).
- Always inform the human user when starting a session: include name, command, attach/detach instructions.
- Check existing sessions with `tmux ls`; one purpose per session.
- Detach with `Ctrl+b, d`; terminate stale sessions via `tmux kill-session -t <name>`.

Example:
```bash
tmux new -s neumann-api
uvicorn main:app --reload --port 8000
```
Inform the user: running FastAPI server, attach via `tmux attach -t neumann-api`.

---

## 7. Coding Standards & Testing
- Follow `ruff` formatting (120 character width) and add type hints for new functions.
- Limit chunk sizes to keep under 16KB for Chroma Cloud compatibility.
- When editing renderer defaults, ensure tests like `tests/test_defaults_and_pages_only.py` still pass.
- Summaries must stay within 200–400 words; see `tests/test_summarize.py`.
- Hybrid search weights (0.6 semantic / 0.4 lexical) are codified in tests—update tests if you change them.
- Generated assets in `output/` are fixtures; regenerate intentionally and document in commits.

---

## 8. Directory Supplements
These directories have additional guidance tailored to their workflows:

| Directory | Guide                                                                                                                                                            |
| --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `docs/`   | `docs/AGENTS.md` – documentation authoring, spec updates, and external references.<br>`docs/beads.md` – comprehensive Beads CLI reference and workflow patterns. |
| `tests/`  | `tests/AGENTS.md` – automated vs. manual testing conventions, fixture etiquette.                                                                                 |

If you introduce new process-heavy folders (e.g., `services/`, `ui/`), add a sibling `AGENTS.md` and link it here.

---

## 9. Common Tasks (Agent Checklist)
- **Add support for a new file type**: update `SUPPORTED_MD`/`SUPPORTED_CODE` in `render_to_webp.py`; ensure Pygments handles lexer; adjust tests.
- **Change tile layout**: run `render_to_webp.py` with `--tile-size` / `--tile-overlap`; update manifests and document assumptions.
- **Run full ingestion**: `neumann ingest --input-dir ./docs --out-dir ./out`.
- **Search workflow**: `neumann search "query" --must term --path-like file.py`. `query` optional for lexical-only if no OpenAI key.
- **Serve output**: `neumann serve ./out --asset-root out`.
- **Run manual tests**: Always use `scripts/test-manual tests/manual/test_<name>.py` to ensure correct environment variable handling (see §10 below).

---

## 10. Environment Variable Precedence & Configuration Issues

### ⚠️ Critical: Pydantic Loads Environment Variables BEFORE .env Files

**Problem:** If you have `export OPENAI_API_KEY=old-key` in `~/.zshrc` or a global `~/.env`, it will **override** the project's `.env` file. This causes:
- New API keys in project `.env` to be ignored
- "Quota exceeded" errors even after updating `.env`
- Different keys used by different processes
- Confusing debugging ("why isn't my config working?")

**Root cause:** pydantic-settings precedence order:
1. Environment variables (highest priority)
2. `.env` file (lower priority)
3. Default values (lowest priority)

### Solution: Never Export API Keys Globally

**DO NOT do this in ~/.zshrc:**
```bash
# ✗ BAD - Overrides project .env
export OPENAI_API_KEY=sk-proj-...
```

**DO use project-local .env:**
```bash
# ✓ GOOD - Each project has its own key
# In /Users/ben/code/neumann/.env
OPENAI_API_KEY=sk-proj-...
```

### Detecting The Issue

**Check for global overrides:**
```bash
env | grep OPENAI_API_KEY
# If you see output, you have a global override!
```

**Check if ~/.env exists:**
```bash
cat ~/.env 2>/dev/null | grep OPENAI
```

**Fix immediately:**
```bash
# Remove from global environment
unset OPENAI_API_KEY

# Remove from ~/.zshrc (if present)
# Edit ~/.zshrc and delete any export OPENAI_API_KEY= lines

# Remove from ~/.env (if it exists)
# Edit ~/.env and remove API keys

# Restart all processes
tmux kill-server  # Nuclear option, kills all sessions
```

### Best Practice: Use On-Demand Key Loading

For tools that need API keys, use the function wrapper pattern (like `llms-txt()` in `~/.zshrc`):

```bash
# Fetch API key only when command runs, from 1Password
my-tool() {
  OPENAI_API_KEY="$(op item get 'My OpenAI Key' --fields notesPlain)" \
  command my-tool "$@"
}
```

Benefits:
- Keys never persisted in environment
- No accidental exposure
- Each command can use different keys
- Project `.env` files work correctly

### Running Manual Tests with Correct Environment

**direnv should handle this automatically** if properly configured:

1. **One-time setup:** Run `direnv allow` in the project directory to whitelist `.envrc`
2. **Automatic loading:** direnv automatically loads `.envrc` when you `cd` into the directory
3. **The `.envrc` file** explicitly exports `OPENAI_API_KEY` from `.env`, overriding global exports

```bash
# If direnv is working, just run tests normally:
python3 tests/manual/test_summarization.py
pytest tests/manual/test_*.py

# If direnv isn't active, use the wrapper script:
scripts/test-manual tests/manual/test_summarization.py
```

**Checking if direnv is active:**
```bash
cd /Users/ben/code/neumann
direnv status  # Should show ".envrc loaded"
env | grep OPENAI_API_KEY  # Should show key from .env (sk-proj-21jbPpw...)
```

**Fallback wrapper script:** If direnv isn't configured or working in your shell, use `scripts/test-manual` which manually ensures the correct environment. This is mainly for CI environments or shells without direnv support.

### Restarting Processes After Config Changes

When you update `.env`, processes must be restarted:

**API server:**
```bash
tmux kill-session -t neumann-api
cd /Users/ben/code/neumann
tmux new-session -d -s neumann-api 'cd /Users/ben/code/neumann && source .venv/bin/activate && uvicorn api.app:create_app --factory --reload --port 8001'
```

**Important:** tmux sessions inherit the environment from when they're created. If you had `OPENAI_API_KEY` set when you created the session, it persists even after you `unset` it in another terminal. Always kill and recreate tmux sessions after environment changes.

---

## 11. Additional Notes
- System dependencies (macOS): `brew install cairo pango gdk-pixbuf libffi`. Ubuntu equivalents listed in `docs/AGENTS.md`.
- `.envrc` enables direnv; run `direnv allow` after cloning.
- Keep `CLAUDE.md` up to date for architectural history; treat this file as the canonical agent guide going forward.
- For upstream documentation, use Context7 MCP IDs:
  - WeasyPrint `/FedericoCeratto/weasyprint`
  - Chroma `/chroma-core/chroma`
  - FastAPI `/tiangolo/fastapi`

Questions? Start with `CLAUDE.md` (legacy deep dive), then raise an issue via Beads if something is unclear.

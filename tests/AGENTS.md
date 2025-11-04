# Testing Guide for Agents

Use this brief to navigate the `tests/` tree, choose the right testing strategy, and preserve conventions when adding coverage.

## 1. Structure
- `test_*.py`: Pytest suites covering chunking, rendering defaults, hybrid search, metadata normalization, etc. Tests are organized by domain; follow existing naming when adding new modules.
- `fixtures/`: Shared sample data. Prefer reusing fixtures over duplicating inline constants.
- `manual/`: Scripts and notes for exploratory or long-running tests. Treat as documentation—do not rely on them for CI coverage.

## 2. General Rules
- Always run `pytest` (or the targeted subset) before closing an issue.
- Tests should pass in isolation; avoid hidden dependencies on environment variables except when explicitly guarded (e.g., OpenAI key checks).
- Keep chunk sizes below 16KB to satisfy Chroma constraints—tests enforce this via `test_chunker.py`.
- When adjusting defaults (e.g., renderer emit options), update `test_defaults_and_pages_only.py` and any relevant fixtures.
- Summaries must stay within 200–400 words; enforced by `test_summarize.py`.

## 3. Adding New Tests
1. Place canonical unit tests alongside similar suites (e.g., search logic → `test_hybrid_search.py`).
2. Use descriptive test function names (`test_<module>_<behavior>`).
3. Add fixtures under `fixtures/` if multiple tests need the same data.
4. For expensive integration tests, mark them with `@pytest.mark.slow` and document invocation in `manual/`.

## 4. Manual & Exploratory Testing

### Running Manual Tests

**direnv handles this automatically** - the `.envrc` file explicitly exports `OPENAI_API_KEY` from `.env`, overriding global exports.

**One-time setup:**
```bash
cd /Users/ben/code/neumann
direnv allow  # Whitelist the .envrc file
```

**Then just run tests normally:**
```bash
python3 tests/manual/test_summarization.py
python3 tests/manual/test_api_quick.py
pytest tests/manual/test_*.py
```

**Verify direnv is working:**
```bash
cd /Users/ben/code/neumann
direnv status  # Should show ".envrc loaded"
env | grep OPENAI_API_KEY  # Should match your .env file
```

**Fallback (if direnv not available):**
```bash
# Use the wrapper script for CI or shells without direnv
scripts/test-manual tests/manual/test_summarization.py
```

**Why this matters:** Manual tests import `config` which uses pydantic-settings. If `OPENAI_API_KEY` is exported globally (e.g., from `~/.zprofile`), direnv's explicit export in `.envrc` ensures the project `.env` value takes precedence.

### Documentation & Guidelines

- Document step-by-step instructions and expected outputs in `tests/manual/`.
- When manual tests uncover gaps, file a Beads issue and backfill automated coverage whenever feasible.
- For long runs, invoke `pytest --progress` (or set `PYTEST_PROGRESS=1`) to stream test start/end timestamps and durations.
- Manual suites under `tests/manual/` are excluded from default collection; run them explicitly with `pytest --manual tests/manual/...` or by calling the scripts noted inside each file.

## 5. Future Work
As we introduce new services (API/UI layers), create subdirectories such as `tests/api/` or `tests/ui/` with their own `AGENTS.md` explaining environment setup and mocks. Update the table in the root `AGENTS.md` accordingly.

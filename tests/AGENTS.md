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
- Document step-by-step instructions and expected outputs in `tests/manual/`.
- When manual tests uncover gaps, file a Beads issue and backfill automated coverage whenever feasible.

## 5. Future Work
As we introduce new services (API/UI layers), create subdirectories such as `tests/api/` or `tests/ui/` with their own `AGENTS.md` explaining environment setup and mocks. Update the table in the root `AGENTS.md` accordingly.

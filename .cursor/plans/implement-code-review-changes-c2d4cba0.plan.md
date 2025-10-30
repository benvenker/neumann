<!-- c2d4cba0-9ae3-4061-9b7f-4415f2927eac 00cb2538-1a98-48bb-8ce1-97427c30d002 -->
# Implement Code Review Changes

Based on GPT-5 Pro code review, implement changes to align with pages-first philosophy and fix quality issues.

## 1. Change Defaults (Critical)

**File: `render_to_webp.py`**

- Update `RenderConfig.emit` default: `"both"` → `"pages"` (line 73)
- Update `RenderConfig.manifest` default: `"jsonl"` → `"none"` (line 74)
- Update CLI `--emit` default: `"both"` → `"pages"` (line 447)
- Update CLI `--manifest` default: `"jsonl"` → `"none"` (line 448)
- Update header docstring (lines 3-11) to reflect pages-only default

## 2. Fix Page Path Metadata

**File: `render_to_webp.py`**

- In `render_file()`, set `page_path` to `None` when `emit="tiles"` and pages aren't emitted (line 372)
- Logic: `"page_path": str(wp) if include_page_images else None`

## 3. Tighten Line-Number Gutter Styling

**File: `render_to_webp.py`**

- Update CSS for table-style line numbers (lines 190-198):
- Reduce `td.linenos` width: `2.6em` → `2.0em`
- Reduce padding: `0 6px 0 4px` → `0 4px 0 2px`
- Remove `border-right: 1px solid #eee`
- Update `td.code` padding: `8px` → `6px`
- Update color: `#9a9a9a` → `#a7a7a7`

## 4. Use Context Managers for Resource Safety

**File: `render_to_webp.py`**

- Update `pdf_to_webp_pages()` (lines 246-263):
- Replace `doc = fitz.open(...)` and `doc.close()` with `with fitz.open(...) as doc:`
- Update `tile_grid()` (lines 266-281):
- Wrap `Image.open(webp_path)` with context manager: `with Image.open(...) as base:`
- Update `tile_bands()` (lines 284-303):
- Wrap `Image.open(webp_path)` with context manager: `with Image.open(...) as base:`

## 5. Fix Grid Tiler Edge Coverage

**File: `render_to_webp.py`**

- Replace `tile_grid()` function (lines 266-281) with improved version:
- Generate x/y coordinate lists ensuring right/bottom edges are covered
- Handle edge case where last tile would extend beyond image bounds
- Clamp crops with `min()` to prevent out-of-bounds access

## 6. Update Documentation

**File: `README.md`**

- Update description to emphasize pages-first, tiles optional (line 3)
- Update "Basic Example" section to show pages-only default (lines 54-60)
- Add separate section for tiles (lines 62-78)
- Update `--emit` and `--manifest` defaults in options list (lines 95-96)
- Update output structure section to show pages-only default (lines 99-114)
- Add note about line-number styling (optional)

**File: `docs/IMPLEMENTATION_PLAN.md`**

- Update "Default Behavior" section (lines 9-12): pages-only, manifest=none
- Update CLI examples to reflect new defaults (lines 63-77, 99-100)
- Update "Design Decisions" section to explain pages-first rationale (lines 179-183)

## 7. Fix Test Assertion

**File: `tests/test_code_to_html.py`**

- Line 41: Replace brittle assertion:
- From: `assert "<article class='code-article'>" in html`
- To: `assert "code-article" in html` (more robust, doesn't depend on quote style)

## 8. Add New Tests

**File: `tests/test_defaults_and_pages_only.py`** (new file)

- `test_defaults_pages_only()`: Verify RenderConfig defaults
- `test_render_pages_only_no_tiles()`: Integration test that pages are produced and tiles aren't with defaults (mark as `@pytest.mark.integration`)

## 9. Optional: Python Version Alignment

**File: `pyproject.toml`**

- If choosing Option A (wider compatibility):
- Line 9: `requires-python = ">=3.10"` (change from `>=3.13`)
- Line 36: `target-version = "py310"` (change from `py313`)
- Line 59: `python_version = "3.10"` (change from `"3.13"`)
- If choosing Option B (keep 3.13): No changes needed

## Implementation Order

1. Change defaults (RenderConfig + CLI + docstring)
2. Fix resource leaks (context managers)
3. Fix grid tiler edge coverage
4. Fix page_path metadata logic
5. Tighten line-number CSS
6. Update tests (fix assertion + add new tests)
7. Update documentation (README + IMPLEMENTATION_PLAN)
8. Adjust Python version to 3.10

## Notes

- Keep inline line numbers as default (no change needed)
- Tiles remain fully functional when opted-in via `--emit tiles` or `--emit both`
- All changes are backward compatible (only defaults change)
- Grid tiler fix ensures no content is missed at image edges

### To-dos

- [ ] Change RenderConfig defaults: emit='pages', manifest='none', and update CLI arg defaults and header docstring
- [ ] Replace fitz.open and Image.open with context managers in pdf_to_webp_pages, tile_grid, and tile_bands
- [ ] Fix tile_grid function to guarantee right/bottom edge coverage with proper coordinate generation
- [ ] Set page_path to None in tile manifest when emit='tiles' and pages aren't included
- [ ] Tighten line-number gutter CSS: reduce width, padding, remove border-right for table mode
- [ ] Fix brittle test assertion in test_code_to_html.py and add new test_defaults_and_pages_only.py with defaults and integration tests
- [ ] Update README.md and docs/IMPLEMENTATION_PLAN.md to reflect pages-only default and optional tiling
- [ ] Optional: Decide on Python 3.10 vs 3.13 requirement and update pyproject.toml if lowering to 3.10
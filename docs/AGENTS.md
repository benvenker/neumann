# Documentation Guide for Agents

⚠️ **Protocol Override**: Follow the [Operational Protocols in root AGENTS.md](../AGENTS.md) (tmux, Beads MCP) for all tasks in this directory.

This file supplements the root `AGENTS.md` with instructions specific to the `docs/` tree. Use it whenever you add or revise specifications, plans, or supporting references.

## 1. Directory Overview
- `acceptance_results.md`: Historical metrics and outcomes from the end-to-end pipeline. Update when acceptance tests or benchmarks change materially.
- `IMPLEMENTATION_PLAN.md`: Living design plan for the rendering pipeline. Keep in sync with major renderer changes (CLI flags, defaults, architecture).
- `main-spec.md`: Narrative product spec. Update when the user-facing contract changes (API surface, search behaviors).
- `chroma/`: Vendored ChromaDB docs and examples. Treat as upstream reference—do not edit unless explicitly told to sync with a new upstream revision.

## 2. Authoring Standards
- Use Markdown with 120-character soft wrap.
- Ensure headings use sentence case and follow existing hierarchy.
- Provide forward/back references when splitting content across files.
- Call out code paths with backticks (`render_to_webp.py`) and keep code samples minimal.
- Document dates explicitly (e.g., “Updated November 2, 2025”) when logging benchmark runs.

## 3. Syncing with Code Changes
When modifying core pipelines:
1. Update relevant section in `IMPLEMENTATION_PLAN.md`.
2. Reflect user-facing changes in `main-spec.md`.
3. If benchmarks shift, rerun acceptance tests and record summaries in `acceptance_results.md`.
4. Mention doc updates in your Beads issue closure note.

## 4. External References
- Prefer citing official docs via Context7 MCP. Examples:
  - ChromaDB: `/chroma-core/chroma`
  - OpenAI embeddings: `/openai/openai`
- When copying external snippets, include the source URL and date accessed.

## 5. Future Expansion
If we add specialized documentation subsections (e.g., `docs/api/`, `docs/ui/`), create nested `AGENTS.md` files within those subfolders and link them here with a short description.

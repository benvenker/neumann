# Handoff Notes – Beads Sync Guard Loop

## Problem Recap
- After recreating the Beads database via MCP, running `bd sync` always fails with
  `Pre-export validation failed: refusing to export: JSONL is newer than database.`
- The guard compares the hash/mtime of `.beads/issues.jsonl` / `.beads/beads.left.jsonl`
  against the `last_import_hash` recorded inside `.beads/beads.db`.
- Because we flushed (`bd sync --flush-only`) but never imported those new files,
  the DB metadata points to an older hash. Every export attempt sees the mismatch
  and refuses to proceed, even though the data was created locally.

## Options to Move Forward
### Option 1 – Manual Git Workflow (no `bd sync`)
1. Delete `.beads/` entirely.
2. `bd init --prefix nm`.
3. Recreate (or reimport via MCP) the issues.
4. Run `bd sync --flush-only` once to generate fresh `.beads/*.jsonl`.
5. Commit the `.beads/` directory via git and push manually.

As long as we *do not* run `bd import` afterwards, the DB has no `last_import_hash`
recorded, so `bd sync` has no stale JSONL to complain about. Workflows rely on
manual git pushes instead of `bd sync` until Beads is healthier.

### Option 2 – Patch Metadata to Match Current JSONL
1. Run `bd sync --flush-only` to generate the current JSONL (issues + beads.left).
2. Compute the SHA hash of the flushed JSONL (Beads stores this internally as part
   of its export hash calculation).
3. Update `.beads/beads.db` directly:
   ```sql
   UPDATE metadata SET value = '<current_export_hash>' WHERE key = 'last_import_hash';
   UPDATE metadata SET value = '<current_timestamp>' WHERE key = 'last_import_time';
   ```
4. Retry `bd sync` – it now thinks the JSONL was already imported and will proceed.

This is hacky but clears the guard without nuking the DB. Be sure to back up
`beads.db` before editing.

## Recommendation
Pick one approach before the next session. Option 1 is simpler (no DB surgery) but
requires manual git management for Beads artifacts. Option 2 keeps `bd sync`
usable but needs careful manual updates.

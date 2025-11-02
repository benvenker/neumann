# Beads Issue Tracker - Comprehensive Reference

This document provides a detailed reference for using Beads (`bd`) in the Neumann project. **Choose the appropriate method based on your agent:**
- **Cursor agent**: Use MCP tools (see [Using MCP Tools](#using-mcp-tools-cursor-agent))
- **Codex CLI**: Use CLI commands directly (see [Using CLI Commands](#using-cli-commands-codex-cli))

## Table of Contents

- [Quick Start](#quick-start)
- [Initialization](#initialization)
- [Using MCP Tools (Cursor Agent)](#using-mcp-tools-cursor-agent)
- [Using CLI Commands (Codex CLI)](#using-cli-commands-codex-cli)
- [Issue Types and Priorities](#issue-types-and-priorities)
- [Dependency Management](#dependency-management)
- [Labels](#labels)
- [Agent Workflow](#agent-workflow)
- [Git Integration](#git-integration)
- [Advanced Usage](#advanced-usage)

## Quick Start

**CLI approach (Codex CLI):**
```bash
# Check for ready work
bd ready --json

# Create an issue
bd create "Fix bug in renderer" -t bug -p 1 --json

# Start working
bd update nm-a1b2 --status in_progress --json

# Complete work
bd close nm-a1b2 --reason "Fixed and tested" --json

# Always sync at end of session
bd sync
```

**MCP approach (Cursor agent):**
1. Set context: `set_context(workspace_root="/Users/ben/code/neumann")`
2. Find ready work: `ready(limit=10)`
3. Create issue: `create(title="Fix bug in renderer", issue_type="bug", priority=1)`
4. Start working: `update(issue_id="nm-a1b2", status="in_progress")`
5. Complete: `close(issue_id="nm-a1b2", reason="Fixed and tested")`

## Initialization

**First-time setup (agents should use `--quiet` flag):**

```bash
bd init --quiet  # Non-interactive, auto-installs git hooks, no prompts
```

**Why `--quiet`?** Regular `bd init` has interactive prompts that confuse agents. The `--quiet` flag makes it fully non-interactive:
- Automatically installs git hooks
- No prompts for user input
- Safe for agent-driven repo setup

**If database already exists:** Just use `bd` commands normally - no initialization needed.

## Using MCP Tools (Cursor Agent)

The Beads MCP server provides native integration for Cursor agent. All tools use the prefix `mcp__beads__*` or `mcp__plugin_beads_beads__*`.

### Essential MCP Functions

**Context Management:**
- `set_context(workspace_root)` - Set workspace root (call this first!)
- `where_am_i()` - Show current workspace context and database path

**Issue Discovery:**
- `ready(limit, priority, assignee)` - Find tasks with no blockers
- `list(status, priority, issue_type, assignee, labels)` - List issues with filters
- `show(issue_id)` - Show detailed issue information
- `blocked()` - Show blocked issues and their dependencies
- `stats()` - Get project statistics

**Issue Management:**
- `create(title, issue_type, priority, description, labels, deps)` - Create new issues
- `update(issue_id, status, priority, assignee, title, description)` - Update issue properties
- `close(issue_id, reason)` - Mark issues as completed
- `reopen(issue_id, reason)` - Reopen closed issues

**Dependencies:**
- `dep(issue_id, depends_on_id, dep_type)` - Add dependencies between issues
- `dep_remove(issue_id, depends_on_id)` - Remove dependencies

**Labels:**
- `label_add(issue_id, labels)` - Add labels to issues
- `label_remove(issue_id, labels)` - Remove labels from issues
- `label_list(issue_id)` - List labels for an issue
- `label_list_all()` - List all labels with usage counts

**Sync:**
- `sync()` - Force immediate export, commit, pull, import, push (if available)
- If sync function not available, fall back to CLI: `bd sync`

### Example MCP Workflow

```python
# 1. Set context (one-time per session)
set_context(workspace_root="/Users/ben/code/neumann")

# 2. Find ready work
ready_tasks = ready(limit=10, priority=1)

# 3. Claim a task
update(issue_id="nm-a1b2", status="in_progress", assignee="ProductThor")

# 4. Create related issue if discovered
new_issue = create(
    title="Found bug in auth.go",
    issue_type="bug",
    priority=1,
    labels=["auto-generated", "technical-debt"],
    deps=[{"type": "discovered-from", "depends_on_id": "nm-a1b2"}]
)

# 5. Complete work
close(issue_id="nm-a1b2", reason="Implemented and tested")

# 6. Sync at end of session
sync()  # Or use CLI: bd sync
```

### MCP Function Signatures

**Issue types:** `"bug"`, `"feature"`, `"task"`, `"epic"`, `"chore"`  
**Priorities:** `0` (critical) → `4` (backlog). Default: `2` (medium)  
**Status values:** `"open"`, `"in_progress"`, `"blocked"`, `"closed"`  
**Dependency types:** `"blocks"` (default), `"related"`, `"parent-child"`, `"discovered-from"`

**Labels:** Provide as comma-separated string (e.g., `"backend,urgent"`) or array/list.

## Using CLI Commands (Codex CLI)

When MCP is not available (e.g., Codex CLI), use `bd` CLI commands directly:

### Finding Ready Work

```bash
bd ready --json                    # List unblocked issues (JSON format)
bd ready                          # Human-readable format
bd ready --limit 20               # Limit number of results
bd ready --priority 1             # Filter by priority
bd ready --assignee ProductThor   # Filter by assignee
bd ready --sort priority          # Sort by priority (strict order)
bd ready --sort oldest            # Sort by creation date
bd ready --sort hybrid            # Recent by priority, old by age (default)
```

**What is "ready work"?** Issues with no open blockers (all blocking dependencies are closed).

### Creating Issues

```bash
# Basic creation
bd create "Issue title" -t bug -p 1 --json

# With description
bd create "Issue title" -t feature -p 1 -d "Detailed description here" --json

# With labels
bd create "Fix auth bug" -t bug -p 1 -l auth,backend,urgent --json

# Create epic (hierarchical children get auto-numbered suffixes)
bd create "Auth System" -t epic -p 1 --json  # Returns: nm-a3f8e9
# Next issues automatically become: nm-a3f8e9.1, nm-a3f8e9.2, etc.

# Create with explicit ID (for parallel workers)
bd create "Issue title" --id worker1-100 -p 1 --json

# Create multiple from markdown file
bd create -f feature-plan.md --json
```

**Important:** Always quote titles and descriptions with double quotes, especially when they contain special characters or spaces.

### Listing Issues

```bash
bd list --json                    # All issues (JSON)
bd list                           # Human-readable
bd list --status open             # Filter by status
bd list --type bug                # Filter by type
bd list --priority 1              # Filter by priority
bd list --label backend,auth      # AND filtering (must have all labels)
bd list --label-any frontend,ui   # OR filtering (any match)
```

### Viewing Issue Details

```bash
bd show <id> --json               # Single issue
bd show <id> <id> <id> --json    # Multiple issues
bd show nm-a1b2                   # Human-readable
```

### Updating Issues

```bash
bd update <id> --status in_progress --json
bd update <id> --status blocked --json
bd update <id> --status closed --json
bd update <id> --priority 1 --json
bd update <id> --assignee ProductThor --json
bd update <id> <id> <id> --status in_progress --json  # Multiple issues
```

**Status values:** `open`, `in_progress`, `blocked`, `closed`

### Closing Issues

```bash
bd close <id> --reason "Completed implementation" --json
bd close <id> <id> <id> --reason "Batch completion" --json  # Multiple issues
```

**Always provide a reason** - it helps with audit trails and understanding what was accomplished.

### Reopening Issues

```bash
bd reopen <id> --reason "Needs more work" --json
```

## Issue Types and Priorities

### Issue Types

- `bug` - Something broken that needs fixing
- `feature` - New functionality
- `task` - Work item (tests, docs, refactoring)
- `epic` - Large feature composed of multiple issues (supports hierarchical children)
- `chore` - Maintenance work (dependencies, tooling)

### Priorities

- `0` - Critical (security, data loss, broken builds)
- `1` - High (major features, important bugs)
- `2` - Medium (default, nice-to-have features, minor bugs)
- `3` - Low (polish, optimization)
- `4` - Backlog (future ideas)

## Dependency Management

### Adding Dependencies

```bash
# Hard blocker (default) - affects ready work queue
bd dep add <dependent-id> <blocker-id>

# Soft relationship - informational only
bd dep add <dependent-id> <related-id> --type related

# Epic/subtask hierarchy
bd dep add <child-id> <parent-id> --type parent-child

# Track discovered work
bd dep add <discovered-id> <parent-id> --type discovered-from

# Create and link in one command (new way)
bd create "Found bug in auth" -t bug -p 1 --deps discovered-from:<parent-id> --json
```

### Dependency Types

- `blocks` (default) - Hard dependency; issue cannot start until blocker is resolved. **Affects ready work queue.**
- `related` - Soft relationship; issues are connected but not blocking
- `parent-child` - Hierarchical relationship (child depends on parent)
- `discovered-from` - Issue discovered during work on another issue

### Viewing Dependencies

```bash
bd dep tree <id>                  # Show full dependency tree
bd dep cycles                     # Detect circular dependencies
bd blocked                        # Show all blocked issues
```

### Removing Dependencies

```bash
bd dep remove <idA> <idB>
```

## Labels

Labels provide flexible categorization beyond structured fields (status, priority, type).

### Adding Labels

```bash
# During creation
bd create "Fix auth bug" -t bug -p 1 -l auth,backend,urgent --json

# To existing issue
bd label add <id> backend,urgent --json
bd label add <id> <id> <id> security --json  # Multiple issues
```

### Removing Labels

```bash
bd label remove <id> urgent --json
bd label remove <id> <id> <id> urgent --json  # Multiple issues
```

### Listing Labels

```bash
bd label list <id> --json        # Labels on one issue
bd label list-all --json         # All labels with usage counts
```

### Filtering by Labels

```bash
# AND filtering (must have ALL labels)
bd list --label backend,auth --json

# OR filtering (must have AT LEAST ONE)
bd list --label-any frontend,backend --json

# Combine with other filters
bd list --status open --priority 1 --label security --json
```

### Common Label Patterns

**Technical components:**
- `backend`, `frontend`, `api`, `database`, `infrastructure`, `cli`, `ui`

**Domain/feature areas:**
- `auth`, `payments`, `search`, `analytics`, `billing`

**Size/effort:**
- `small` (< 1 day), `medium` (1-3 days), `large` (> 3 days)

**Quality gates:**
- `needs-review`, `needs-tests`, `needs-docs`, `breaking-change`

**Release tracking:**
- `v1.0`, `v2.0`, `backport-candidate`, `release-blocker`

**Process markers:**
- `auto-generated`, `technical-debt`, `good-first-issue`, `duplicate`

## Agent Workflow

### Standard Agent Session

```bash
# 1. Check for ready work
bd ready --json

# 2. Claim your task
bd update nm-a1b2 --status in_progress --json

# 3. Work on it (implement, test, document)

# 4. If you discover new work during implementation:
bd create "Found bug in auth.go" -t bug -p 1 \
  -l auto-generated,technical-debt \
  --deps discovered-from:nm-a1b2 --json

# 5. Complete the work
bd close nm-a1b2 --reason "Implemented and tested" --json

# 6. CRITICAL: Always sync at end of session
bd sync  # Forces immediate export, commit, pull, import, push
```

### Why `bd sync` is Critical

The `bd sync` command:
1. Exports pending changes to JSONL immediately (bypasses 30-second debounce)
2. Commits to git
3. Pulls from remote
4. Imports any updates
5. Pushes to remote

**Without `bd sync`:** Changes sit in a 30-second debounce window, and the user might think you pushed but JSONL is still dirty.

### Finding Forgotten Work

```bash
bd stale --days 30 --json                    # Issues not updated in 30 days (default)
bd stale --days 90 --status in_progress --json  # Filter by status
bd stale --limit 20 --json                   # Limit results
```

## Git Integration

### Auto-Sync Behavior

bd automatically:
- **Exports** to `.beads/issues.jsonl` after CRUD operations (30-second debounce for batching)
- **Imports** from JSONL when it's newer than DB (e.g., after `git pull`)
- **Daemon commits/pushes** every 5 seconds (if `--auto-commit` / `--auto-push` enabled)

The 30-second debounce provides a **transaction window** for batch operations.

### Manual Sync

```bash
bd sync  # Force immediate export, commit, pull, import, push
```

### Git Hooks (Recommended)

Install git hooks for automatic sync (prevents stale JSONL problems):

```bash
# One-time setup - run this in each beads workspace
./examples/git-hooks/install.sh
```

This installs:
- **pre-commit** - Flushes pending changes immediately before commit
- **post-merge** - Imports updated JSONL after pull/merge
- **pre-push** - Exports database to JSONL before push

### Handling Merge Conflicts

With hash-based IDs (v0.20.1+), ID collisions are eliminated. Conflicts happen when the same issue is modified on both branches.

**Resolution:**
```bash
# After git merge creates conflict
git checkout --theirs .beads/issues.jsonl  # Accept remote version
# OR
git checkout --ours .beads/issues.jsonl    # Keep local version

# Import the resolved JSONL
bd import -i .beads/issues.jsonl

# Commit the merge
git add .beads/issues.jsonl
git commit
```

## Advanced Usage

### Issue IDs

- **Hash-based** (e.g., `nm-a1b2`, `nm-f14c`) - Not sequential! Prevents collisions when multiple agents/branches work concurrently.
- Epic children use dotted notation: `nm-a3f8e9.1`, `nm-a3f8e9.2`
- Hierarchical children are auto-numbered sequentially (up to 3 levels of nesting)

### Duplicate Detection & Merging

```bash
# Find duplicates
bd duplicates

# Automatically merge all duplicates
bd duplicates --auto-merge

# Preview merge
bd duplicates --dry-run

# Merge specific issues
bd merge <source-id> <source-id> --into <target-id> --dry-run  # Preview
bd merge <source-id> <source-id> --into <target-id> --json     # Execute
```

### Statistics and Reporting

```bash
bd stats                          # Project statistics
bd blocked                        # Show blocked issues and dependencies
```

### Prefix Renaming

```bash
bd rename-prefix kw- --dry-run   # Preview changes
bd rename-prefix kw- --json      # Apply rename
```

### Migration (After Upgrading bd)

```bash
bd migrate --dry-run              # Check for migration opportunities
bd migrate                        # Migrate old databases
bd migrate --cleanup --yes        # Migrate and clean up old files
```

### Daemon Management

```bash
bd daemons list --json            # List all running daemons
bd daemons health --json          # Check for version mismatches, stale sockets
bd daemons stop /path/to/workspace --json  # Stop specific daemon
bd daemons killall --json         # Stop all daemons
bd daemons logs /path/to/workspace -n 100  # View daemon logs
```

**When to use:**
- After upgrading bd: Run `bd daemons health`, then `bd daemons killall`
- Debugging: Use `bd daemons logs` to view daemon logs

### Import/Export

```bash
bd export -o issues.jsonl         # Manual export
bd import -i issues.jsonl        # Manual import
bd import -i issues.jsonl --dedupe-after  # Import + detect duplicates
```

**Note:** Auto-sync is enabled by default. Manual export/import is rarely needed.

### JSON Output

**Always use `--json` flag for programmatic use** - it provides structured data that's easier to parse and process.

Example:
```bash
bd ready --json | jq '.[] | select(.priority == 1)'
bd list --json | jq '.[] | {id, title, status, labels}'
```

## Best Practices

1. **Always use `--json` flags** for programmatic use in agents
2. **Always run `bd sync` at end of agent sessions** to flush/commit/push immediately
3. **Link discoveries** with `discovered-from` dependencies to maintain context
4. **Check `bd ready`** before asking "what next?"
5. **Use labels consistently** for efficient filtering and categorization
6. **Define dependencies meticulously** to maintain clear workflow and prevent bottlenecks
7. **Provide clear reasons** when closing issues for better audit trails
8. **Use epics** for large features and organize subtasks hierarchically
9. **Periodically check `bd stale`** to find forgotten work
10. **Don't modify `.beads/` manually** - always use CLI commands

## Troubleshooting

### Database Not Found
```bash
bd init --quiet
```

### Version Mismatch Warning
```bash
bd daemons killall  # Restart all daemons with new version
```

### Labels Not Showing
Labels require explicit fetching. Use `--json` flag or `bd label list <id>`.

### Changes Not Syncing
Run `bd sync` to force immediate sync. Check git hooks are installed.

### Stale Sockets
```bash
bd daemons list  # Auto-removes stale sockets
bd daemons killall  # Force restart all daemons
```

## Additional Resources

- [Beads README](https://github.com/steveyegge/beads/blob/main/README.md) - Main documentation
- [Beads AGENTS.md](https://github.com/steveyegge/beads/blob/main/AGENTS.md) - AI agent integration guide
- [Beads LABELS.md](https://github.com/steveyegge/beads/blob/main/LABELS.md) - Label system guide
- [Beads QUICKSTART.md](https://github.com/steveyegge/beads/blob/main/QUICKSTART.md) - Quick start tutorial

## Project-Specific Conventions (Neumann)

- **Issue ID prefix:** `nm-` (e.g., `nm-a1b2`)
- **Commit messages:** Always reference issue ID (e.g., "Fix rendering bug (nm-42)")
- **Epics:** Use for multi-stage initiatives (e.g., Phase 2, Phase 3)
- **Labels:** Use technical labels like `backend`, `frontend`, `api`, `search`, `renderer`


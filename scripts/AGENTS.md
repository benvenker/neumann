# Scripts & Environment Agent Guide

This guide covers the runtime environment, script usage, and process management for Neumann.

## 1. tmux Usage Policy (MANDATORY)

**Protocol Override**: Follow the [Operational Protocols in root AGENTS.md](../AGENTS.md#1-operational-capabilities--protocols) for all long-running processes.

You **MUST** use `tmux` for:
- API Servers (`uvicorn`).
- Long ingestion runs (> 1 minute).
- Background watchers or services.

- **Session Naming**: `neumann-<purpose>` (e.g., `neumann-api`, `neumann-render`).
- **User Communication**: Always inform the human user when starting a session (name, command, attach instructions).
- **Management**:
  - List: `tmux ls`
  - Detach: `Ctrl+b, d`
  - Kill: `tmux kill-session -t <name>`

**Example**:
```bash
tmux new -s neumann-api
uvicorn api.app:app --reload --port 8001
```

## 2. Environment Variables & Configuration

### ⚠️ Critical: Pydantic Precedence
Pydantic loads environment variables in this order (highest to lowest):
1. **Environment variables** (e.g., `export KEY=...` in shell)
2. **.env file**
3. **Default values**

**Problem**: Global exports in `~/.zshrc` or `~/.env` will **override** the project's `.env` file.
**Solution**: Never export API keys globally. Use project-local `.env` files.

### Detecting Overrides
```bash
env | grep OPENAI_API_KEY  # Should be empty (unless direnv is active)
```

### Running Manual Tests
We use `direnv` to manage the environment.
1. **Setup**: `direnv allow` (whitelists `.envrc`).
2. **Verify**: `direnv status` should show "loaded".

**Fallback**: If direnv is not available, use the wrapper script:
```bash
scripts/test-manual tests/manual/test_summarization.py
```
This script manually ensures the correct environment variables are loaded.

## 3. Restarting Processes
When `.env` changes, you must restart running processes (tmux sessions).
```bash
tmux kill-session -t neumann-api
# Re-create session to load new env vars
```

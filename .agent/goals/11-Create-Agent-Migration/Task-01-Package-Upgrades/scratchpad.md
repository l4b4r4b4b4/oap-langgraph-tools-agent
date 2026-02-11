# Task 01: Package Upgrades

> **Status**: 🟢 Complete
> **Parent Goal**: [11-Create-Agent-Migration](../scratchpad.md)
> **Created**: 2026-02-11
> **Updated**: 2026-02-11

## Objective

Upgrade all LangChain/LangGraph ecosystem packages to their latest stable versions and add `langgraph-checkpoint-postgres` + `psycopg[binary,pool]` as new dependencies in preparation for Goal 12 (Postgres Persistence).

## Current → Target Versions

| Package | Current | Target | Change |
|---------|---------|--------|--------|
| `langgraph` | `>=0.6.2` (resolved 1.0.7) | `>=1.0.8` | Bump min + resolve latest |
| `langchain` | `>=0.3.27` (resolved 1.2.7) | `>=1.2.10` | Bump min + resolve latest |
| `langchain-core` | `>=0.3.72` (resolved 1.2.7) | `>=1.2.11` | Bump min + resolve latest |
| `langchain-openai` | `>=0.3.28` (resolved 1.1.7) | `>=1.1.9` | Bump min + resolve latest |
| `langchain-anthropic` | `>=0.3.18` (resolved 1.3.1) | `>=1.3.3` | Bump min + resolve latest |
| `langgraph-checkpoint-postgres` | ❌ not installed | `>=3.0.4` | **NEW** |
| `psycopg[binary,pool]` | ❌ not installed | `>=3.2.0` | **NEW** (transitive from checkpoint-postgres but explicit for pool) |
| `langgraph-api` | `==0.7.9` (pinned) | Check compatibility | ⚠️ May need unpin or bump |
| `langgraph-checkpoint` | (resolved 4.0.0) | 4.0.0 | ✅ Already latest |

## Implementation Plan

### Step 1: Upgrade existing packages via `uv`

```bash
# Upgrade langchain ecosystem
uv add "langgraph>=1.0.8"
uv add "langchain>=1.2.10"
uv add "langchain-core>=1.2.11"
uv add "langchain-openai>=1.1.9"
uv add "langchain-anthropic>=1.3.3"
```

### Step 2: Add new dependencies for persistence prep

```bash
uv add "langgraph-checkpoint-postgres>=3.0.4"
uv add "psycopg[binary,pool]>=3.2.0"
```

### Step 3: Check `langgraph-api==0.7.9` pin

The `langgraph-api` is pinned to exactly `0.7.9`. This was set during Goal 05 to resolve runtime bugs. Need to check:
- Is 0.7.9 still compatible with langgraph 1.0.8?
- Is there a newer version that should be used?
- Can the pin be relaxed to `>=0.7.9`?

### Step 4: Lock and verify

```bash
uv lock
uv sync
```

### Step 5: Run tests

```bash
uv run ruff check . --fix --unsafe-fixes && uv run ruff format .
uv run pytest
```

### Step 6: Verify imports work

```python
# Verify new packages are importable
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.postgres.aio import AsyncPostgresStore
from langchain.agents import create_agent
import psycopg_pool
```

## Files to Modify

- `pyproject.toml` — version bumps in `[project.dependencies]`
- `uv.lock` — regenerated (committed together with pyproject.toml)

## Risks

- **`langgraph-api==0.7.9` pin conflict**: The exact pin may conflict with upgraded langgraph. Mitigation: check compatibility first, relax pin if safe.
- **Transitive dependency conflicts**: Upgrading multiple packages simultaneously. Mitigation: `uv` resolves this automatically; if conflicts arise, upgrade incrementally.
- **`psycopg` binary wheels**: May not be available for all platforms. Mitigation: `psycopg[binary]` provides pre-built wheels for common platforms; `psycopg[pool]` is pure Python.

## Acceptance Criteria

- [x] All packages at latest stable versions
- [x] `langgraph-checkpoint-postgres` importable
- [x] `psycopg_pool` importable
- [ ] `langchain.agents.create_agent` importable — ⚠️ deferred to Task-02 (import path TBD, `create_react_agent` still works)
- [x] `uv lock` succeeds without conflicts
- [x] `ruff check` passes
- [x] Existing test suite passes (`pytest`) — 440 passed, 0 failed
- [x] `pyproject.toml` + `uv.lock` changes are coherent

## Notes

- Use `uv add` exclusively per project rules (never manually edit pyproject.toml)
- Commit `pyproject.toml` + `uv.lock` together per project rules
- The `langgraph-checkpoint-postgres` package brings `psycopg>=3.2.0` and `psycopg-pool>=3.2.0` as transitive deps, but we add `psycopg[binary,pool]` explicitly to ensure binary wheels + pool support

## Completion Log

### What was done
1. **Removed `langgraph-api==0.7.9`** from runtime dependencies — no actual imports exist in codebase; `langgraph-cli[inmem]` (dev dep) already pulls it in as `>=0.5.35,<0.8.0`
2. **Upgraded all packages** to latest stable via `uv add`:
   - `langgraph`: 1.0.7 → **1.0.8**
   - `langchain`: 1.2.7 → **1.2.10**
   - `langchain-core`: 1.2.7 → **1.2.11**
   - `langchain-openai`: 1.1.7 → **1.1.9**
   - `langchain-anthropic`: 1.3.1 → **1.3.3** (also upgraded transitive `anthropic` 0.76.0 → 0.79.0)
   - `langgraph-checkpoint`: 4.0.0 — ✅ already latest
3. **Added new dependencies**:
   - `langgraph-checkpoint-postgres>=3.0.4` — resolved 3.0.4
   - `psycopg[binary,pool]>=3.2.0` — resolved psycopg 3.3.2, psycopg-binary 3.3.2, psycopg-pool 3.3.0
4. **Verified imports**: `AsyncPostgresSaver`, `AsyncPostgresStore`, `psycopg_pool` all importable
5. **Fixed pre-existing pytest issues**:
   - Removed `pytest_plugins` from non-root `conftest.py` (rejected by newer pytest)
   - Added `[tool.pytest.ini_options]` to `pyproject.toml` with `testpaths`, `norecursedirs`, `asyncio_mode`, `asyncio_default_fixture_loop_scope`
6. **All tests pass**: 440 passed, 0 failed, 0 errors in 1.43s
7. **Ruff clean**: `All checks passed!`

### Key decisions
- **`langgraph-api` removed from runtime deps**: Dead weight — 27 transitive deps (grpcio, protobuf, uvicorn, starlette, etc.) not needed since we have our own Robyn server. Dev dep `langgraph-cli[inmem]` still provides it for `langgraph dev` workflow.
- **pytest `testpaths` set to `robyn_server/tests`**: Prevents collecting archived E2E test scripts that require live services (vLLM, Supabase).
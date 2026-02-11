# Goal 11: Package Upgrade & `create_agent` Migration

> **Status**: 🟢 Complete
> **Priority**: P1 (High)
> **Created**: 2026-02-11
> **Updated**: 2026-02-11

## Overview

Upgrade all LangChain/LangGraph packages to their latest stable versions and migrate the agent from the deprecated `langgraph.prebuilt.create_react_agent` to the new `langchain.agents.create_agent` API introduced in LangChain v1. This migration is a prerequisite for Goal 12 (Postgres Persistence) and aligns the project with the officially recommended agent construction pattern.

## Success Criteria

- [x] All langchain/langgraph packages upgraded to latest stable versions
- [x] `langgraph-checkpoint-postgres` and `psycopg[binary,pool]` added as dependencies (prep for Goal 12)
- [x] `tools_agent/agent.py` migrated from `create_react_agent` to `create_agent`
- [x] `prompt=` → `system_prompt=` parameter rename applied
- [x] `config_schema=GraphConfigPydantic` handling adapted for new API (removed — not a param of `create_agent`)
- [x] Streaming node name references updated in `robyn_server/routes/streams.py` (`"agent"` → `"model"`)
- [x] SSE streaming verified end-to-end (live test with Ministral-3B via vLLM)
- [x] All existing tests pass (440 passed, 0 failures)
- [x] No regressions in Robyn runtime behavior

## Context & Background

**Why now?** LangGraph v1 (released, we're on 1.0.7) officially deprecates `create_react_agent` in favor of `create_agent`. The new API provides:
- Middleware system for dynamic prompts, tool error handling, guardrails
- Cleaner separation of concerns (context injection vs config)
- Better alignment with LangChain v1 ecosystem
- Required foundation for Postgres persistence integration (Goal 12)

**Current state:**
- `langgraph: 1.0.7` — latest is **1.0.8**
- `langchain: 1.2.7` — latest is **1.2.10**
- `langchain-core: 1.2.7` — latest is **1.2.11**
- `langchain-openai: 1.1.7` — latest is **1.1.9**
- `langchain-anthropic: 1.3.1` — latest is **1.3.3**
- `langgraph-checkpoint: 4.0.0` — ✅ already latest
- `langgraph-checkpoint-postgres` — ❌ not installed (needed for Goal 12)

**Key migration changes** (from [LangChain v1 migration guide](https://docs.langchain.com/oss/python/migrate/langchain-v1)):

| Aspect | Old (`create_react_agent`) | New (`create_agent`) |
|--------|---------------------------|---------------------|
| Import | `from langgraph.prebuilt import create_react_agent` | `from langchain.agents import create_agent` |
| Prompt | `prompt=` | `system_prompt=` |
| Config schema | `config_schema=GraphConfigPydantic` | Removed — use middleware or `state_schema` |
| ⚠️ Streaming node | `"agent"` | `"model"` |
| Dynamic config | via `config_schema` + `configurable` | via middleware system |
| Tool errors | Built-in | Middleware `wrap_tool_call` |

## Constraints & Requirements

- **Hard Requirements**:
  - No breaking changes to the Robyn runtime HTTP API contract
  - SSE streaming must continue to work with the same event format
  - The OAP UI `x_oap_ui_config` metadata on `GraphConfigPydantic` must remain functional
  - `pyproject.toml` + `uv.lock` committed together after upgrades
- **Soft Requirements**:
  - Minimize code churn — targeted migration, not a rewrite
  - Maintain backward compatibility for `langgraph dev` runtime path
- **Out of Scope**:
  - Postgres persistence (Goal 12)
  - Middleware system adoption beyond basic migration
  - `create_agent` middleware for dynamic prompts (future enhancement)

## Approach

1. **Package upgrades first** — get on latest, run tests, confirm baseline
2. **Agent migration** — swap `create_react_agent` → `create_agent` in `agent.py`
3. **Streaming fixes** — update node name references in `streams.py`
4. **Full testing** — verify the complete pipeline

## Tasks

| Task ID | Description | Status | Depends On |
|---------|-------------|--------|------------|
| Task-01 | Package Upgrades — upgrade all langchain/langgraph to latest, add checkpoint-postgres | 🟢 | - |
| Task-02 | Agent Migration — `create_react_agent` → `create_agent` in `agent.py` | 🟢 | Task-01 |
| Task-03 | Streaming Compatibility — fix node name refs in `streams.py` | 🟢 | Task-02 |
| Task-04 | Testing — full pipeline verification | 🟢 | Task-03 |

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Streaming node name change breaks SSE | High | High | Task-03 explicitly addresses this; grep all `"agent"` refs in streams.py |
| `config_schema` removal breaks OAP UI config | Medium | Medium | `GraphConfigPydantic` parsing is already manual in `graph()`; config_schema was informational |
| Package upgrade introduces breaking changes | Medium | Low | All upgrades are patch-level; run full test suite after upgrade |
| `create_agent` signature differs from `create_react_agent` | Medium | Medium | Review signature carefully; both accept checkpointer/store |

## Dependencies

- **Upstream**: None (all packages are public PyPI)
- **Downstream**: Goal 12 (Postgres Persistence) depends on this goal completing

## Files to Modify

- `pyproject.toml` — version bumps + new dependencies
- `uv.lock` — regenerated
- `tools_agent/agent.py` — core migration
- `robyn_server/routes/streams.py` — streaming node name fix
- Possibly `robyn_server/routes/sse.py` — if event format references node names

## Notes & Decisions

### Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-11 | Do migration before persistence | Clean foundation before adding complexity |
| 2026-02-11 | Add checkpoint-postgres dep in Task-01 | Avoid a second dependency churn for Goal 12 |
| 2026-02-11 | Keep `GraphConfigPydantic` as-is | It's manually parsed in `graph()` already; config_schema was only for LangGraph runtime introspection |

### Open Questions (Resolved)

- [x] Does `create_agent` support `astream_events` the same way as `create_react_agent`? → **Yes** — confirmed via live SSE streaming test. Same v2 events, just node name changed from `"agent"` to `"model"`.
- [x] Should we adopt middleware for the dynamic model selection logic? → **Deferred** — existing manual config parsing in `graph()` works. Middleware is a future enhancement.
- [x] Is the `langgraph-api==0.7.9` pin still needed/compatible with latest langgraph? → **Removed entirely** — no imports exist in codebase; `langgraph-cli[inmem]` dev dep provides it for `langgraph dev` workflow.

## Completion Summary

**Completed**: 2026-02-11

### Final Package Versions
| Package | Before | After |
|---------|--------|-------|
| `langgraph` | 1.0.7 | **1.0.8** |
| `langchain` | 1.2.7 | **1.2.10** |
| `langchain-core` | 1.2.7 | **1.2.11** |
| `langchain-openai` | 1.1.7 | **1.1.9** |
| `langchain-anthropic` | 1.3.1 | **1.3.3** |
| `langgraph-checkpoint-postgres` | ❌ | **3.0.4** (new) |
| `psycopg[binary,pool]` | ❌ | **3.3.2** (new) |
| `langgraph-api` | ==0.7.9 | **removed** from runtime deps |

### Commits
1. `d1279cb` — Task-01: Package upgrades + pytest config fixes
2. `ab61422` — Task-02+03: `create_agent` migration + streaming node name fix

### Live Verification
- Ministral-3B via vLLM → Robyn SSE streaming → Supabase auth: **all working**
- 440 unit tests passing, ruff clean

## References

- [LangChain v1 Migration Guide](https://docs.langchain.com/oss/python/migrate/langchain-v1)
- [LangGraph v1 Migration Guide](https://docs.langchain.com/oss/python/migrate/langgraph-v1)
- [LangGraph v1 Release Notes](https://docs.langchain.com/oss/python/releases/langgraph-v1)
- [LangChain v1 Release Notes](https://docs.langchain.com/oss/python/releases/langchain-v1)
- [create_agent API docs](https://docs.langchain.com/oss/python/langchain/short-term-memory)
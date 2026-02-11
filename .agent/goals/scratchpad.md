# Goals Index & Tracking Scratchpad

> Central hub for tracking all goals in `l4b4r4b4b4/oap-langgraph-tools-agent`

---

## Active Goals

| ID | Goal Name | Status | Priority | Last Updated |
|----|-----------|--------|----------|--------------|
| 01 | Repo scaffolding (flake.nix + .rules + branch protection + CI/CD to GHCR) | 🟢 Complete | Critical | 2026-01-27 |
| 02 | Remove LangSmith dependency and integration code | 🟡 In Progress | High | 2026-01-27 |
| 03 | Add Langfuse tracing (replace LangSmith tracing path) | ⚪ Not Started | High | - |
| 04 | Supabase development stack integration | 🟡 In Progress | High | 2026-01-27 |
| 05 | OpenAI-compatible LLM integration (vLLM) | 🟢 Complete | Critical | 2026-01-30 |
| 06 | Robyn Runtime Server (LangGraph API parity) | 🟢 Complete | Critical | 2026-02-05 |
| 07 | Bun + TypeScript Runtime (LangGraph JS) | ⚪ Not Started | High | 2026-01-30 |
| 08 | CI/CD DevOps Workflow & Feature Parity | 🟡 In Progress | Critical | 2026-02-05 |
| 10 | SSE Messages-Tuple Protocol Compatibility | 🟡 In Progress | Critical | 2026-02-20 |
| 11 | Package Upgrade & `create_agent` Migration | 🟢 Complete | High | 2026-02-11 |
| 12 | Postgres Persistence (Supabase) | 🟢 Complete | High | 2026-02-14 |
| 13 | MCP Agent Integration | 🟢 Complete | Medium | 2026-02-14 |
| 14 | Agent Persistence (Supabase/Postgres) | ⚪ Not Started | Medium | 2026-02-11 |

---

## Status Legend

- 🟢 **Complete** — Goal achieved and verified
- 🟡 **In Progress** — Actively being worked on
- 🔴 **Blocked** — Waiting on external dependency or decision
- ⚪ **Not Started** — Planned but not yet begun
- ⚫ **Archived** — Abandoned or superseded

---

## Priority Levels

- **Critical** — Blocking other work or system stability
- **High** — Important for near-term objectives
- **Medium** — Should be addressed when time permits
- **Low** — Nice to have, no urgency

---

## Quick Links

- [00-Template-Goal](./00-Template-Goal/scratchpad.md) — Template for new goals
- [01-Repo-Scaffolding](./01-Repo-Scaffolding/scratchpad.md)
- [02-Remove-LangSmith](./02-Remove-LangSmith/scratchpad.md)
- [03-Add-Langfuse-Tracing](./03-Add-Langfuse-Tracing/scratchpad.md)
- [04-Supabase-Integration](./04-Supabase-Integration/scratchpad.md)
- [05-LLM-Integration](./05-LLM-Integration/scratchpad.md)
- [06-Robyn-Runtime](./06-Robyn-Runtime/scratchpad.md)
- [07-Bun-TypeScript-Runtime](./07-Bun-TypeScript-Runtime/scratchpad.md)
- [08-CI-CD-Feature-Parity](./08-CI-CD-Feature-Parity/scratchpad.md)
- [10-SSE-Messages-Tuple-Protocol](./10-SSE-Messages-Tuple-Protocol/scratchpad.md)
- [11-Create-Agent-Migration](./11-Create-Agent-Migration/scratchpad.md)
- [12-Postgres-Persistence](./12-Postgres-Persistence/scratchpad.md)
- [13-MCP-Agent-Integration](./13-MCP-Agent-Integration/scratchpad.md)
- [14-Agent-Persistence](./14-Agent-Persistence/scratchpad.md)

---

## Goal Creation Guidelines

1. **Copy from template:** Use `00-Template-Goal/` as starting point
2. **Follow numbering:** Goals are `01-10-*`, tasks are `Task-01-*`
3. **Update this index:** Add new goals to the table above
4. **Reference, don't duplicate:** Link to detailed scratchpads instead of copying content

---

## Recent Activity

- 2026-02-14 (implementation session — Goals 12+13 Task-04):
  - Goal 12 Task-04: **COMPLETE** — Postgres Integration Testing
    - Created `test_database.py` (18 unit tests) — DB accessors, shutdown safety, config, in-memory fallback
    - Created `test_postgres_integration.py` (34 integration tests) — schema, all 5 stores CRUD, cascades, full lifecycle
    - Updated `conftest.py` — `@pytest.mark.postgres` marker, `postgres_pool`/`postgres_storage` fixtures, auto-skip when Postgres unavailable
    - Discovered 3 pre-existing bugs in `postgres_storage.py`: BUG-PG-001 (cron thread_id None), BUG-PG-002 (cron update dict serialisation), BUG-PG-003 (thread delete doesn't cascade to runs)
    - **Goal 12: 🟢 COMPLETE** — all 4 tasks done
  - Goal 13 Task-04: **COMPLETE** — MCP + Persistence Testing
    - 23 MCP tests (Task-03) + 18 DB unit + 34 Postgres integration = 75 new tests total
    - **Goal 13: 🟢 COMPLETE** — all 4 tasks done
    - 515/515 tests passing, ruff clean
  - **Next**: Phase 2 — Goal 14 (Agent Persistence), then Goals 02+03 (LangSmith removal + Langfuse)

- 2026-02-14 (implementation session — Goal 13 Task-03):
  - Goal 13 Task-03: **COMPLETE** — MCP Server: Wire Agent Execution & Dynamic Tools
    - Created `robyn_server/agent.py` (+364 lines) — `execute_agent_run()`, `get_agent_tool_info()`, config builder, response extractor
    - Wired `tools/call` to real agent execution via `execute_agent_run()` (removed placeholder fallback)
    - `tools/list` now dynamically built from assistant config (MCP sub-tools, RAG collections, model name)
    - `PROTOCOL_VERSION` bumped `"2024-11-05"` → `"2025-03-26"` (handlers + schemas)
    - Removed hardcoded `LANGGRAPH_AGENT_TOOL` global — replaced with `_get_dynamic_agent_tool()`
    - 23 new tests: protocol version, dynamic tool listing, agent execution wiring, agent module functions
    - 463/463 tests passing, ruff clean

- 2026-02-14 (implementation session — Goal 13 Task-02):
  - Goal 13 Task-02: **COMPLETE** — MCP Client: Adopt `langchain-mcp-adapters`
    - Added `langchain-mcp-adapters>=0.2.1` dependency (`mcp` bumped 1.9.1 → 1.26.0)
    - Replaced 55-line manual MCP connection block in `graph()` with ~15-line `MultiServerMCPClient` call
    - Removed `create_langchain_mcp_tool()` and `wrap_mcp_authenticate_tool()` from `tools_agent/utils/tools.py`
    - Created `tools_agent/utils/mcp_interceptors.py` — `handle_interaction_required` interceptor (code -32003 → clean `ToolException`)
    - `MCPConfig` backward-compatible with OAP UI (unchanged schema)
    - Relaxed `cfg.mcp_config.tools` requirement (load all tools if not specified, filter afterward)
    - 440/440 tests passing, ruff clean
  - **Next**: Goal 13 Task-03 — MCP Server: wire `execute_agent_run`, dynamic tool listing

- 2026-02-14 (research session — Goal 13 Task-01):
  - Goal 13 Task-01: **COMPLETE** — MCP Agent Integration Research
    - Evaluated `langchain-mcp-adapters` v0.2.1 (PyPI) — official LangChain MCP package, 28 releases, actively maintained
    - Compatible with our deps: `langchain-core>=1.0.0,<2.0.0` ✅, `mcp>=1.9.2` (needs patch bump from 1.9.1) ⚠️
    - Features: `MultiServerMCPClient` (multi-server, named servers), tool interceptors, stateful sessions, auth (headers + httpx.Auth), resources, prompts, progress notifications, elicitation, structured/multimodal content
    - **Decision: ADOPT `langchain-mcp-adapters`** — replaces ~200 lines of manual MCP client code with ~20 lines
    - Assessed current MCP client: 6 confirmed problems (no connection reuse, single server, manual wrapping, no caching, silent errors, no health checks)
    - Assessed current MCP server: 5 confirmed problems (agent execution not wired, no streaming, hardcoded single tool, manual JSON-RPC, outdated protocol version)
    - Decision: Keep manual JSON-RPC server for now (lower risk), just wire `execute_agent_run`
    - Refined task breakdown: Task-02 (adopt adapters), Task-03 (wire MCP server), Task-04 (testing)
    - Updated Goal 13 scratchpad with comprehensive findings
  - **Next**: Goal 13 Task-02 — MCP Client: adopt `langchain-mcp-adapters`, refactor `graph()`

- 2026-02-14 (implementation session):
  - Goal 12 Task-03: **COMPLETE** — Robyn Storage → Postgres (All 3 Phases)
    - Phase 1 ✅: ALL storage methods async, ALL route handlers + handlers await, ALL 7 test files converted
    - Phase 1 ✅: 440/440 tests passing (was 230/440 — converted remaining 5 test files)
    - Phase 1 ✅: Production bug fix — `streams.py` had missing `await` on final state store calls
    - Phase 2 ✅: Created `robyn_server/postgres_storage.py` (~1636 lines) — 5 Postgres store classes + container
    - Phase 2 ✅: Added DDL migration in `database.py` — `langgraph_server` schema + 6 tables + 2 indexes
    - Phase 2 ✅: Wired `get_storage()` to return `PostgresStorage` when `is_postgres_enabled()`
    - Phase 3 ✅: DDL migration verified against Supabase Postgres (6 tables, 8 indexes)
    - Phase 3 ✅: Full E2E test — CRUD on all 5 stores (assistants, threads, runs, store, crons) against real Postgres
    - Phase 3 ✅: `get_storage()` switch verified: `Storage` without Postgres, `PostgresStorage` with Postgres
    - 440/440 tests passing, ruff clean
    - **Remaining**: Task-04 (Integration Testing), then Goals 13 + 14
    - Branch: feat/goal-11-12-agent-migration-postgres-persistence (uncommitted, ready to commit)

- 2026-02-13 (implementation session):
  - Goal 12 Task-03: Phase 1 partially completed — async migration of production code + 2 test files

- 2026-02-12 (implementation session):
  - Goal 12: **IN PROGRESS** — Postgres Persistence
    - Task-01 ✅: Created `robyn_server/database.py` — shared `AsyncConnectionPool`, fast-fail probe, checkpointer/store init
    - Task-01 ✅: Added `DatabaseConfig` to `robyn_server/config.py` (DATABASE_URL + pool tuning env vars)
    - Task-01 ✅: Wired `@app.startup_handler` / `@app.shutdown_handler` in `app.py`
    - Task-01 ✅: Updated `/health` (persistence status) and `/info` (postgres capabilities)
    - Task-01 ✅: Automatic RLS hardening on LangGraph tables at startup (blocks PostgREST, superuser bypasses)
    - Task-02 ✅: Wired `checkpointer` + `store` into `create_agent()` in `tools_agent/agent.py`
    - Task-02 ✅: Live E2E test with Ministral-3B: multi-turn memory ("Alice loves chess") + thread isolation
    - Task-02 ✅: 6 checkpoints confirmed in Supabase Postgres, RLS verified, security advisors clean
    - 440 tests passing, ruff clean
    - **Remaining**: Task-03 (Robyn Storage → Postgres), Task-04 (Integration Testing)
    - Branch: feat/goal-11-12-agent-migration-postgres-persistence

- 2026-02-11 (implementation session, cont.):
  - Goal 13: **CREATED** — MCP Agent Integration
    - Improve MCP client: connection reuse, multi-server support, evaluate LangChain native MCP tools
    - Complete MCP server: wire agent execution, SSE streaming, dynamic tool listing
    - Depends on Goal 12 (Postgres Persistence)
    - Tasks: 01-Research, 02-MCP-Client-Improvements, 03-MCP-Server-Completion, 04-Testing
  - Goal 14: **CREATED** — Agent Persistence (Supabase/Postgres)
    - Persist agent definitions (graph factory refs, default config, tool bindings, versioning)
    - Agent registry in `langgraph_server` schema with version history
    - API endpoints for agent CRUD + versioning
    - Link assistants to agent definitions by ID + version
    - Depends on Goal 12 (Postgres Persistence)
    - Tasks: 01-Research-Design, 02-Database-Schema, 03-Agent-Registry, 04-API-Endpoints, 05-Assistant-Integration, 06-Testing

- 2026-02-11 (implementation session):
  - Goal 11: **COMPLETE** — Package Upgrade & `create_agent` Migration
    - Task-01 ✅: Upgraded all packages (langgraph 1.0.8, langchain 1.2.10, langchain-core 1.2.11, langchain-openai 1.1.9, langchain-anthropic 1.3.3)
    - Task-01 ✅: Added langgraph-checkpoint-postgres 3.0.4 + psycopg[binary,pool] 3.3.2
    - Task-01 ✅: Removed langgraph-api==0.7.9 from runtime deps (no imports; dev dep covers it)
    - Task-01 ✅: Fixed pytest config (non-root conftest, asyncio settings, testpaths)
    - Task-02 ✅: Migrated create_react_agent → create_agent (import, prompt→system_prompt, removed config_schema)
    - Task-03 ✅: Fixed streaming node name "agent" → "model" in streams.py, sse.py, test_streams.py
    - Task-04 ✅: Live-tested E2E with Ministral-3B via vLLM + Supabase auth + Robyn SSE streaming
    - 440 tests passing, ruff clean, full SSE event sequence verified
    - Branch: feat/goal-11-12-agent-migration-postgres-persistence
  - Goal 12: **READY** — Postgres Persistence (Supabase) — all prerequisites met (Goal 11 complete)

- 2026-02-11 (research session):
  - Goal 11: **CREATED** — Package Upgrade & `create_agent` Migration
  - Goal 12: **CREATED** — Postgres Persistence (Supabase)
    - Connect LangGraph checkpointer + store to Supabase Postgres (direct connection)
    - Replace in-memory Robyn runtime storage with Postgres-backed implementations
    - `langgraph_server` schema for runtime tables (assistants, threads, runs, crons, store_items)
    - `DATABASE_URL` env var config, in-memory fallback when not set
    - Tasks: 01-Dependencies-DB-Module, 02-LangGraph-Checkpointer, 03-Robyn-Storage-Postgres, 04-Integration-Testing
    - Depends on Goal 11 completion (now satisfied)

- 2026-02-20:
  - Goal 10: **CREATED** — SSE Messages-Tuple Protocol Compatibility
    - Branch: `fix/sse-messages-tuple-protocol`
    - Root cause: robyn-runtime emits old-format SSE events (`messages/partial` with accumulated content)
    - SDK v1.6.0 expects new-format (`messages` with delta content + inline metadata tuple)
    - Fix: update `sse.py` and `streams.py` to emit `event: messages` with `[delta, metadata]` tuples
    - Blocks real-time chat streaming in docproc-platform

- 2026-02-05:
  - Goal 06: **COMPLETE** — Robyn Runtime Server fully implemented
    - All 268 tests passing (240 core + 28 OpenAPI)
    - Docker build verified working
    - Deployed and tested on AKS
    - OpenAPI/Swagger UI with endpoint grouping
    - Tier 1 & 2 complete, Tier 3 partial (Crons/A2A/MCP deferred)
  - Goal 08: **CREATED** — CI/CD DevOps Workflow & Feature Parity
    - Establish proper CI/CD pipeline with branch protection
    - Feature branch → PR → CI → merge → CD workflow
    - Implement missing Crons, A2A, MCP endpoints
    - Separate Docker workflows for Robyn and LangGraph runtimes

## Notes

- Each goal has its own directory under `.agent/goals/`
- Goals contain a `scratchpad.md` and one or more `Task-XX/` subdirectories
- Tasks are atomic, actionable units of work within a goal
- Follow `.rules` workflow: Research → Plan → Pitch → Implement → Document

---

## Recent Activity

- 2026-01-30 (Task 01 Session):
  - Goal 06 Task 01: **COMPLETE** — Robyn Project Setup & Hello World
    - Added `robyn>=0.76.0` dependency via `uv add robyn`
    - Renamed `robyn_prototype/` to `robyn_server/`
    - Created directory structure: `config.py`, `models.py`, `routes/`
    - Implemented `/health`, `/`, `/info` endpoints
    - Key learnings: Robyn 0.76 validates handler signatures, auto-generates `/docs`
    - Server tested successfully on port 8081
  - Next: Task 02 — Authentication Middleware (port Supabase JWT auth)

- 2026-01-30 (Earlier):
  - Goal 05: **COMPLETE** — vLLM integration proven E2E via LangGraph Runtime API
    - In-process smoke test: `test_tools_agent_vllm_smoke.py`
    - Full auth E2E test: `test_with_auth_vllm.py`
    - Message parsing fixed for LangChain format
  - Goal 06: **CREATED** — Robyn Runtime Server (LangGraph API parity)
    - Prioritized Robyn implementation before Langfuse/persistence
    - Robyn has built-in MCP support which aligns with our architecture
    - Will replace `langgraph dev` with custom Rust-based HTTP server
    - Task 01 scratchpad created with detailed implementation plan
  - Goal 07: **CREATED** — Bun + TypeScript Runtime (LangGraph JS)
    - Planned for after Goal 06 completion
    - Rationale: Compiled TS/JS with JIT faster than interpreted Python
    - Bun native drivers outperform Python for DB/storage (per Anton Putra benchmarks)
    - Will use LangGraph JS SDK with Hono/Elysia HTTP framework
  - Priority order established:
    1. Goal 06: Robyn Runtime (validates API shape)
    2. Tool calling validation
    3. Documentation
    4. Goal 07: Bun/TypeScript Runtime
    5. Langfuse Prompt Management
    6. Dynamic agent loading
    7. Postgres persistence
    8. (Later) Azure OpenAI

- 2026-01-27:
  - Goal 04: Local Supabase dev stack integration documented (env values + local workflow notes).
  - Goal 05: Local vLLM (Ministral-3B) validated on `http://localhost:7374/v1` (OpenAI-compatible API).
  - Goal 05: Runtime bug root-caused and resolved by upgrading the LangGraph API server and updating request shape:
    - New server line: `langgraph-api==0.7.9` (pulled in LangGraph v1 / LangChain v1 family updates).
    - Assistant creation must persist settings under `AssistantCreate.config` (NOT top-level `configurable`).
    - After switching assistant payload to `{"config": {"configurable": {...}}}`, runtime runs stop calling OpenAI and can run successfully.
  - Goal 05: E2E test harness updated for LangGraph API 0.7.x behavior changes:
    - terminal status can be `"success"` (not `"completed"`)
    - `/threads/{thread_id}/messages` is removed; use `/threads/{thread_id}/history` or `/state` to inspect outputs.

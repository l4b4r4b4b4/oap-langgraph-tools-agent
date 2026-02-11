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
| 12 | Postgres Persistence (Supabase) | 🟡 In Progress | High | 2026-02-12 |
| 13 | MCP Agent Integration | ⚪ Not Started | Medium | 2026-02-11 |
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

# Goals Index & Tracking Scratchpad

> Central hub for tracking all goals in `l4b4r4b4b4/oap-langgraph-tools-agent`

---

## Active Goals

| ID | Goal Name | Status | Priority | Last Updated |
|----|-----------|--------|----------|--------------|
| 01 | Repo scaffolding (flake.nix + .rules + branch protection + CI/CD to GHCR) | 🟢 Complete | Critical | 2026-01-27 |
| 02 | Remove LangSmith dependency and integration code | 🟢 Complete | High | 2026-02-11 |
| 03 | Add Langfuse tracing (replace LangSmith tracing path) | 🟢 Complete | High | 2026-02-11 |
| 04 | Supabase development stack integration | 🟡 In Progress | High | 2026-01-27 |
| 05 | OpenAI-compatible LLM integration (vLLM) | 🟢 Complete | Critical | 2026-01-30 |
| 06 | Robyn Runtime Server (LangGraph API parity) | 🟢 Complete | Critical | 2026-02-05 |
| 07 | Bun + TypeScript Runtime (LangGraph JS) | ⚪ Not Started | High | 2026-01-30 |
| 08 | CI/CD DevOps Workflow & Feature Parity | 🟡 In Progress | Critical | 2026-02-05 |
| 10 | SSE Messages-Tuple Protocol Compatibility | 🟢 Complete | Critical | 2026-02-20 |
| 11 | Package Upgrade & `create_agent` Migration | 🟢 Complete | High | 2026-02-11 |
| 12 | Postgres Persistence (Supabase) | 🟢 Complete | High | 2026-02-14 |
| 13 | MCP Agent Integration | 🟢 Complete | Medium | 2026-02-14 |
| 14 | Agent Persistence (Supabase/Postgres) | ⚫ Deferred | Low | 2026-02-11 |

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

- 2026-02-11 (deployment & docs session — PR #10):
  - **Docker deployment fixes**:
    - Root-caused `resource temporarily unavailable` — container appuser UID 1000 shared host nproc quota (4131/4096 threads)
    - Fixed: Dockerfile UID 1000 → 65532, added `ulimits.nproc: 65535` to compose
    - Removed `OPENAI_API_KEY=EMPTY` and `OPENAI_API_BASE` env overrides that blocked standard provider models
    - Removed unused `lm-awq` service from compose
  - **MCP external server support**:
    - Fixed agent.py: don't append `/mcp` if URL already ends with it
    - Tested with `https://docs.langchain.com/mcp` — MCP protocol v2025-06-18 negotiated successfully
  - **E2E verified (full Docker stack)**:
    - Supabase auth → create assistant → create thread → stream run ✅
    - OpenAI `gpt-4o-mini` + LangChain docs MCP → tool call + streamed response ✅
    - Ministral 3B (vLLM) basic chat ✅ (MCP tool results fail on vLLM due to stricter content block validation)
    - Postgres persistence + Langfuse tracing confirmed ✅
    - All `/info` capabilities true
  - **Documentation**: Created `docs/NEXTJS_INTEGRATION.md` — Next.js 16 + Bun 1.3 integration guide
    - Auth, SDK client, streaming hook, chat component, Server Actions, MCP config, model config, Docker deployment, troubleshooting
  - **PR #10 created** (`fix/docker-mcp-nextjs-docs`), CI passing, ready to merge
  - **Known issue**: vLLM rejects MCP tool results with structured content blocks (LangChain adds `id` fields vLLM doesn't accept). Use OpenAI/Anthropic for MCP+tool workflows.

- 2026-02-11 (implementation session — Goals 02+03 combined):
  - **Goals 02+03: COMPLETE** — LangSmith disabled + Langfuse tracing integrated
    - Created `tools_agent/tracing.py` — Langfuse lifecycle (init, shutdown, callback handler factory, `inject_tracing()`)
    - `LANGCHAIN_TRACING_V2` defaults to `"false"` at import time (LangSmith disabled unless explicit override)
    - Langfuse `CallbackHandler` injected at both invocation paths:
      - Streaming: `robyn_server/routes/streams.py` → `execute_run_stream()` with `trace_name="agent-stream"`
      - Non-streaming: `robyn_server/agent.py` → `execute_agent_run()` with `trace_name="mcp-invoke"`
    - Trace metadata: `langfuse_user_id` (owner), `langfuse_session_id` (thread), `langfuse_tags` (path-specific)
    - Startup/shutdown wired in `robyn_server/app.py` (`initialize_langfuse()` / `shutdown_langfuse()`)
    - `/info` endpoint includes `"tracing": is_langfuse_enabled()` capability flag
    - Added `langfuse>=3.14.1` dependency
    - 35 new tracing tests (`test_tracing.py`) — config detection, lifecycle, injection, graceful degradation
    - Removed `.agent/tmp/test_langsmith_startup.py`, `test_runtime.py`, `test_runtime_langsmith.py`
    - 550/550 tests passing, ruff clean
  - **Goal 14: DEFERRED** — single graph factory works fine with assistant configs; agent registry is premature abstraction until multiple graph types exist
  - **PR #8 merged** — Goals 10–13 squash-merged to `main` (`f6b38e6`)

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

- 2026-02-14 (research session — Goal 13 Task-01):
  - Goal 13 Task-01: **COMPLETE** — MCP Agent Integration Research
    - Evaluated `langchain-mcp-adapters` v0.2.1 (PyPI) — official LangChain MCP package, 28 releases, actively maintained
    - **Decision: ADOPT `langchain-mcp-adapters`** — replaces ~200 lines of manual MCP client code with ~20 lines

- 2026-02-14 (implementation session):
  - Goal 12 Task-03: **COMPLETE** — Robyn Storage → Postgres (All 3 Phases)
    - 440/440 tests passing, ruff clean

- 2026-02-13 (implementation session):
  - Goal 12 Task-03: Phase 1 partially completed — async migration of production code + 2 test files

- 2026-02-12 (implementation session):
  - Goal 12: **IN PROGRESS** — Postgres Persistence
    - Tasks 01+02 ✅: DB module, checkpointer/store, RLS, live E2E with Ministral-3B

- 2026-02-11 (implementation session):
  - Goal 11: **COMPLETE** — Package Upgrade & `create_agent` Migration
    - 440 tests passing, ruff clean, full SSE event sequence verified
  - Goals 12, 13, 14: **CREATED** — Postgres Persistence, MCP Integration, Agent Persistence

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

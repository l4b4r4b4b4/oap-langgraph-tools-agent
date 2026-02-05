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

---

## Goal Creation Guidelines

1. **Copy from template:** Use `00-Template-Goal/` as starting point
2. **Follow numbering:** Goals are `01-10-*`, tasks are `Task-01-*`
3. **Update this index:** Add new goals to the table above
4. **Reference, don't duplicate:** Link to detailed scratchpads instead of copying content

---

## Recent Activity

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

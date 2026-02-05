# Goal 03 — Add Langfuse Tracing (replace LangSmith tracing path)

**Status:** ⚪ Not Started  
**Priority:** High  
**Owner:** `l4b4r4b4b4/oap-langgraph-tools-agent`

## Objective

Replace LangSmith-style tracing (direct or implicit) with **Langfuse tracing** so that:

- Runs/spans are captured in Langfuse for agent execution and tool calls.
- Tracing can be enabled/disabled without code changes (configuration-based).
- No secrets are logged or hard-coded.

This goal depends on **Goal 02 (Remove LangSmith)** completing first (or at least removing/neutralizing LangSmith initialization), because mixing both usually creates confusing traces and extra deps.

## Success Criteria (Acceptance Checklist)

- [ ] Repository has **no LangSmith dependency** in runtime dependencies (Goal 02).
- [ ] Langfuse tracing is available and documented:
  - [ ] Minimal env var configuration documented (public key/secret key/host).
  - [ ] Clear “on/off” behavior defined (by env vars and/or a dedicated `ENABLE_TRACING` flag).
- [ ] Running the agent locally results in traces appearing in Langfuse for:
  - [ ] A normal LLM turn
  - [ ] At least one tool call (MCP tool or RAG tool)
- [ ] CI passes (`ruff`, `pytest`) and tracing additions do not break non-tracing execution.
- [ ] No sensitive data is exposed in logs, errors, or trace attributes.

## Assumptions / Open Decisions

### Tracing integration approach (to decide during implementation)
- **Option A: Langfuse Python SDK integration**
  - Pros: You’ve used it before; straightforward for custom spans.
  - Cons: Depends on how well it hooks into LangChain/LangGraph callbacks in this codebase.
- **Option B: OpenTelemetry (OTEL) + Langfuse OTEL ingestion**
  - Pros: Standardized, often plays nicely with frameworks; good ecosystem.
  - Cons: More moving parts; configuration overhead.

**Decision point:** Choose the approach after inspecting how current tracing is done (or implicitly enabled) and after Goal 02 confirms LangSmith removal. We will not implement both.

### Enable/disable behavior
- To be decided later per your note (“we decide this when we work on this”).
- Strong preference: enable tracing only when the required Langfuse env vars are present, optionally gated by an explicit flag if needed to avoid accidental tracing in dev.

## Context: What we have today

- Agent entrypoint is `tools_agent/agent.py` with `async def graph(config: RunnableConfig)`.
- Model is created with `init_chat_model(...)`.
- Tools are assembled dynamically (RAG + MCP tools).
- No explicit Langfuse code exists yet.
- LangSmith may still be present implicitly via dependencies and environment variables (Goal 02 is expected to clarify/remove this).

## Proposed Approach (High-Level)

1. **Inventory current tracing**
   - Search for LangSmith usage (imports, env vars, CLI flags, LangGraph/LangChain tracing settings).
   - Identify the most reliable insertion point:
     - Global init at process start, or
     - Per-request/per-run initialization inside `graph(config)`.

2. **Add Langfuse integration**
   - Introduce a small, well-contained module for tracing setup (e.g., `tools_agent/observability/langfuse_tracing.py`).
   - Keep implementation minimal and testable:
     - Read configuration from env
     - Initialize Langfuse
     - Provide a no-op fallback when disabled

3. **Instrument agent lifecycle**
   - Ensure each agent run is traced with useful metadata:
     - model name
     - tool list / tool usage
     - request identifiers if present (but do not log tokens/PII)
   - Where possible, hook into LangGraph/LangChain callbacks to capture tool spans automatically.

4. **Documentation**
   - Update `README.md` with:
     - required env vars
     - how to enable locally
     - how to verify traces

5. **Tests**
   - Add unit tests that validate:
     - tracing is a no-op when disabled
     - tracing initializes when env vars present
     - no secrets are emitted in logs/returned structures
   - Avoid tests that require actual Langfuse network connectivity (use mocks).

## Planned Task Breakdown

### Task 01 — Research current tracing points (⚪ Not Started)
- Locate any LangSmith tracing configuration, direct or indirect.
- Decide where tracing initialization belongs.

### Task 02 — Implement Langfuse tracing module (⚪ Not Started)
- Add the minimal integration layer.
- Keep dependencies and configuration explicit.

### Task 03 — Wire tracing into agent runtime (⚪ Not Started)
- Add callback/instrumentation integration for runs and tools.
- Ensure no-op fallback and safe metadata.

### Task 04 — Docs + tests (⚪ Not Started)
- Update `README.md`
- Add tests and run `pytest` + `ruff`

## Risks / Tradeoffs

- LangGraph/LangChain tracing hooks can change across versions; we should keep the integration narrow and version-aware.
- Over-instrumenting can leak data into traces. We must be conservative with attributes and ensure secrets/PII are excluded.
- Adding tracing dependencies may increase image size and import time; keep it minimal.

## Notes / Links

- Repo: `l4b4r4b4b4/oap-langgraph-tools-agent`
- Related goals:
  - Goal 01: Repo scaffolding and CI/CD to GHCR
  - Goal 02: Remove LangSmith dependency (must land before final tracing swap)

## Progress Log

- (none yet)

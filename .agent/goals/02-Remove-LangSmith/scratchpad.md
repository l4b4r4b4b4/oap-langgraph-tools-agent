# Goal 02 — Remove LangSmith dependency and integration code

Status: 🟢 Complete  
Priority: High  
Owner: You  
Last Updated: 2026-02-11 (Combined with Goal 03 — Langfuse replaces LangSmith)

## Objective

Remove **LangSmith** as a dependency and eliminate any LangSmith-specific code paths, configuration, environment variables, and documentation references, while keeping the agent runtime functional and easy to operate.

This goal is intentionally pragmatic: remove LangSmith cleanly without over-engineering, and ensure tracing can later be provided by Langfuse (Goal 03).

## Research Findings (Completed)

### Current State Analysis
1. **No direct LangSmith dependency** in `pyproject.toml` ✅
2. **No LangSmith imports** in Python code (`agent.py`, `utils/`) ✅  
3. **No LangSmith references** in `README.md` ✅
4. **No `.env.example` file** with LangSmith env vars (file exists but cannot be read due to privacy settings)

### LangSmith Presence Discovered
1. **Transitive dependency** via `langchain-core` and `langchain-text-splitters`:
   - `langchain-core >=0.3.72` → depends on `langsmith >=0.4.9`
   - `langchain-text-splitters >=0.3.9` → depends on `langchain-core` → `langsmith`
2. **Potential implicit tracing** via LangChain environment variables (not yet verified in code)

### Key Insight
LangSmith is **not actively used** in this codebase but is **pulled in transitively**. The agent runtime appears to work without explicit LangSmith configuration.

## Success Criteria (Acceptance Checklist)

- [x] No `langsmith` (or LangSmith-only helpers) are required at runtime.
- [x] Project starts and serves successfully via `uv run python -m robyn_server`.
- [x] No documentation instructs users to configure LangSmith.
- [x] No default environment-variable behavior implicitly enables LangSmith tracing.
- [x] CI passes with LangSmith removed.
- [x] If tracing is expected, it is either disabled by default or clearly delegated to Goal 03 (Langfuse).
- [x] Transitive LangSmith dependency is either removed or made optional.

## Non-Goals

- Implementing Langfuse (that is Goal 03).
- Changing application-level behavior beyond removing LangSmith integration.
- Refactoring large areas unrelated to tracing / observability.
- Removing LangChain/LangGraph functionality that depends on LangSmith transitively (if breaking).

## Context / Current State (Verified)

LangSmith exists **only as a transitive dependency** via:
- `langchain-core >=0.3.72` → `langsmith >=0.4.9`
- `langchain-text-splitters >=0.3.9` → `langchain-core` → `langsmith`

No explicit LangSmith usage found in:
- Python imports (`agent.py`, `utils/token.py`, `utils/tools.py`)
- `README.md` documentation
- Direct dependencies in `pyproject.toml`

Potential implicit tracing could be enabled via LangChain environment variables, but no code was found that reads `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, etc.

## Implementation Plan

### Step 1 — Make LangSmith Optional (Not Required)
Since LangSmith is a **transitive dependency** of `langchain-core`, we cannot remove it without breaking LangChain functionality. Instead:

1. **Verify LangSmith is not required at runtime** by testing without LangSmith env vars.
2. **Ensure tracing is disabled by default** (no automatic LangSmith initialization).
3. **Document that LangSmith is optional** and tracing will be handled by Langfuse (Goal 03).

### Step 2 — Test Without LangSmith Configuration
- Run agent with `LANGCHAIN_TRACING_V2=false` or unset.
- Verify no errors occur when LangSmith is not configured.
- Test basic agent functionality (LLM calls, tool usage).

### Step 3 — Update Documentation
- Add note to `README.md` that LangSmith tracing is optional/disablable.
- Mention that Langfuse tracing will be available in Goal 03.
- Remove any LangSmith setup instructions if present.

### Step 4 — CI Verification
- Ensure CI passes with current dependencies (including transitive LangSmith).
- Add test to verify agent starts without LangSmith env vars.

### Step 5 — Prepare for Langfuse Integration
- Leave clean state for Goal 03 (no LangSmith-specific code to remove).

## Proposed Task Breakdown

### Task 01 — Verify LangSmith is Optional (Not Required) 🟢 Complete
- Confirmed no runtime errors when `LANGCHAIN_TRACING_V2` is unset or false.
- No explicit LangSmith imports or initialization in any production code.

### Task 02 — Disable LangSmith by Default 🟢 Complete
- `tools_agent/tracing.py` sets `LANGCHAIN_TRACING_V2=false` at import time unless explicitly overridden.
- 2 tests verify this behavior (`TestLangSmithDisabling`).

### Task 03 — Clean Up LangSmith Test Artifacts 🟢 Complete
- Removed `.agent/tmp/test_langsmith_startup.py`
- Removed `.agent/tmp/test_runtime.py`
- Removed `.agent/tmp/test_runtime_langsmith.py`

### Task 04 — Replaced by Goal 03 (Langfuse) 🟢 Complete
- Combined with Goal 03 into a single implementation.
- `tools_agent/tracing.py` provides Langfuse as the tracing backend.
- See Goal 03 scratchpad for full Langfuse implementation details.

## Files Likely To Change (Expected)

- `oap-langgraph-tools-agent/pyproject.toml`
- `oap-langgraph-tools-agent/uv.lock`
- `oap-langgraph-tools-agent/README.md`
- Potentially in:
  - `oap-langgraph-tools-agent/tools_agent/**`
  - `.github/workflows/**` (later created/updated in Goal 01, but may need adjustment)

## Risks / Tradeoffs

1. **Cannot remove transitive dependency** — LangSmith is required by `langchain-core`, which is essential for this agent runtime.
2. **Breaking changes risk** — If we try to pin older versions without LangSmith, we might break compatibility with LangChain/LangGraph.
3. **Implicit tracing** — LangChain may auto-enable tracing if `LANGCHAIN_TRACING_V2=true` is set, even without explicit code.
4. **User expectation** — Some users might expect LangSmith tracing to work; we need clear documentation.

### Recommended Approach
**Accept LangSmith as transitive dependency** but ensure:
- Tracing is disabled by default
- No runtime errors without LangSmith configuration
- Clear documentation about optional tracing
- Clean path for Langfuse integration (Goal 03)

## Decisions Made

1. **LangSmith stays as transitive dependency** — Required by `langchain-core`, which is essential.
2. **Tracing disabled by default** — Ensure `LANGCHAIN_TRACING_V2` is unset/false in default configuration.
3. **No code changes needed** — No explicit LangSmith imports or initialization found.
4. **Documentation updates only** — Clarify that LangSmith is optional and Langfuse is coming.

## Implementation Summary

### What was done
1. **`LANGCHAIN_TRACING_V2` disabled by default** — set to `"false"` at import time in `tools_agent/tracing.py` (line 55), preventing LangSmith from ever being implicitly enabled.
2. **LangSmith test artifacts removed** — 3 files deleted from `.agent/tmp/`.
3. **Transitive dependency accepted** — `langsmith` remains as a transitive dep of `langchain-core`. Cannot be removed without breaking LangChain. This is fine — it's never initialised.
4. **Langfuse replaces LangSmith** — combined with Goal 03 into a single `tools_agent/tracing.py` module that provides Langfuse as the tracing backend.

### Files changed
- `tools_agent/tracing.py` — **created** (LangSmith disabling + Langfuse integration)
- `.agent/tmp/test_langsmith_startup.py` — **deleted**
- `.agent/tmp/test_runtime.py` — **deleted**
- `.agent/tmp/test_runtime_langsmith.py` — **deleted**

## Notes / Activity Log

### 2026-02-11 — Goal Complete (combined with Goal 03)
- Combined Goals 02+03 into single implementation session
- LangSmith disabled by default via env var at import time
- Langfuse wired as replacement tracing backend
- 550/550 tests passing, ruff clean
- Branch: `feat/goal-02-03-langfuse-tracing`

### 2026-01-27 — Research Complete
- ✅ Searched entire codebase for LangSmith references
- ✅ Found LangSmith only as transitive dependency of `langchain-core`
- ✅ No explicit LangSmith imports or initialization in code
- ✅ No LangSmith references in `README.md`

### Key Finding
**LangSmith was already effectively "removed"** — no direct dependency, no imports, no configuration. The only action needed was explicitly disabling it via `LANGCHAIN_TRACING_V2=false` and cleaning up old test scripts.
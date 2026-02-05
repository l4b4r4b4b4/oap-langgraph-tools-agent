# Goal 02 — Remove LangSmith dependency and integration code

Status: 🟡 In Progress  
Priority: High  
Owner: You  
Last Updated: 2026-01-27 (Research complete, ready for implementation)

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

- [ ] No `langsmith` (or LangSmith-only helpers) are required at runtime.
- [ ] Project starts and serves successfully via `uv run langgraph dev --no-browser`.
- [ ] No documentation instructs users to configure LangSmith.
- [ ] No default environment-variable behavior implicitly enables LangSmith tracing.
- [ ] CI passes with LangSmith removed.
- [ ] If tracing is expected, it is either disabled by default or clearly delegated to Goal 03 (Langfuse).
- [ ] Transitive LangSmith dependency is either removed or made optional.

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

### Task 01 — Verify LangSmith is Optional (Not Required) ⚪ Not Started
- Test agent startup without LangSmith environment variables.
- Verify no runtime errors when `LANGCHAIN_TRACING_V2` is unset or false.
- Check if any code imports or initializes LangSmith explicitly.

### Task 02 — Update Documentation ⚪ Not Started  
- Review `README.md` for any LangSmith references.
- Add note about optional tracing and upcoming Langfuse integration.
- Ensure `.env.example` (if readable) doesn't suggest LangSmith is required.

### Task 03 — CI & Testing ⚪ Not Started
- Run existing CI workflow to verify it passes.
- Add simple test to ensure agent starts without LangSmith config.
- Verify `uv run langgraph dev --no-browser` works.

### Task 04 — Prepare for Goal 03 (Langfuse) ⚪ Not Started
- Document current tracing state (disabled/optional).
- Note any environment variables that affect tracing.
- Create clean baseline for Langfuse integration.

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

## Next Steps

Ready to implement Task 01 (verification) and Task 02 (documentation). Since no code changes are needed beyond documentation, this goal is simpler than expected.

## Files to Review/Update

- `README.md` (if any LangSmith references exist)
- `.env.example` (if readable/contains LangSmith vars)
- CI workflows (no changes needed)
- `pyproject.toml` (no changes needed — keep current dependencies)

## Notes / Activity Log

### 2026-01-27 — Research Complete
- ✅ Searched entire codebase for LangSmith references
- ✅ Found LangSmith only as transitive dependency of `langchain-core`
- ✅ No explicit LangSmith imports or initialization in code
- ✅ No LangSmith references in `README.md`
- ✅ `.env.example` exists but cannot be read (privacy settings)

### Key Finding
**LangSmith is already "removed"** in the sense that:
1. No direct dependency in `pyproject.toml`
2. No imports in Python code  
3. No configuration in visible files
4. Only exists transitively via essential LangChain dependencies

### Implementation Approach
Since LangSmith is not actively used, we simply need to:
1. Verify agent works without LangSmith configuration
2. Update documentation to clarify tracing is optional
3. Prepare clean state for Langfuse (Goal 03)

### Next Action
Proceed with Task 01 verification and Task 02 documentation updates.
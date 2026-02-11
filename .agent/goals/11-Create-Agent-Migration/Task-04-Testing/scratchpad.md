# Task 04: Testing — Full Pipeline Verification

> **Status**: ⚪ Not Started
> **Parent Goal**: [11-Create-Agent-Migration](../scratchpad.md)
> **Depends On**: [Task-03-Streaming-Compatibility](../Task-03-Streaming-Compatibility/scratchpad.md)
> **Created**: 2026-02-11
> **Updated**: 2026-02-11

## Objective

Verify that the complete pipeline works end-to-end after the `create_agent` migration and streaming fixes. This includes automated tests, linting, and manual verification of the Robyn runtime SSE streaming.

## Verification Checklist

### Automated Checks

- [ ] `ruff check . --fix --unsafe-fixes && ruff format .` passes cleanly
- [ ] `pytest` — all existing tests pass (240+ core tests, 28+ OpenAPI tests)
- [ ] No new deprecation warnings from LangChain/LangGraph in test output
- [ ] Import verification script succeeds (see below)

### Import Verification

```python
# Verify all new/migrated imports work
from langchain.agents import create_agent
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.postgres.aio import AsyncPostgresStore
from langgraph.checkpoint.memory import InMemorySaver
import psycopg_pool

# Verify old import still exists (deprecated but should not be removed from langgraph yet)
from langgraph.prebuilt import create_react_agent

# Verify our agent module loads cleanly
from tools_agent.agent import graph, GraphConfigPydantic
```

### Agent Build Verification

Test that the `graph()` factory function produces a valid compiled graph with various configurations:

1. **Standard OpenAI model**: `{"model_name": "openai:gpt-4o"}`
2. **Standard Anthropic model**: `{"model_name": "anthropic:claude-3-5-sonnet-latest"}`
3. **Custom vLLM endpoint**: `{"model_name": "custom:", "base_url": "http://localhost:7374/v1", "custom_model_name": "ministral-3b"}`
4. **With MCP config**: Verify MCP tool loading doesn't error when server unavailable (graceful failure)
5. **With RAG config**: Verify RAG tool creation path (requires Supabase token)

### Streaming Verification

Test that `astream_events(version="v2")` from the new `create_agent` compiled graph emits expected events:

- [ ] `on_chat_model_stream` events fire for token-level streaming
- [ ] `on_chain_end` with `event_name == "model"` fires for completion (not `"agent"`)
- [ ] Event metadata includes `langgraph_node`, `langgraph_step`, `langgraph_checkpoint_ns`
- [ ] Token deltas contain `content` field

### Robyn Runtime Manual Verification

If feasible (requires API keys and running server):

1. Start Robyn server: `uv run python -m robyn_server`
2. Create an assistant via POST `/assistants`
3. Create a thread via POST `/threads`
4. Send a streaming run via POST `/threads/{thread_id}/runs/stream`
5. Verify SSE events arrive in correct order:
   - `event: metadata`
   - `event: values` (initial)
   - `event: messages` (token-level deltas)
   - `event: updates` (final node output)
   - `event: values` (final state)
   - `event: end`

## Test Strategy

### Unit Tests (Automated)

Existing tests in `robyn_server/tests/` should all pass without modification (except `test_streams.py` which may need node name updates per Task-03).

### Smoke Test (Semi-Automated)

Create a minimal smoke test script that:
1. Imports `graph` from `tools_agent.agent`
2. Builds the agent with a mock config
3. Verifies the returned object is a compiled graph
4. Optionally streams a simple message through it (requires API key)

### Integration Test (Manual)

Full Robyn server + streaming test. Only possible with:
- A valid LLM API key (OpenAI or Anthropic)
- The Robyn server running

## Files to Check

| File | What to Verify |
|------|---------------|
| `tools_agent/agent.py` | `graph()` builds successfully with `create_agent` |
| `robyn_server/routes/streams.py` | SSE events emitted correctly with `"model"` node name |
| `robyn_server/routes/sse.py` | SSE formatting utilities unchanged |
| `robyn_server/tests/test_streams.py` | All streaming tests pass |
| `robyn_server/tests/test_runs.py` | All run tests pass |
| `robyn_server/tests/test_app.py` | Health/info endpoints unaffected |
| `robyn_server/tests/test_assistants.py` | Assistant CRUD unaffected |
| `robyn_server/tests/test_threads.py` | Thread CRUD unaffected |

## Acceptance Criteria

- [ ] `ruff check` passes
- [ ] `ruff format` passes (no changes needed)
- [ ] `pytest` passes with 0 failures
- [ ] All new imports verified working
- [ ] `graph()` produces a compiled graph with `create_agent` under the hood
- [ ] No `DeprecationWarning` from our code (warnings from dependencies are acceptable)
- [ ] Streaming node name confirmed as `"model"` in event output
- [ ] Goal 11 scratchpad updated to 🟢 Complete

## Rollback Plan

If critical issues are found that can't be resolved quickly:

1. Revert `agent.py` changes (restore `create_react_agent`)
2. Revert `streams.py` changes (restore `"agent"` node name)
3. Keep package upgrades (they're backward compatible)
4. Document issues in Goal 11 scratchpad for next attempt

## Notes

- The `langgraph-api==0.7.9` pin is used only by the `langgraph dev` runtime path, not by Robyn. If tests pass with Robyn but `langgraph dev` breaks, that's acceptable — Robyn is the production runtime.
- Coverage should remain at ≥73% per project rules. The migration should not reduce coverage since we're changing implementation, not removing tests.
- If any test relies on mocking `create_react_agent` specifically, it needs to be updated to mock `create_agent` instead.
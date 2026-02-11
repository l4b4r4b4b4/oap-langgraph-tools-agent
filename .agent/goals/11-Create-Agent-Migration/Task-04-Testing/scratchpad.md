# Task 04: Testing — Full Pipeline Verification

> **Status**: 🟢 Complete
> **Parent Goal**: [11-Create-Agent-Migration](../scratchpad.md)
> **Depends On**: [Task-03-Streaming-Compatibility](../Task-03-Streaming-Compatibility/scratchpad.md)
> **Created**: 2026-02-11
> **Updated**: 2026-02-11

## Objective

Verify that the complete pipeline works end-to-end after the `create_agent` migration and streaming fixes. This includes automated tests, linting, and manual verification of the Robyn runtime SSE streaming.

## Verification Checklist

### Automated Checks

- [x] `ruff check . --fix --unsafe-fixes && ruff format .` passes cleanly
- [x] `pytest` — all 440 tests pass, 0 failures, 0 errors (1.50s)
- [x] No new deprecation warnings from LangChain/LangGraph in test output (only upstream Pydantic V2 warnings from langsmith)
- [x] Import verification script succeeds (see below)

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

- [x] `on_chat_model_stream` events fire for token-level streaming — confirmed via live SSE stream ("4", ".")
- [x] `on_chat_model_end` fires with `finish_reason: "stop"` and `model_name: "ministral-3b-instruct"`
- [x] Event metadata includes `langgraph_node: "model"`, `langgraph_step`, `langgraph_checkpoint_ns` — confirmed in every messages-tuple event
- [x] Token deltas contain `content` field — confirmed ("4", ".", "")

### Robyn Runtime Manual Verification ✅ COMPLETED

Live-tested with Ministral-3B on local vLLM (port 7374) + Supabase auth (port 54321) + Robyn server (port 8081):

1. ✅ Started Robyn server: `uv run python -m robyn_server` on port 8081
2. ✅ Created assistant via POST `/assistants` — configured for `custom:` endpoint pointing to `http://127.0.0.1:7374/v1` with model `ministral-3b-instruct`
3. ✅ Created thread via POST `/threads`
4. ✅ Sent streaming run via POST `/threads/{thread_id}/runs/stream` with `{"messages": [{"role": "user", "content": "What is 2+2? Be very brief."}]}`
5. ✅ SSE events arrived in correct order:
   - `event: metadata` — `run_id` + `attempt: 1`
   - `event: values` (initial) — human message
   - `event: messages` — initial empty delta with full metadata tuple (`langgraph_node: "model"`)
   - `event: messages` — token `"4"` as delta
   - `event: messages` — token `"."` as delta
   - `event: messages` — final empty delta with `finish_reason: "stop"`, `model_name: "ministral-3b-instruct"`
   - `event: values` (final) — both human + AI messages with complete response `"4."`
6. ✅ Supabase JWT auth verified — `HTTP/1.1 200 OK` from `/auth/v1/user`
7. ✅ Messages-tuple protocol correct — every `event: messages` is `[delta, metadata]` 2-element array

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

- [x] `ruff check` passes
- [x] `ruff format` passes (no changes needed)
- [x] `pytest` passes with 0 failures — 440 passed in 1.50s
- [x] All new imports verified working — `create_agent`, `AsyncPostgresSaver`, `AsyncPostgresStore`, `psycopg_pool`
- [x] `graph()` produces a compiled graph with `create_agent` under the hood — verified via live Ministral streaming
- [x] No `DeprecationWarning` from our code (only upstream Pydantic V2 warnings from langsmith)
- [x] Streaming node name confirmed as `"model"` in event output — `langgraph_node: "model"` in all metadata
- [ ] Goal 11 scratchpad updated to 🟢 Complete — pending this commit

## Rollback Plan

If critical issues are found that can't be resolved quickly:

1. Revert `agent.py` changes (restore `create_react_agent`)
2. Revert `streams.py` changes (restore `"agent"` node name)
3. Keep package upgrades (they're backward compatible)
4. Document issues in Goal 11 scratchpad for next attempt

## Notes

- The `langgraph-api==0.7.9` pin was removed from runtime deps entirely (no imports existed). Dev dep `langgraph-cli[inmem]` still provides it for `langgraph dev` workflow.
- Coverage should remain at ≥73% per project rules. The migration should not reduce coverage since we're changing implementation, not removing tests.
- No tests relied on mocking `create_react_agent` specifically — all agent tests use higher-level mocks of the compiled graph.
- The `event: updates` event did not fire in the simple no-tool-call case. This is expected — it fires on `on_chain_end` with `event_name == "model"`, which may not emit in all graph execution paths. The `event: values` (final) carries the complete state regardless.

## Completion Log

### Live Test Details (2026-02-11)

**Infrastructure:**
- Ministral-3B via vLLM (docker-compose `ministral` service) on `http://127.0.0.1:7374/v1`
- Supabase local dev stack on `http://127.0.0.1:54321`
- Robyn server on `http://127.0.0.1:8081`

**Test flow:**
1. Created test user via Supabase Auth signup → got JWT token
2. Created assistant with `custom:` model pointing to local Ministral
3. Created thread
4. Streamed run with `"What is 2+2? Be very brief."`
5. Ministral responded `"4."` — streamed token-by-token as SSE messages-tuple events
6. Full SSE event sequence verified correct

**Verified:**
- `create_agent` migration works end-to-end (agent builds, streams, produces correct output)
- Streaming node name `"model"` correctly appears in all metadata (not `"agent"`)
- Messages-tuple protocol intact — `[delta, metadata]` format in every `event: messages`
- Custom vLLM endpoint routing works via `base_url` config
- Supabase JWT authentication works through the full chain
- Final `event: values` contains complete conversation state

### What was NOT tested (out of scope for Task-04)
- Standard provider models (OpenAI, Anthropic) — requires API keys, but code path is identical
- MCP tool loading — requires running MCP server
- RAG tool loading — requires Supabase RAG endpoint + collections
- `langgraph dev` runtime — deprecated path, Robyn is primary
# Task 02: LangGraph Checkpointer + Store Integration

> **Status**: ⚪ Not Started
> **Parent Goal**: [12-Postgres-Persistence](../scratchpad.md)
> **Depends On**: [Task-01-Dependencies-DB-Module](../Task-01-Dependencies-DB-Module/scratchpad.md)
> **Created**: 2026-02-11
> **Updated**: 2026-02-11

## Objective

Wire `AsyncPostgresSaver` (checkpointer) and `AsyncPostgresStore` (cross-thread memory) into the agent compilation pipeline so that conversation state persists across server restarts and cross-thread memory is available for long-term user context. This is the core integration that gives the agent durable memory.

## Background

### What the Checkpointer Does

The LangGraph checkpointer saves a **checkpoint of the graph state at every super-step**. These checkpoints are saved to a **thread**, enabling:

- **Short-term memory**: Multi-turn conversation history within a thread
- **Thread history**: Full state history accessible via `graph.get_state_history()`
- **Time travel**: Resume from any previous checkpoint
- **Fault tolerance**: Resume interrupted runs from last checkpoint
- **Human-in-the-loop**: Interrupt execution, inspect state, resume

### What the Store Does

The LangGraph store provides **cross-thread persistence** — data that spans multiple conversations:

- **Long-term memory**: User preferences, facts, learned context
- **Namespaced storage**: Data organized by `(user_id, "memories")` tuples
- **Semantic search**: Optional vector search over stored items
- **Cross-thread access**: Any thread can read/write the same namespace

### Current State

The agent in `tools_agent/agent.py` currently returns a compiled graph with **no checkpointer and no store**:

```python
return create_agent(
    model=model,
    tools=tools,
    system_prompt=cfg.system_prompt + UNEDITABLE_SYSTEM_PROMPT,
)
```

Every invocation is stateless — the agent has no memory of previous messages in the same thread.

## Implementation Plan

### Step 1: Modify `tools_agent/agent.py` — Accept checkpointer and store

The `graph()` function needs to accept (or retrieve) the checkpointer and store, then pass them to `create_agent`:

```python
from robyn_server.database import get_checkpointer, get_store, is_postgres_enabled

async def graph(config: RunnableConfig):
    # ... existing config parsing, model init, tool loading ...

    # Get persistence components (None if DATABASE_URL not set)
    checkpointer = get_checkpointer()
    store = get_store()

    return create_agent(
        model=model,
        tools=tools,
        system_prompt=cfg.system_prompt + UNEDITABLE_SYSTEM_PROMPT,
        checkpointer=checkpointer,  # None = no persistence (in-memory mode)
        store=store,                # None = no cross-thread memory
    )
```

**Key consideration**: `create_agent` accepts `checkpointer=None` gracefully — it simply doesn't checkpoint. So the in-memory fallback path requires zero special handling.

### Step 2: Verify `thread_id` propagation

For the checkpointer to work, every invocation must include a `thread_id` in the config:

```python
config = {"configurable": {"thread_id": "some-thread-id"}}
```

This is already handled by the Robyn runtime — `streams.py` builds a `RunnableConfig` with `thread_id` from the HTTP request path parameter. Verify that:

1. `_build_runnable_config()` in `streams.py` sets `thread_id` in `configurable`
2. The `thread_id` from the URL path (`/threads/{thread_id}/runs/stream`) flows through correctly

### Step 3: Handle agent compilation lifecycle

**Important architectural consideration**: Currently `graph()` is called on **every run request** — it builds a fresh agent each time. With a checkpointer, the agent graph should ideally be compiled once and reused (the checkpointer handles per-thread isolation via `thread_id`).

However, our `graph()` function does dynamic work per-request:
- Different models per assistant config
- Different tools per MCP/RAG config
- Different system prompts per assistant

**Options**:

A. **Keep per-request compilation** (simplest, current approach):
   - Pass checkpointer/store to each `create_agent` call
   - The checkpointer is stateless itself — it's just a gateway to Postgres
   - Slight overhead of graph compilation per request, but functionally correct
   - ✅ **Recommended for now** — minimal change, works correctly

B. **Cache compiled graphs by assistant config** (optimization):
   - Cache compiled graphs keyed by (model_name, tools_hash, system_prompt_hash)
   - Invalidate on assistant config change
   - More complex, premature optimization
   - ❌ Defer to future enhancement

### Step 4: Handle `astream_events` with checkpointer

When a checkpointer is present, `astream_events()` behavior changes subtly:
- Checkpoints are written after each super-step
- The `thread_id` in config determines which thread state is loaded/saved
- Previous messages are automatically loaded from the checkpoint at invocation start

**Impact on `streams.py`**: The `execute_run_stream()` function currently constructs `input_messages` from the HTTP request body and passes them as `{"messages": input_messages}` to the agent. With a checkpointer:

- The agent automatically loads the previous thread state (including old messages)
- Only the **new** user message should be passed as input
- The previous messages are already in the checkpoint

This should work correctly as-is because we only pass the current request's messages as input, not the full history. The checkpointer handles prepending historical messages.

**Verify**: That `astream_events` doesn't duplicate messages (new input + checkpoint history).

### Step 5: Thread state API integration

With a checkpointer, the Robyn runtime can expose richer thread state APIs:

- `GET /threads/{thread_id}/state` — can now return real checkpoint state via `graph.aget_state(config)`
- `GET /threads/{thread_id}/history` — can now return real state history via `graph.aget_state_history(config)`

Currently these endpoints return mock/in-memory state from `ThreadStore`. With a checkpointer, they could delegate to the actual LangGraph checkpoint. This is an enhancement beyond the minimum viable integration but worth noting.

**Minimum viable**: Just wire checkpointer into `create_agent`. The thread state/history API enhancement can be a follow-up.

## Files to Modify

| File | Changes |
|------|---------|
| `tools_agent/agent.py` | Import `get_checkpointer`, `get_store`, `is_postgres_enabled`; pass `checkpointer` and `store` to `create_agent()` |
| `robyn_server/routes/streams.py` | Verify `thread_id` propagation in `_build_runnable_config()`; potentially adjust message handling for checkpointed runs |

## Dependencies

- Task-01 must be complete (`database.py` module with `get_checkpointer()`, `get_store()`)
- Goal 11 must be complete (`create_agent` migration)
- A running Postgres instance (Supabase local stack) for testing

## Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Message duplication with checkpointer (input + checkpoint history) | High | Medium | Test carefully; verify `astream_events` output with checkpointer enabled |
| Checkpointer slows down agent invocation (DB write per super-step) | Medium | Low | Postgres is fast for small writes; monitor latency |
| `graph()` per-request compilation is incompatible with checkpointer state | Medium | Low | Checkpointer is stateless gateway — safe to create new graph instances that share it |
| Import cycle: `tools_agent.agent` → `robyn_server.database` | Medium | Medium | Consider passing checkpointer/store via config or function args instead of direct import |
| `create_agent` doesn't support `checkpointer=None` gracefully | Low | Low | Verified via introspection — it's an optional parameter |

## Acceptance Criteria

- [ ] `tools_agent/agent.py` passes `checkpointer` and `store` to `create_agent()`
- [ ] When `DATABASE_URL` is set: conversation state persists across server restarts
- [ ] When `DATABASE_URL` is NOT set: agent works identically to before (no persistence, no errors)
- [ ] `thread_id` correctly flows from HTTP request → `RunnableConfig` → checkpointer
- [ ] Multi-turn conversation memory works:
  - Message 1: "My name is Alice" → agent responds
  - Message 2 (same thread): "What's my name?" → agent knows "Alice"
- [ ] Different threads are isolated (thread A doesn't see thread B's messages)
- [ ] LangGraph checkpoint tables exist in Postgres after `.setup()` runs
- [ ] No message duplication in streaming output
- [ ] `ruff check` and `ruff format` pass
- [ ] Existing tests pass

## Verification Script

```python
# Quick smoke test for checkpointer integration
import asyncio
from langchain_core.runnables import RunnableConfig

async def test_persistence():
    from tools_agent.agent import graph

    # Build agent with minimal config (requires OPENAI_API_KEY)
    config: RunnableConfig = {
        "configurable": {
            "thread_id": "test-thread-001",
            "model_name": "openai:gpt-4o-mini",
        }
    }

    agent = await graph(config)

    # First message
    result1 = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "Hi! My name is Alice."}]},
        config,
    )
    print("Turn 1:", result1["messages"][-1].content)

    # Second message — same thread, should remember name
    result2 = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "What's my name?"}]},
        config,
    )
    print("Turn 2:", result2["messages"][-1].content)
    assert "Alice" in result2["messages"][-1].content

asyncio.run(test_persistence())
```

## Notes

- The `AsyncPostgresSaver` uses its own internal `psycopg_pool.AsyncConnectionPool`. Even though we create a shared pool in `database.py`, the checkpointer manages its own connections via `from_conn_string()`. This means slightly more connections to Postgres than strictly necessary, but it's the simplest and most maintainable approach. Sharing a pool requires using the lower-level `AsyncPostgresSaver(conn=...)` constructor which is more complex.
- The cross-thread `AsyncPostgresStore` enables future features like user-scoped memories, preferences, and knowledge that persists across all conversations. For the minimum viable integration, we wire it in but don't add store-writing logic to the agent nodes. That can be a future enhancement (e.g., a "remember this" tool).
- The import cycle risk (`tools_agent` → `robyn_server`) is real. If it causes issues, the cleanest solution is to pass checkpointer/store as arguments to `graph()` or via the `RunnableConfig` configurable dict, rather than importing from `robyn_server.database` directly.
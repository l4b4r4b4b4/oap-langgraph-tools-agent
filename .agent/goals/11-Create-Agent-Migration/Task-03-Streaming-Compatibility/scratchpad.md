# Task 03: Streaming Compatibility — Fix Node Name References

> **Status**: ⚪ Not Started
> **Parent Goal**: [11-Create-Agent-Migration](../scratchpad.md)
> **Depends On**: [Task-02-Agent-Migration](../Task-02-Agent-Migration/scratchpad.md)
> **Created**: 2026-02-11
> **Updated**: 2026-02-11

## Objective

Update all streaming node name references in `robyn_server/routes/streams.py` (and related files) from `"agent"` to `"model"` to reflect the node naming change in `create_agent` vs `create_react_agent`. This is a **breaking change** in the internal graph structure that will silently break SSE streaming if not addressed.

## Background

When migrating from `create_react_agent` to `create_agent`, the internal graph node that calls the LLM changes its name:

- **Old** (`create_react_agent`): The LLM-calling node is named `"agent"`
- **New** (`create_agent`): The LLM-calling node is named `"model"`

This affects `astream_events()` output, which our `streams.py` uses to detect event boundaries and emit properly formatted SSE events to the frontend.

## Impact Analysis

### `robyn_server/routes/streams.py` — Known References

The `execute_run_stream()` function in `streams.py` uses event names from `astream_events()` to detect:

1. **Chain/graph end events**: `event_kind == "on_chain_end" and event_name == "agent"` — used to emit `updates` SSE events with final agent output
2. **Metadata construction**: `"langgraph_node": event_metadata.get("langgraph_node", "agent")` — default fallback value
3. **Graph ID references**: `"graph_id": "agent"` — metadata field (this may be a semantic label, not a node name)

### Other Potentially Affected Files

Need to grep for all `"agent"` references that could be node name dependent:

- `robyn_server/routes/sse.py` — SSE event formatting utilities
- `robyn_server/routes/streams.py` — primary target
- `robyn_server/tests/test_streams.py` — test assertions may reference `"agent"` node name
- `robyn_server/tests/test_runs.py` — run tests may reference agent node names

## Implementation Plan

### Step 1: Comprehensive grep for affected references

Search for all `"agent"` string references in the streaming and SSE code paths. Distinguish between:

- **Node name references** (must change to `"model"`) — e.g., `event_name == "agent"`
- **Semantic labels** (keep as `"agent"`) — e.g., `"graph_id": "agent"`, `"assistant_id": assistant_id`
- **Unrelated uses** (keep as-is) — e.g., log messages, error codes

### Step 2: Update node name references in `streams.py`

```python
# OLD — detecting chain end for the agent node
elif event_kind == "on_chain_end" and event_name == "agent":

# NEW — the model node in create_agent
elif event_kind == "on_chain_end" and event_name == "model":
```

```python
# OLD — metadata default fallback
"langgraph_node": event_metadata.get("langgraph_node", "agent"),

# NEW
"langgraph_node": event_metadata.get("langgraph_node", "model"),
```

### Step 3: Evaluate `"graph_id": "agent"` references

The `graph_id` in metadata is a **semantic identifier** for the overall graph, not a node name. It likely should stay as `"agent"` since it describes what the graph _is_, not the node. However, verify what the LangGraph SDK/frontend expects.

### Step 4: Update test assertions

Any test in `test_streams.py` or `test_runs.py` that asserts on `"agent"` as a node name in event data must be updated.

### Step 5: Verify `astream_events` format

Run the agent with `create_agent` and inspect the raw events from `astream_events(version="v2")` to confirm:

- The node name for LLM calls is indeed `"model"`
- The event structure (event_kind, event_name, event_data) is otherwise unchanged
- `on_chat_model_stream` events still fire for token-level streaming
- `on_chain_end` with the new node name fires for completion

## Files to Modify

| File | Changes |
|------|---------|
| `robyn_server/routes/streams.py` | Node name `"agent"` → `"model"` in event detection logic and metadata defaults |
| `robyn_server/routes/sse.py` | Check for any node name references (likely none) |
| `robyn_server/tests/test_streams.py` | Update test assertions for node names |
| `robyn_server/tests/test_runs.py` | Check for node name references in test data |

## Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Silent SSE streaming breakage if node name not updated | **Critical** | **Certain** (if Task-02 done without Task-03) | This task MUST be done together with or immediately after Task-02 |
| `astream_events` v2 format changed beyond node naming | Medium | Low | Inspect raw events during testing |
| Frontend (CopilotKit/OAP) parses metadata node names | Medium | Low | The frontend should not depend on internal node names; verify |
| Some `"agent"` references are semantic and should NOT change | Medium | Medium | Careful grep analysis distinguishing node names from labels |

## Acceptance Criteria

- [ ] All `event_name == "agent"` references updated to `"model"` in `streams.py`
- [ ] Metadata default `"langgraph_node"` fallback updated to `"model"`
- [ ] `"graph_id": "agent"` references evaluated and documented (keep or change)
- [ ] Test assertions updated for new node name
- [ ] SSE streaming produces correct events end-to-end:
  - `event: metadata` — emitted first
  - `event: values` — initial values
  - `event: messages/partial` or `event: messages` — token-level streaming
  - `event: updates` — final node output
  - `event: values` — final state
  - `event: end` — stream end
- [ ] No regressions in `pytest` for streaming tests
- [ ] Manual verification: start Robyn server, send a chat message, confirm SSE stream completes

## Notes

- The `on_chat_model_stream` events (token-level) are **not** affected by this change — they come from the chat model, not the graph node. Token streaming should continue to work without changes.
- The `messages` tuple protocol (Goal 10) uses `current_metadata` which includes `langgraph_node` — this metadata flows through to the frontend and affects how messages are attributed. The default fallback should match the actual node name.
- Consider adding a constant (e.g., `AGENT_NODE_NAME = "model"`) to avoid string literals scattered through the code. This would make future changes easier if the node name changes again.
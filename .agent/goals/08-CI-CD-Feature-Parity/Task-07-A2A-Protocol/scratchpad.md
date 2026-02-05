# Task 07 — A2A Protocol Implementation

> Implement the Agent-to-Agent (A2A) Protocol endpoint for inter-agent communication using JSON-RPC 2.0.

---

## Status: 🟢 Complete

**Started:** 2026-02-05
**Completed:** 2026-02-05
**Branch:** `feature/a2a-protocol`

---

## Objective

Implement the A2A (Agent-to-Agent) Protocol according to the Google A2A specification, enabling external agents to communicate with our LangGraph agent using a standardized JSON-RPC 2.0 interface.

---

## API Specification

### Endpoint

`POST /a2a/{assistant_id}` - JSON-RPC 2.0 message handler

### Supported Methods

| Method | Description | Maps To |
|--------|-------------|---------|
| `message/send` | Send message, wait for result | `/runs/wait` (synchronous) |
| `message/stream` | Send message, stream response | `/runs/stream` (SSE) |
| `tasks/get` | Get task status by ID | Run status retrieval |
| `tasks/cancel` | Cancel a task | Returns error (not supported) |

### Key Mappings (A2A → LangGraph)

- `message.contextId` → `thread_id`
- `message.messageId` → tracked for response correlation
- `message.taskId` → `run_id` (for resuming interrupted tasks)
- `message.parts[].text` → `input.messages` content
- `message.parts[].data` → merged into assistant input
- A2A `Task` → wraps LangGraph run with artifacts

### Request Schema

```json
{
  "jsonrpc": "2.0",
  "id": "request-id",
  "method": "message/send|message/stream|tasks/get|tasks/cancel",
  "params": {
    "message": {
      "role": "user|agent",
      "parts": [
        {"kind": "text", "text": "..."},
        {"kind": "data", "data": {...}}
      ],
      "messageId": "msg-uuid",
      "contextId": "thread-uuid",
      "taskId": "task-id (optional)"
    }
  }
}
```

### Response Schema

```json
{
  "jsonrpc": "2.0",
  "id": "request-id",
  "result": {
    "kind": "task",
    "id": "task-id",
    "contextId": "thread-uuid",
    "status": {"state": "completed|working|input-required|failed"},
    "artifacts": [
      {
        "artifactId": "uuid",
        "name": "Assistant Response",
        "parts": [{"kind": "text", "text": "..."}]
      }
    ]
  }
}
```

---

## Implementation Plan

### File Structure

```
robyn_server/
├── a2a/
│   ├── __init__.py      # Module exports
│   ├── schemas.py       # Pydantic models for A2A
│   └── handlers.py      # Method handlers
├── routes/
│   └── a2a.py           # HTTP route handler
└── tests/
    └── test_a2a.py      # Comprehensive tests
```

### Implementation Steps

1. [x] Create `robyn_server/a2a/schemas.py`
   - JSON-RPC request/response models (reuse from MCP where possible)
   - A2A-specific models: Message, Part, Task, Artifact, Status
   - Parameter models for each method

2. [x] Create `robyn_server/a2a/handlers.py`
   - `A2AHandler` class with method dispatch
   - `handle_message_send()` - sync execution via runs
   - `handle_message_stream()` - SSE streaming
   - `handle_tasks_get()` - retrieve task/run status
   - `handle_tasks_cancel()` - return not-supported error

3. [x] Create `robyn_server/a2a/__init__.py`
   - Export public interface

4. [x] Create `robyn_server/routes/a2a.py`
   - `POST /a2a/{assistant_id}` route handler
   - Accept header validation (application/json or text/event-stream)
   - JSON-RPC parsing and error handling

5. [x] Register routes in `robyn_server/app.py`
   - Import and register A2A routes
   - Update `/info` endpoint: `capabilities.a2a = true`

6. [x] Update OpenAPI spec
   - Add A2A endpoint documentation
   - Add A2A schemas

7. [x] Create `robyn_server/tests/test_a2a.py`
   - Schema validation tests
   - Handler unit tests
   - Route integration tests
   - Error handling tests

---

## Design Decisions

### 1. Reuse JSON-RPC Infrastructure from MCP

The MCP implementation already has JSON-RPC 2.0 infrastructure. We can:
- Reuse `JsonRpcRequest`, `JsonRpcResponse`, `JsonRpcError` base schemas
- Reuse error code definitions
- Follow same handler pattern

### 2. Task ID Format

A2A uses `taskId` which maps to LangGraph runs. Format: `{thread_id}:{run_id}`
- Allows reconstruction of both IDs from single identifier
- Matches LangGraph's thread+run model

### 3. Message Parts Handling

Only `text` and `data` parts supported (per LangGraph spec):
- `text` parts → concatenated into `messages` input
- `data` parts → merged into assistant input object
- `file` parts → return error (not supported)

### 4. Streaming via SSE

For `message/stream`, use existing SSE infrastructure:
- Reuse `robyn_server/routes/sse.py` utilities
- Return `text/event-stream` content type
- Each SSE event contains JSON-RPC response envelope

### 5. Thread Creation

If `contextId` is omitted:
- Create new thread automatically
- Return new `contextId` in response

---

## Test Strategy

### Unit Tests (schemas.py)
- [x] A2A message parsing
- [x] Part type validation (text, data, reject file)
- [x] Task status mapping
- [x] Artifact construction

### Unit Tests (handlers.py)
- [x] message/send dispatches to run execution
- [x] message/stream sets up SSE
- [x] tasks/get retrieves run status
- [x] tasks/cancel returns proper error

### Integration Tests (routes)
- [x] Valid message/send returns task result
- [x] Invalid JSON returns parse error
- [x] Missing required fields return validation error
- [x] Unknown method returns method-not-found error
- [x] Missing assistant returns 404

### Edge Cases
- [x] Empty parts array
- [x] Mixed text and data parts
- [x] Missing contextId (auto-create thread)
- [x] Task resumption with taskId

---

## Success Criteria

- [x] All 4 A2A methods implemented (send, stream, get, cancel)
- [x] JSON-RPC 2.0 compliant responses
- [x] Proper error codes for all failure modes
- [x] SSE streaming works for message/stream
- [x] Tests achieve ≥90% coverage for A2A module (70 tests)
- [x] OpenAPI spec updated
- [x] `/info` shows `capabilities.a2a = true`

---

## References

- [A2A Protocol Spec](https://github.com/google/a2a-spec)
- [LangGraph A2A Endpoint](../.agent/tmp/langgraph-serve_openape_spec.json#L2737-3119)
- [MCP Implementation](../Task-08-MCP-Protocol/scratchpad.md) - reference for JSON-RPC pattern
- [JSON-RPC 2.0 Spec](https://www.jsonrpc.org/specification)

---

## Progress Log

### 2026-02-05
- Created task scratchpad
- Analyzed LangGraph OpenAPI spec for A2A endpoint
- Identified mapping between A2A concepts and LangGraph APIs
- Implemented A2A module:
  - `robyn_server/a2a/schemas.py` - 379 lines: JSON-RPC 2.0 + A2A models
  - `robyn_server/a2a/handlers.py` - 588 lines: Method handlers with agent execution
  - `robyn_server/a2a/__init__.py` - 94 lines: Public exports
  - `robyn_server/routes/a2a.py` - 232 lines: HTTP route handler
  - `robyn_server/tests/test_a2a.py` - 1000+ lines: 70 comprehensive tests
- Updated `robyn_server/app.py` to register A2A routes
- Updated `robyn_server/openapi_spec.py` with A2A tag and endpoint documentation
- Updated `/info` endpoint: `capabilities.a2a = true`
- All 368 tests passing in robyn_server/ (70 new A2A tests)

### Files Created
- `robyn_server/a2a/__init__.py`
- `robyn_server/a2a/schemas.py`
- `robyn_server/a2a/handlers.py`
- `robyn_server/routes/a2a.py`
- `robyn_server/tests/test_a2a.py`

### Files Modified
- `robyn_server/app.py` - Added A2A route registration, updated /info capabilities
- `robyn_server/openapi_spec.py` - Added A2A tag and endpoint documentation
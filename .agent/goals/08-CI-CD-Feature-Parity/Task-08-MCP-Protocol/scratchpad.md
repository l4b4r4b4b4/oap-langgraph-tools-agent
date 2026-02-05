# Task 08 — Implement MCP Protocol Endpoints

> Expose the LangGraph agent as an MCP (Model Context Protocol) server for integration with MCP clients like Claude Desktop, Cursor, etc.

---

## Objective

Implement the MCP Protocol endpoints to match LangGraph FastAPI's specification:
- `POST /mcp/` - JSON-RPC 2.0 message endpoint (Streamable HTTP Transport)
- `GET /mcp/` - Returns 405 (streaming not supported)
- `DELETE /mcp/` - Returns 404 (stateless, no session to terminate)

---

## Research Summary

### LangGraph MCP Spec (from OpenAPI)

```json
{
  "/mcp/": {
    "post": {
      "operationId": "post_mcp",
      "summary": "MCP Post",
      "description": "Implemented according to the Streamable HTTP Transport specification.\nSends a JSON-RPC 2.0 message to the server.",
      "parameters": [
        {
          "name": "Accept",
          "in": "header",
          "required": true,
          "schema": { "type": "string", "enum": ["application/json, text/event-stream"] }
        }
      ],
      "requestBody": {
        "required": true,
        "content": { "application/json": { "schema": { "type": "object" } } }
      },
      "responses": {
        "200": { "description": "Successful JSON-RPC response" },
        "202": { "description": "Notification accepted; no content body" },
        "400": { "description": "Bad request" },
        "405": { "description": "HTTP method not allowed" },
        "500": { "description": "Internal server error" }
      }
    },
    "get": {
      "operationId": "get_mcp",
      "responses": { "405": { "description": "GET method not allowed" } }
    },
    "delete": {
      "operationId": "delete_mcp",
      "responses": { "404": { "description": "Session not found" } }
    }
  }
}
```

### MCP Protocol Overview

**Model Context Protocol (MCP)** is a JSON-RPC 2.0 based protocol for LLM tool integration.

Key MCP Methods:
- `initialize` - Client handshake with capabilities
- `tools/list` - List available tools
- `tools/call` - Execute a tool
- `prompts/list` - List available prompts (optional)
- `resources/list` - List available resources (optional)

### Implementation Approach

Since LangGraph's MCP implementation is **stateless** and uses **Streamable HTTP Transport**:
1. No session management needed
2. Each request is independent
3. Support both JSON response and SSE streaming via Accept header

---

## Implementation Plan

### Files to Create/Modify

1. **New:** `robyn_server/routes/mcp.py` - MCP route handlers
2. **New:** `robyn_server/mcp/__init__.py` - MCP module
3. **New:** `robyn_server/mcp/handlers.py` - JSON-RPC method handlers
4. **New:** `robyn_server/mcp/schemas.py` - Request/Response Pydantic models
5. **Modify:** `robyn_server/app.py` - Register MCP routes
6. **Modify:** `robyn_server/openapi_spec.py` - Add MCP endpoints to spec
7. **New:** `robyn_server/tests/test_mcp.py` - MCP endpoint tests

### Phase 1: Basic Endpoint Structure
- [ ] Create `/mcp/` POST endpoint (returns 501 Not Implemented initially)
- [ ] Create `/mcp/` GET endpoint (returns 405)
- [ ] Create `/mcp/` DELETE endpoint (returns 404)
- [ ] Add to OpenAPI spec
- [ ] Basic tests for HTTP methods

### Phase 2: JSON-RPC Infrastructure
- [ ] Create JSON-RPC 2.0 request/response models
- [ ] Implement error handling (parse error, invalid request, method not found)
- [ ] Create method dispatcher

### Phase 3: MCP Methods
- [ ] `initialize` - Return server capabilities
- [ ] `tools/list` - List LangGraph agent as a tool
- [ ] `tools/call` - Execute agent run and return result

### Phase 4: Agent Integration
- [ ] Map MCP tool calls to LangGraph runs
- [ ] Handle async execution
- [ ] Support streaming responses (SSE)

---

## MCP Tool Design

The LangGraph agent will be exposed as a single MCP tool:

```json
{
  "name": "langgraph_agent",
  "description": "Execute the LangGraph agent with a message",
  "inputSchema": {
    "type": "object",
    "properties": {
      "message": { "type": "string", "description": "User message to send to the agent" },
      "thread_id": { "type": "string", "description": "Optional thread ID for conversation continuity" }
    },
    "required": ["message"]
  }
}
```

---

## JSON-RPC 2.0 Structure

### Request
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "tools/call",
  "params": { ... }
}
```

### Response (Success)
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "result": { ... }
}
```

### Response (Error)
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "error": {
    "code": -32600,
    "message": "Invalid Request"
  }
}
```

### Standard Error Codes
- `-32700` - Parse error
- `-32600` - Invalid Request
- `-32601` - Method not found
- `-32602` - Invalid params
- `-32603` - Internal error

---

## Success Criteria

- [ ] All MCP endpoints return correct HTTP status codes
- [ ] JSON-RPC 2.0 protocol compliance
- [ ] `initialize` returns server capabilities
- [ ] `tools/list` returns the LangGraph agent tool
- [ ] `tools/call` executes agent and returns result
- [ ] OpenAPI spec includes MCP endpoints
- [ ] Tests pass with ≥80% coverage for MCP module
- [ ] `/info` endpoint shows `"mcp": true` in capabilities

---

## Notes

- MCP is stateless per LangGraph spec - no session persistence
- Start simple: basic tool execution, add streaming later
- Consider rate limiting for tool calls in production
- MCP clients expect specific error formats - test with real clients

---

## Progress

- [ ] Phase 1: Basic Endpoint Structure
- [ ] Phase 2: JSON-RPC Infrastructure  
- [ ] Phase 3: MCP Methods
- [ ] Phase 4: Agent Integration
- [ ] Tests written and passing
- [ ] Documentation updated
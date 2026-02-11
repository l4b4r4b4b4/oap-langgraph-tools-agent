# Goal 13: MCP Agent Integration

> **Status**: ⚪ Not Started
> **Priority**: P2 (Medium)
> **Created**: 2026-02-11
> **Updated**: 2026-02-11
> **Depends On**: Goal 12 (Postgres Persistence)

## Overview

Deepen the MCP (Model Context Protocol) integration in both directions: improve how the agent **consumes** tools from remote MCP servers (client side), and complete the implementation that **exposes** the agent as an MCP server (server side). Currently both sides exist but have significant gaps — the client does manual tool wrapping with no connection reuse, and the server is a skeleton with a placeholder agent execution path.

## Current State

### MCP Client (agent consumes tools from remote MCP servers)

**Location**: `tools_agent/agent.py`, `tools_agent/utils/tools.py`, `tools_agent/utils/token.py`

**How it works today**:
1. `graph()` reads `MCPConfig` from assistant configurable (url, tools list, auth_required)
2. Opens a `streamablehttp_client` connection to `{mcp_url}/mcp`
3. Lists all tools, filters by name, wraps each as a LangChain `StructuredTool`
4. Each tool invocation opens a **new** `streamablehttp_client` connection (no reuse)
5. Auth: optional Supabase token → MCP OAuth token exchange via `/oauth/token`
6. Errors silently swallowed with `logger.warning`

**Problems**:
- **No connection reuse** — every tool call opens a new HTTP connection + MCP session
- **Single MCP server** — `MCPConfig` only supports one `url` field
- **Manual tool wrapping** — reimplements what LangChain may now provide natively
- **No tool caching** — tool list fetched fresh on every `graph()` invocation
- **Fragile error handling** — MCP connection failures silently drop all tools
- **No health checking** — no way to know if an MCP server is reachable before invocation

### MCP Server (agent exposed as MCP server)

**Location**: `robyn_server/mcp/handlers.py`, `robyn_server/mcp/schemas.py`, `robyn_server/routes/mcp.py`

**How it works today**:
1. Robyn registers POST/GET/DELETE `/mcp/` routes
2. `McpMethodHandler` implements JSON-RPC 2.0 for `initialize`, `tools/list`, `tools/call`, `ping`
3. Exposes a single hardcoded `langgraph_agent` tool
4. `tools/call` tries to import `robyn_server.agent.execute_agent_run` — **this module doesn't exist** (falls back to placeholder)
5. No streaming support (GET returns 405)
6. Stateless — no session management

**Problems**:
- **Agent execution not wired** — `execute_agent_run` import fails, returns placeholder
- **No streaming** — MCP supports SSE streaming but server returns 405 on GET
- **Hardcoded single tool** — only exposes `langgraph_agent`, doesn't reflect actual agent capabilities
- **No auth** — MCP endpoint skips Supabase auth (it's registered but public paths don't include it... actually it's NOT in PUBLIC_PATHS so it does require auth)
- **No dynamic tool discovery** — doesn't expose the agent's sub-tools (MCP tools, RAG tools) as individual MCP tools

## Success Criteria

- [ ] MCP client: connection pooling / session reuse for tool invocations
- [ ] MCP client: support multiple MCP servers per agent (list of URLs)
- [ ] MCP client: evaluate and adopt LangChain native MCP tool integration if available
- [ ] MCP client: graceful degradation with clear error messages per server
- [ ] MCP server: wire `tools/call` to actual agent execution via `graph()`
- [ ] MCP server: support SSE streaming for `tools/call` responses
- [ ] MCP server: dynamic tool listing that reflects agent's actual capabilities
- [ ] MCP server: proper integration with Supabase auth context
- [ ] All existing tests pass
- [ ] New tests for MCP client connection reuse and multi-server support
- [ ] New tests for MCP server agent execution

## Proposed Tasks

| Task ID | Description | Status | Depends On |
|---------|-------------|--------|------------|
| Task-01 | Research — LangChain native MCP support, connection pooling patterns, multi-server config | ⚪ | - |
| Task-02 | MCP Client Improvements — connection reuse, multi-server, error handling | ⚪ | Task-01 |
| Task-03 | MCP Server Completion — wire agent execution, streaming, dynamic tools | ⚪ | Task-01 |
| Task-04 | Testing — unit tests for both sides, integration test with live MCP server | ⚪ | Task-02, Task-03 |

> **Note**: Task breakdown is preliminary. Full research (Task-01) will refine scope and may split/merge tasks.

## Architecture Considerations

### MCP Client — Connection Reuse

Currently each tool call creates a fresh connection:
```python
# Current: new connection per invocation (in tools.py)
async def new_tool(**kwargs):
    async with streamablehttp_client(mcp_server_url, headers=headers) as streams:
        ...  # opens and closes connection every time
```

Options:
1. **Connection pool** — maintain a pool of MCP sessions per server URL
2. **Session-per-graph** — keep the MCP session alive for the lifetime of `graph()` execution
3. **LangChain native** — if LangChain v1 has built-in MCP tool support, it may handle this

### MCP Client — Multi-Server

Current `MCPConfig` supports a single URL. Options:
1. Change `url: str` to `urls: list[str]` (breaking change to config schema)
2. Change `mcp_config: MCPConfig` to `mcp_configs: list[MCPConfig]` (supports per-server auth)
3. Keep single `mcp_config` but add `additional_mcp_servers: list[MCPConfig]`

Option 2 is cleanest but requires OAP UI changes.

### MCP Server — Agent Execution

The `execute_agent_run` function needs to:
1. Look up or create an assistant
2. Create a thread (or reuse one via `thread_id`)
3. Build the agent graph via `graph(config)`
4. Invoke the agent with the message
5. Return the response text

This is essentially what `execute_run_stream` does in `streams.py` but non-streaming.

## Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| LangChain native MCP support doesn't exist or is immature | Medium | Medium | Keep current manual wrapping as fallback |
| Connection pooling adds complexity for marginal gain | Medium | Medium | Measure before optimizing — profile tool call latency |
| Multi-server config breaks OAP UI compatibility | High | Medium | Additive change only — keep single-server as default |
| MCP server wiring creates circular imports | Medium | High | Use lazy imports, dependency injection |

## Dependencies

- **Upstream**: Goal 12 (Postgres Persistence) — agent execution needs checkpointer/store for stateful MCP tool calls
- **Downstream**: None identified

## Files Likely Affected

### MCP Client
- `tools_agent/agent.py` — `MCPConfig`, `graph()` MCP tool loading
- `tools_agent/utils/tools.py` — `create_langchain_mcp_tool`, connection management
- `tools_agent/utils/token.py` — token caching improvements

### MCP Server
- `robyn_server/mcp/handlers.py` — wire `_execute_agent`, streaming, dynamic tools
- `robyn_server/mcp/schemas.py` — additional schemas if needed
- `robyn_server/routes/mcp.py` — SSE streaming support on GET

### New Files (possible)
- `tools_agent/utils/mcp_pool.py` — MCP connection pool manager
- `robyn_server/agent.py` — shared agent execution logic (extracted from streams.py)

## References

- [MCP Specification](https://modelcontextprotocol.io/specification)
- [MCP Streamable HTTP Transport](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#streamable-http)
- [LangChain MCP Integration](https://docs.langchain.com/oss/python/langchain/mcp) — check if exists
- Current MCP client: `tools_agent/utils/tools.py`
- Current MCP server: `robyn_server/mcp/handlers.py`

## Notes & Decisions

### Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-11 | Goal created as P2 after Postgres persistence | MCP improvements are valuable but not blocking |
| 2026-02-11 | Research-first approach (Task-01) | LangChain v1 may have native MCP support that changes the approach |

### Open Questions

- [ ] Does LangChain v1 provide native MCP tool integration? (check via SearchDocsByLangChain)
- [ ] Should the MCP server expose individual sub-tools or just the top-level agent?
- [ ] What's the latency impact of per-call MCP connections? (measure before optimizing)
- [ ] Should MCP server support the full Streamable HTTP spec including SSE streaming?
- [ ] How should MCP auth interact with Supabase JWT — pass-through or separate?
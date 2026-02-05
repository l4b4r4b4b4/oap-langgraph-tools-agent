# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.0.1] - 2026-02-05

### Added

#### Robyn Runtime - Full LangGraph Feature Parity

The Robyn runtime now implements 100% of the LangGraph API specification, achieving full feature parity with the original FastAPI implementation.

**A2A Protocol (Agent-to-Agent Communication)**
- `POST /a2a/{assistant_id}` - JSON-RPC 2.0 message handler
- Supported methods:
  - `message/send` - Send message and wait for result
  - `message/stream` - Send message with SSE streaming response
  - `tasks/get` - Retrieve task status by ID
  - `tasks/cancel` - Cancel task (returns not-supported gracefully)
- Maps A2A concepts to LangGraph primitives (contextId → thread_id, taskId → run_id)
- 70 comprehensive tests

**Crons API (Scheduled Recurring Runs)**
- `POST /runs/crons` - Create a cron job
- `POST /runs/crons/search` - Search crons with filters
- `POST /runs/crons/count` - Count matching crons
- `DELETE /runs/crons/{cron_id}` - Delete a cron job
- APScheduler integration for background job scheduling
- Croniter-based schedule validation (5 and 6 field expressions)
- `on_run_completed`: "delete" (stateless) vs "keep" (persistent threads)
- Owner isolation for multi-tenant support
- 58 comprehensive tests

**MCP Protocol (Model Context Protocol)**
- `POST /mcp/` - JSON-RPC 2.0 message handler
- `GET /mcp/` - Returns 405 (streaming not supported)
- `DELETE /mcp/` - Returns 404 (stateless, no sessions)
- Supported methods:
  - `initialize` - Client handshake with capabilities
  - `tools/list` - Returns `langgraph_agent` tool
  - `tools/call` - Execute agent with message
  - `ping` - Health check
- 30 comprehensive tests

**Enhanced `/info` Endpoint**
```json
{
  "capabilities": {
    "streaming": true,
    "store": true,
    "crons": true,
    "a2a": true,
    "mcp": true,
    "metrics": true
  },
  "tiers": {
    "tier1": true,
    "tier2": true,
    "tier3": true
  }
}
```

#### CI/CD Pipeline

- **GitHub Actions Workflows**
  - `ci.yml` - Lint and test for both `tools_agent` and `robyn_server`
  - `image.yml` - Docker build and push for main LangGraph runtime
  - `robyn-image.yml` - Docker build and push for Robyn runtime
  - `release.yml` - PyPI and GitHub release workflow on version tags

- **Branch Protection**
  - Required status checks: Lint, Test robyn_server, CI Success
  - Pull request required for main branch merges

- **Docker Images**
  - `ghcr.io/l4b4r4b4b4/oap-langgraph-tools-agent:latest`
  - `ghcr.io/l4b4r4b4b4/oap-langgraph-tools-agent-robyn:latest`

### Changed

- Updated `pyproject.toml` with new dependencies: `apscheduler`, `croniter`
- Storage layer now includes `CronStore` for cron job persistence
- OpenAPI spec updated with full A2A, Crons, and MCP documentation

### Technical Details

- **Total Tests**: 426 passing (robyn_server)
- **New Modules**:
  - `robyn_server/a2a/` - A2A Protocol implementation
  - `robyn_server/crons/` - Crons API implementation
  - `robyn_server/mcp/` - MCP Protocol implementation
- **Dependencies Added**:
  - `apscheduler>=3.11.2` - Background job scheduler
  - `croniter>=6.0.0` - Cron expression parsing

---

## Previous Development

### Initial Release

- Robyn runtime server with Tier 1 and Tier 2 LangGraph API support
- Supabase JWT authentication
- SSE streaming support
- Store API for long-term memory
- Prometheus metrics
- 240+ initial tests

[Unreleased]: https://github.com/l4b4r4b4b4/oap-langgraph-tools-agent/compare/v0.0.1...HEAD
[0.0.1]: https://github.com/l4b4r4b4b4/oap-langgraph-tools-agent/releases/tag/v0.0.1
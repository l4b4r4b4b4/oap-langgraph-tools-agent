# Goal 08 — CI/CD DevOps Workflow & Feature Parity

> Establish production-ready CI/CD pipeline with branch protection and implement remaining API features for full parity with LangGraph FastAPI implementation.

---

## Objective

1. **CI/CD Pipeline**: Proper GitHub Actions workflow with:
   - Feature branch → PR → CI (tests/lint) → merge → CD (Docker + optional PyPI release)
   - Main branch protection enforced via rulesets
   - Separate workflows for Robyn runtime and original LangGraph runtime

2. **Feature Parity**: Implement missing endpoints to match LangGraph FastAPI:
   - Crons API (scheduled/recurring runs)
   - A2A Protocol (Agent-to-Agent)
   - MCP Protocol (Model Context Protocol server)

---

## Decision: Fork vs New Repo

**Decision: Keep as fork but treat as independent**

Rationale:
- Already have our own repo URL (`l4b4r4b4b4/oap-langgraph-tools-agent`)
- Robyn implementation is substantially different (not patches to FastAPI)
- Want our own release cycle and versioning
- No need to sync with upstream LangChain repo
- Clean CI/CD without upstream conflicts
- Can still reference upstream for API spec updates if needed

---

## Current State Analysis

### What Exists
- ✅ `.github/workflows/ci.yml` - Lint and test workflow
- ✅ `.github/workflows/image.yml` - Docker build and push to GHCR
- ✅ `.github/rulesets/main.json` - Branch protection ruleset
- ✅ `robyn_server/Dockerfile` - Robyn runtime Docker build
- ✅ `Dockerfile` - Original LangGraph runtime Docker build

### What's Missing
- ❌ CI doesn't run `robyn_server/` tests
- ❌ No separate Docker workflow for Robyn runtime
- ❌ No release workflow for PyPI publishing
- ❌ Uncommitted changes need to be organized and committed
- ❌ Crons, A2A, MCP endpoints not implemented

### OpenAPI Comparison

| Feature | Robyn | LangGraph FastAPI |
|---------|-------|-------------------|
| OpenAPI Version | 3.1.0 | 3.1.0 |
| Endpoints | 28 paths | ~50 paths |
| Assistants API | ✅ Full | Full |
| Threads API | ✅ Full | Full |
| Thread Runs API | ✅ Full | Full |
| Stateless Runs API | ✅ Full | Full |
| Store API | ✅ Full | Full |
| Crons API | ❌ Missing | ✅ Included |
| A2A Protocol | ❌ Missing | ✅ Included |
| MCP Protocol | ❌ Missing | ✅ Included |

---

## Task Breakdown

| Task | Name | Status | Priority |
|------|------|--------|----------|
| 01 | Organize & Commit Current Work | 🟢 Complete | Critical |
| 02 | Update CI Workflow for Robyn Tests | 🟢 Complete | Critical |
| 03 | Add Robyn Docker Workflow | 🟢 Complete | Critical |
| 04 | Add Release Workflow (PyPI) | 🟢 Complete | High |
| 05 | Verify Branch Protection Rules | 🟢 Complete | High |
| 06 | Implement Crons API | 🟢 Complete | Medium |
| 07 | Implement A2A Protocol | 🟢 Complete | Medium |
| 08 | Implement MCP Protocol | 🟢 Complete | Medium |
| 09 | Documentation & Cleanup | ⚪ Not Started | Medium |

---

## Completed Work Summary

### PR #1 Merged (2026-02-05)

**CI/CD Pipeline Established:**
- `ci.yml` - Lint + test for both `tools_agent` and `robyn_server`
- `image.yml` - CD workflow for main LangGraph Docker image (main/tags only)
- `robyn-image.yml` - CD workflow for Robyn Docker image (main/tags only)
- `release.yml` - PyPI + GitHub release workflow on version tags

**Key Fix Applied:**
- Separated CI (lint+test on PRs) from CD (Docker builds on main/tags)
- CI should NOT build Docker images - that's CD after merge

**Branch Protection (Ruleset ID: 12191808):**
- Requires PR to merge to main
- Required status checks: `Lint`, `Test robyn_server`, `CI Success`
- No approval required (solo dev workflow)

**Docker Images Published to GHCR:**
- `ghcr.io/l4b4r4b4b4/oap-langgraph-tools-agent:latest`
- `ghcr.io/l4b4r4b4b4/oap-langgraph-tools-agent-robyn:latest`

### PR #2 Merged (2026-02-05)

**MCP Protocol Implementation:**
- `POST /mcp/` - JSON-RPC 2.0 message handler
- `GET /mcp/` - Returns 405 (streaming not supported)
- `DELETE /mcp/` - Returns 404 (stateless, no sessions)

**MCP Methods Supported:**
- `initialize` - Client handshake with capabilities
- `tools/list` - Returns `langgraph_agent` tool
- `tools/call` - Execute agent with message
- `ping` - Health check

**Files Created:**
- `robyn_server/mcp/` - MCP module (schemas, handlers)
- `robyn_server/routes/mcp.py` - HTTP route handlers
- `robyn_server/tests/test_mcp.py` - 30 tests

**Updated `/info` endpoint:** `capabilities.mcp = true`

### PR #3 (Pending) - A2A Protocol

**A2A Protocol Implementation:**
- `POST /a2a/{assistant_id}` - JSON-RPC 2.0 message handler

**A2A Methods Supported:**
- `message/send` - Send message, wait for result (maps to runs/wait)
- `message/stream` - Send message, stream response (SSE)
- `tasks/get` - Retrieve task status
- `tasks/cancel` - Returns not-supported error

**Files Created:**
- `robyn_server/a2a/` - A2A module (schemas, handlers)
- `robyn_server/routes/a2a.py` - HTTP route handlers
- `robyn_server/tests/test_a2a.py` - 70 tests

**Updated `/info` endpoint:** `capabilities.a2a = true`

**Test Count:** 426 tests passing in `robyn_server/`

---

## Task 01: Organize & Commit Current Work

### Files to Commit

**New directories:**
- `robyn_server/` - Complete Robyn runtime implementation
- `.github/` - Workflows and rulesets
- `.devops/` - DevOps configurations

**Modified files:**
- `pyproject.toml` - Added robyn dependency
- `uv.lock` - Updated lockfile
- `.gitignore` - Updated ignores
- `README.md` - Updated documentation
- `flake.nix` - Nix development environment

**Files to archive/clean:**
- `test_*.py` files in root - Move to `archive/` or proper test directories
- `debug_*.py` files - Move to `archive/`

### Commit Strategy

1. First commit: Clean up test files (move to archive)
2. Second commit: Core infrastructure (pyproject.toml, flake.nix, .github)
3. Third commit: Robyn server implementation
4. Fourth commit: Documentation updates

---

## Task 02: Update CI Workflow

### Current ci.yml
```yaml
# Runs ruff check, ruff format, pytest on root
```

### Updated ci.yml (Plan)
```yaml
name: CI / lint-and-test

on:
  push:
    branches: ['**']
    tags: ['v*']
  pull_request:
    branches: ['**']

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Sync dependencies
        run: uv sync --quiet
      - name: Ruff check
        run: uv run ruff check .
      - name: Ruff format
        run: uv run ruff format --check .

  test-tools-agent:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Sync dependencies
        run: uv sync --quiet
      - name: Run tools_agent tests
        run: uv run pytest tests/ -v --tb=short

  test-robyn-server:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Sync dependencies
        run: uv sync --quiet
      - name: Run robyn_server tests
        run: uv run pytest robyn_server/tests/ -v --tb=short
```

---

## Task 03: Add Robyn Docker Workflow

### New robyn-image.yml (Plan)
```yaml
name: CI / build-robyn-image

on:
  push:
    branches: [main]
    tags: ['v*']
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}-robyn

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/metadata-action@v5
        id: meta
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch,prefix=branch-
            type=sha,prefix=sha-
            type=raw,value=latest,enable=${{ github.ref == 'refs/heads/main' }}
            type=semver,pattern={{version}}
      - uses: docker/build-push-action@v5
        with:
          context: .
          file: robyn_server/Dockerfile
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

---

## Task 04: Add Release Workflow

### New release.yml (Plan)
```yaml
name: Release

on:
  push:
    tags: ['v*']

jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      id-token: write  # For PyPI trusted publishing
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Build package
        run: uv build
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          packages-dir: dist/
      - name: Create GitHub Release
        uses: softprops/action-gh-release@v1
        with:
          generate_release_notes: true
          files: dist/*
```

---

## Task 05: Verify Branch Protection

### Current Ruleset
- ✅ Prevent deletion of main
- ✅ Require pull request with 1 approval
- ✅ Dismiss stale reviews on push
- ✅ Require status check: "CI / lint-and-test"

### Updates Needed
- Add status check: "CI / test-robyn-server"
- Add status check: "CI / build-robyn-image"

---

## Task 06: Implement Crons API ✅ Complete

### Endpoints Implemented
- `POST /runs/crons` - Create a cron job
- `POST /runs/crons/search` - Search cron jobs
- `POST /runs/crons/count` - Count cron jobs
- `DELETE /runs/crons/{cron_id}` - Delete a cron job

### Implementation Details
- APScheduler (AsyncIOScheduler) for background scheduling
- croniter for schedule expression parsing
- CronStore in storage.py for persistence
- Full module: `robyn_server/crons/` (schemas, handlers, scheduler)
- 58 tests in test_crons.py
- OpenAPI spec updated with Crons tag and schemas

---

## Task 07: Implement A2A Protocol

### Endpoints to Implement
- `POST /a2a/{assistant_id}` - JSON-RPC endpoint for A2A protocol

### A2A Methods
- `message/send` - Send message to agent
- `message/stream` - Stream message to agent
- `tasks/get` - Get task status
- `tasks/cancel` - Cancel a task

### Implementation Notes
- JSON-RPC 2.0 protocol
- Maps to existing run execution logic
- Adds task abstraction layer over runs

---

## Task 08: Implement MCP Protocol

### Endpoints to Implement
- `POST /mcp/` - MCP message endpoint
- `GET /mcp/` - MCP endpoint (returns 405)
- `DELETE /mcp/` - MCP endpoint (returns 404)

### Implementation Notes
- Model Context Protocol for LLM integration
- Robyn has native MCP support (`app.mcp_server_tools`)
- May leverage existing Robyn MCP infrastructure

---

## Success Criteria

### CI/CD (Tasks 01-05) ✅ COMPLETE
- [x] All uncommitted work properly organized and committed
- [x] CI runs tests for both tools_agent and robyn_server
- [x] Docker images built for both runtimes on push to main
- [x] Release workflow publishes to PyPI on version tags
- [x] Branch protection requires all CI checks to pass

### Feature Parity (Tasks 06-09)
- [x] Crons API endpoints implemented and tested (58 tests)
- [x] A2A Protocol endpoints implemented and tested (PR #3)
- [x] MCP Protocol endpoints implemented and tested (PR #2)
- [x] OpenAPI spec updated to include all new endpoints
- [x] Test coverage maintained at ≥73% (426 tests passing)

---

## Notes

- Priority: CI/CD first (Tasks 01-05), then Feature Parity (Tasks 06-09)
- Can deploy to AKS with current implementation (core features work)
- Feature parity is "nice to have" for full LangGraph compatibility
- Crons/A2A/MCP are advanced features, not critical for basic agent operations
- **All feature parity tasks complete** - ready for PR with A2A + Crons

---

## Session Handoff: Task 06 - Crons API

```
# Task 06 - Crons API Implementation

## Context
Robyn LangGraph runtime with A2A Protocol complete (PR pending).
See `.agent/goals/08-CI-CD-Feature-Parity/scratchpad.md` for full details.
Task 07 (A2A) is complete with 70 tests, 368 total tests passing.

## What Was Done (This Session)
- Implemented A2A Protocol (`robyn_server/a2a/` module)
- 4 methods: message/send, message/stream, tasks/get, tasks/cancel
- 70 new tests, all passing
- Updated OpenAPI spec and /info endpoint

## Current Task: Implement Crons API (Task 06)
Full implementation with background scheduler (APScheduler).

### Endpoints to Implement
- POST /runs/crons - Create cron job
- POST /runs/crons/search - Search crons
- POST /runs/crons/count - Count crons  
- DELETE /runs/crons/{cron_id} - Delete cron

### Key Files
- `.agent/tmp/langgraph-serve_openape_spec.json` L2150-2571 (Crons spec)
- `.agent/tmp/langgraph-serve_openape_spec.json` L3537-3810 (Cron schemas)
- `robyn_server/a2a/` - Reference for module structure
- `robyn_server/mcp/` - Reference for JSON-RPC pattern

### Implementation Notes
- Add APScheduler dependency via `uv add apscheduler`
- Store cron definitions in memory (same pattern as other entities)
- Calculate next_run_date from cron schedule
- Handle on_run_completed: "delete" vs "keep" thread policy

## Guidelines
- Create Task-06-Crons-API directory and scratchpad first
- Follow same module pattern as A2A (schemas, handlers, routes)
- Run ruff and pytest before completing
```

---

## References

- [LangGraph API Spec](../.agent/tmp/langgraph-serve_openape_spec.json)
- [Robyn OpenAPI Spec](../.agent/tmp/robyn_openapi.json)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
- [A2A Protocol Spec](https://github.com/google/a2a-spec)
- [MCP Protocol Spec](https://modelcontextprotocol.io/)
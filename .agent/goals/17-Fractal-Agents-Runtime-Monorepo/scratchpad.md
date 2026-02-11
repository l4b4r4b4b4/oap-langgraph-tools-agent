# Goal 17: Transition to `fractal-agents-runtime` Monorepo

> **Status:** ⚪ Not Started
> **Priority:** Critical
> **Created:** 2026-02-11
> **Last Updated:** 2026-02-11

---

## Objectives

Detach from the `langchain-ai/oap-langgraph-tools-agent` fork and establish a self-sufficient monorepo named `fractal-agents-runtime` with:

1. **Bun-based workspace** at the root for monorepo orchestration
2. **`apps/python/`** — Robyn-based LangGraph runtime (publishes to PyPI + GHCR Docker image)
3. **`apps/ts/`** — Scaffolded Bun/TypeScript variant for future high-perf deployment

---

## Justification: Fork Divergence Analysis

### Quantitative

| Metric | Value |
|--------|-------|
| Fork point | `8bf78d7` ("chore: Bump deps (#40)") |
| Commits since fork | 13 |
| Files changed | 223 |
| Lines added | 78,246 |
| Lines deleted | 1,046 |
| Upstream file count | ~10 |
| Our file count | 126 source files, 62 Python modules |
| Test count | 550+ |

### Qualitative

**Entirely original subsystems (no shared code with upstream):**
- `robyn_server/` — 14 modules, routes, tests, Helm charts, A2A, MCP, crons
- `.github/workflows/` — 4 CI/CD pipelines
- 2 Dockerfiles + docker-compose
- `flake.nix`, `.rules`, `CHANGELOG.md`
- `tools_agent/tracing.py`, `tools_agent/utils/store_namespace.py`
- Agent sync, Postgres persistence, store API, Langfuse integration

**Modified shared code:**
- `tools_agent/agent.py` — 312 insertions / 95 deletions (essentially rewritten)
- `security/auth.py` — heavily modified
- `utils/tools.py` — heavily modified

**Upstream engagement:**
- [Issue #42](https://github.com/langchain-ai/oap-langgraph-tools-agent/issues/42) filed Feb 6, 2026
- Zero comments, zero reactions after 5 days
- No indication of interest from LangChain maintainers

**Verdict:** This is substantively an independent project. The fork label misrepresents provenance, blocks independent issue tracking / stars / discovery, and adds no value.

---

## Architecture Decision: Monorepo Structure

```
fractal-agents-runtime/
├── package.json              # Bun workspace root
├── bun.lock
├── flake.nix                 # Nix flake (monorepo: bun + python/uv + ts)
├── .github/
│   └── workflows/            # Monorepo-aware CI/CD
│       ├── ci.yml            # Lint + test (both apps)
│       ├── python-image.yml  # Python Docker → GHCR
│       ├── python-pypi.yml   # Python package → PyPI
│       └── ts-ci.yml         # Future TS CI
├── apps/
│   ├── python/               # Robyn-based LangGraph runtime
│   │   ├── pyproject.toml    # fractal-agents-runtime package
│   │   ├── uv.lock
│   │   ├── Dockerfile
│   │   ├── langgraph.json
│   │   ├── src/
│   │   │   ├── react_agent_with_mcp_tools/   # Renamed from tools_agent
│   │   │   │   ├── __init__.py
│   │   │   │   ├── agent.py              # LangGraph ReAct agent graph
│   │   │   │   ├── tracing.py
│   │   │   │   ├── security/
│   │   │   │   └── utils/
│   │   │   └── robyn_server/
│   │   │       ├── (all existing robyn code)
│   │   │       └── tests/
│   │   └── README.md
│   └── ts/                   # Future Bun/TS variant (high-perf deployment)
│       ├── package.json
│       ├── tsconfig.json
│       ├── src/
│       │   └── index.ts      # Placeholder entrypoint
│       └── README.md
├── packages/                 # Future shared packages
│   └── .gitkeep
├── docs/
├── .agent/                   # Carried over from current repo
├── .rules
├── README.md
├── LICENSE                   # MIT — with LangChain attribution
└── CHANGELOG.md
```

### Why Bun Workspace?

- **Native monorepo support** via `workspaces` in package.json
- **TS app uses bun natively** — no separate toolchain needed
- **Python app delegates to uv** — bun scripts call `uv sync`, `pytest`, etc.
- **Fast** — bun install/run is dramatically faster than npm/yarn
- **Simple** — no Turborepo, Nx, or Lerna overhead for 2 apps

### Key Naming Decisions

| What | Name |
|------|------|
| GitHub repo | `fractal-agents-runtime` |
| PyPI package | `fractal-agents-runtime` |
| Agent graph module | `react_agent_with_mcp_tools` (renamed from `tools_agent`) |
| Server module | `robyn_server` (unchanged) |
| Docker image (Python) | `ghcr.io/l4b4r4b4b4/fractal-agents-runtime` |
| TS package (future) | `@fractal/agents-runtime` |

> **Rationale for `react_agent_with_mcp_tools`:** The module IS a ReAct agent that uses
> MCP tools. The name is long but self-documenting. It's internal to the monorepo
> (robyn_server imports it, end users don't), so clarity > brevity.

### License & Attribution

- License remains **MIT**
- Add attribution line: "Originally derived from [langchain-ai/oap-langgraph-tools-agent](https://github.com/langchain-ai/oap-langgraph-tools-agent) (MIT License, Copyright LangChain, Inc.)"
- Our new copyright: "Copyright (c) 2026 l4b4r4b4b4"
- This is fully compliant with MIT license terms

---

## Success Criteria

- [ ] New `fractal-agents-runtime` repo created on GitHub (not a fork)
- [ ] Bun workspace at root with `apps/python/` and `apps/ts/`
- [ ] All Python code migrated into `apps/python/` with `fractal_agents_runtime` module name
- [ ] `uv sync && pytest` passes from `apps/python/`
- [ ] `ruff check . && ruff format --check .` passes from `apps/python/`
- [ ] Docker build succeeds for the Python app
- [ ] CI/CD workflows adapted for monorepo paths
- [ ] PyPI publish workflow configured (manual trigger for now)
- [ ] `apps/ts/` scaffolded with Bun project, tsconfig, placeholder entrypoint
- [ ] `bun install` works at root
- [ ] README reflects new identity, architecture, and attribution
- [ ] Git history preserved (not a squash — import full history)
- [ ] Old repo archived or updated with redirect notice

---

## Task Breakdown

### Task-01: Create New Repo & Monorepo Scaffold
- Create `fractal-agents-runtime` repo on GitHub (NOT a fork)
- Initialize bun workspace: `package.json` with workspaces config
- Create directory structure: `apps/`, `packages/`, `docs/`
- Root-level files: `.gitignore`, `README.md`, `LICENSE`, `.rules`
- **Depends on:** Nothing

### Task-02: Migrate Python App
- Move `tools_agent/` → `apps/python/src/react_agent_with_mcp_tools/`
- Move `robyn_server/` → `apps/python/src/robyn_server/`
- Update all internal imports (`tools_agent.` → `react_agent_with_mcp_tools.`)
- Update `pyproject.toml` (package name, module paths, version 0.0.0)
- Update `langgraph.json` paths
- Verify: `uv sync && pytest && ruff check .`
- **Depends on:** Task-01

### Task-03: Migrate Docker & CI/CD
- Move/update Dockerfiles for monorepo context paths
- Adapt all GitHub Actions workflows for `apps/python/` paths
- Path-filtered triggers (only run Python CI on `apps/python/**` changes)
- GHCR image build with new naming
- **Depends on:** Task-02

### Task-04: Scaffold TypeScript App
- Create `apps/ts/package.json` with bun/TypeScript config
- `tsconfig.json` with strict settings
- Placeholder `src/index.ts` with basic type-safe structure
- README documenting future intent and API parity goals
- Basic `bun test` setup
- **Depends on:** Task-01

### Task-05: PyPI Publishing Pipeline
- Configure `apps/python/pyproject.toml` for PyPI distribution
- GitHub Actions workflow for PyPI publish (tag-triggered)
- Test with `uv build` locally
- Version 0.0.0 initial publish
- **Depends on:** Task-02, Task-03

### Task-06: Documentation & Cleanup
- Root README: project vision, monorepo structure, getting started
- Per-app READMEs
- CHANGELOG reset for new project identity
- Update `.rules` for monorepo context
- Archive/redirect notice on old repo
- Migrate `.agent/goals/` history
- **Depends on:** All other tasks

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Git history loss | High | Import via `git filter-repo` or fresh repo with full history attribution |
| Import rename breakage | High | Systematic find/replace + full test suite validation |
| PyPI name conflict | Medium | Check availability before committing to name |
| CI/CD path filter bugs | Medium | Test with dry-run PRs before merging |
| Bun workspace + uv friction | Low | Bun delegates to uv for Python; no tight coupling |

---

## Decisions (Resolved)

1. **Git history strategy:** ✅ **Fresh repo.** Commit current state in old repo, create empty
   public repo on GitHub, `cp` directory, `rm -rf .git`, reorganize, `git init`, push.
   Clean break — no history transplant, no filter-repo.
2. **PyPI name:** ✅ **`fractal-agents-runtime` is available** on both PyPI and GitHub.
   (`fractal-agents` exists but is a different project — pre-alpha placeholder by someone else.)
3. **Old repo fate:** ✅ **Leave as-is for now.** Archive with redirect once successfully transitioned.
4. **Nix flake:** ✅ **Update for monorepo now.** User will provide a starting point for the
   monorepo flake covering bun + python/uv + ts apps.
5. **Module rename:** ✅ **`tools_agent` → `react_agent_with_mcp_tools`** — descriptive name
   reflecting that this is a ReAct agent graph with MCP tool capabilities.

---

## Execution Plan

**Step-by-step for Task-01:**
1. Commit & push any pending changes in `oap-langgraph-tools-agent`
2. Create empty `fractal-agents-runtime` repo on GitHub (NOT a fork, public, no README init)
3. `cp -r oap-langgraph-tools-agent ../fractal-agents-runtime`
4. `cd ../fractal-agents-runtime && rm -rf .git`
5. Delete stale artifacts: `.venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `*.egg-info/`
6. Reorganize into monorepo structure (apps/python/, apps/ts/, packages/)
7. Create bun workspace: `package.json` at root
8. User provides flake.nix starting point for monorepo
9. `git init && git add . && git commit && git remote add origin && git push`

---

## Notes

- The original LangChain MIT license permits this transition fully
- We implement the LangGraph runtime **protocol/API** — we don't depend on their server code
- The Robyn server, store API, agent sync, A2A, MCP, crons — all original work
- Even `agent.py` is essentially rewritten (312/95 = 3.3x more new code than original)
- Goal 07 (Bun + TypeScript Runtime) is subsumed into Task-04 of this goal
# Task-01: Create New Repo & Monorepo Scaffold

> **Status:** ⚪ Not Started
> **Priority:** Critical
> **Created:** 2026-02-11
> **Last Updated:** 2026-02-11
> **Parent Goal:** [17-Fractal-Agents-Runtime-Monorepo](../scratchpad.md)
> **Depends on:** Nothing

---

## Objective

Create a fresh `fractal-agents-runtime` GitHub repo (NOT a fork) and set up the bun-based monorepo scaffold with the correct directory structure for `apps/python/`, `apps/ts/`, and `packages/`.

---

## Implementation Plan

### Step 1: Ensure Current Repo is Clean

- [ ] Verify all changes committed and pushed to `oap-langgraph-tools-agent` main
- [ ] Run `git status` — should be clean

### Step 2: Create Empty GitHub Repo

- [ ] Create `fractal-agents-runtime` repo on GitHub
  - Owner: `l4b4r4b4b4`
  - Public, NOT a fork
  - No README init, no .gitignore, no license (we'll add our own)
- [ ] Verify repo exists and is empty

### Step 3: Copy and Clean

- [ ] `cp -r oap-langgraph-tools-agent ../fractal-agents-runtime`
- [ ] `cd ../fractal-agents-runtime && rm -rf .git`
- [ ] Remove stale build/cache artifacts:
  - `.venv/`
  - `__pycache__/` (all instances)
  - `.pytest_cache/`
  - `.ruff_cache/`
  - `tools_agent.egg-info/`
  - `.langgraph_api/`
  - `archive/`

### Step 4: Reorganize into Monorepo Structure

**Directory creation:**
- [ ] `mkdir -p apps/python/src`
- [ ] `mkdir -p apps/ts/src`
- [ ] `mkdir -p packages`

**Move Python code into `apps/python/`:**
- [ ] `mv tools_agent/ apps/python/src/react_agent_with_mcp_tools/`
- [ ] `mv robyn_server/ apps/python/src/robyn_server/`
- [ ] `mv pyproject.toml apps/python/`
- [ ] `mv uv.lock apps/python/`
- [ ] `mv Dockerfile apps/python/Dockerfile.langgraph`
- [ ] `mv robyn_server/Dockerfile apps/python/Dockerfile` (already moved with robyn_server)
  - Actually: the robyn Dockerfile is inside robyn_server/ so it moves with it
  - Need to relocate it to `apps/python/Dockerfile`
- [ ] `mv langgraph.json apps/python/`
- [ ] `mv docker-compose.yml apps/python/`
- [ ] `mv Makefile apps/python/`
- [ ] `mv openapi.json apps/python/`
- [ ] `mv tests/ apps/python/tests/` (root-level tests dir)
- [ ] `mv scripts/ apps/python/scripts/`
- [ ] `mv static/ apps/python/static/`
- [ ] `mv docs/ docs/` (keep at root — monorepo-level docs)

**Files that stay at root:**
- `.rules` (update for monorepo)
- `.agent/` (goal tracking)
- `LICENSE` (new — dual copyright)
- `README.md` (new — monorepo overview)
- `CHANGELOG.md` (new — fresh start)
- `.gitignore` (new — monorepo-aware)
- `flake.nix` (new — user provides starting point)
- `flake.lock` (generated)
- `package.json` (new — bun workspace root)

**Files to delete (root-level, now redundant):**
- [ ] Old root `Dockerfile` (replaced by `apps/python/Dockerfile`)
- [ ] `.devops/` (review — may move to apps/python or .github)
- [ ] `.langgraph_api/` (build artifact)
- [ ] `.zed/` (editor config — recreate if needed)
- [ ] `.vscode/` (editor config — recreate if needed)

### Step 5: Create Bun Workspace Root

**`package.json`:**
```json
{
  "name": "fractal-agents-runtime",
  "private": true,
  "workspaces": [
    "apps/*",
    "packages/*"
  ],
  "scripts": {
    "dev:python": "cd apps/python && uv run python -m robyn_server",
    "dev:ts": "cd apps/ts && bun run dev",
    "test:python": "cd apps/python && uv run pytest",
    "test:ts": "cd apps/ts && bun test",
    "test": "bun run test:python && bun run test:ts",
    "lint:python": "cd apps/python && uv run ruff check . && uv run ruff format --check .",
    "lint:ts": "cd apps/ts && bun run lint",
    "lint": "bun run lint:python && bun run lint:ts",
    "format:python": "cd apps/python && uv run ruff check . --fix --unsafe-fixes && uv run ruff format .",
    "docker:python": "docker build -f apps/python/Dockerfile -t fractal-agents-runtime:latest apps/python"
  }
}
```

### Step 6: Scaffold TypeScript App

**`apps/ts/package.json`:**
```json
{
  "name": "@fractal/agents-runtime-ts",
  "version": "0.0.0",
  "private": true,
  "scripts": {
    "dev": "bun run src/index.ts",
    "build": "bun build src/index.ts --outdir dist",
    "test": "bun test",
    "lint": "echo 'TODO: add biome or eslint'"
  },
  "devDependencies": {
    "@types/bun": "latest",
    "typescript": "^5.8"
  }
}
```

**`apps/ts/tsconfig.json`:**
```json
{
  "compilerOptions": {
    "target": "ESNext",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "skipLibCheck": true,
    "noEmit": true,
    "esModuleInterop": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "types": ["bun-types"],
    "outDir": "dist",
    "rootDir": "src"
  },
  "include": ["src/**/*.ts"],
  "exclude": ["node_modules", "dist"]
}
```

**`apps/ts/src/index.ts`:**
- Placeholder with TODO comments referencing LangGraph API parity
- Basic type definitions for the runtime protocol

### Step 7: Root Configuration Files

**`.gitignore`** — monorepo-aware:
- Node: `node_modules/`, `dist/`, `bun.lock` (or commit it?)
- Python: `.venv/`, `__pycache__/`, `*.egg-info/`, `.ruff_cache/`
- General: `.env`, `.DS_Store`, `archive/`
- IDE: `.vscode/`, `.zed/`

**`LICENSE`** — MIT with dual copyright:
```
Copyright (c) 2026 l4b4r4b4b4
Originally derived from langchain-ai/oap-langgraph-tools-agent (MIT License, Copyright LangChain, Inc.)
```

**`README.md`** — Monorepo overview:
- Project vision
- Architecture diagram (apps/python, apps/ts)
- Quick start
- Links to per-app READMEs

### Step 8: Git Init & Push

- [ ] `git init`
- [ ] `git add .`
- [ ] `git commit -m "feat: initial monorepo scaffold (migrated from oap-langgraph-tools-agent)"`
- [ ] `git remote add origin https://github.com/l4b4r4b4b4/fractal-agents-runtime.git`
- [ ] `git branch -M main`
- [ ] `git push -u origin main`

### Step 9: Nix Flake

- [ ] User provides starting point for monorepo flake
- [ ] Covers: bun, python/uv, typescript
- [ ] Per-app dev shells

---

## Files to Create

| File | Location | Description |
|------|----------|-------------|
| `package.json` | `/` | Bun workspace root |
| `package.json` | `apps/ts/` | TS app package |
| `tsconfig.json` | `apps/ts/` | TypeScript config |
| `src/index.ts` | `apps/ts/src/` | Placeholder entrypoint |
| `README.md` | `apps/ts/` | TS app documentation |
| `README.md` | `/` | Monorepo overview |
| `README.md` | `apps/python/` | Python app docs (update existing) |
| `LICENSE` | `/` | MIT with dual copyright |
| `.gitignore` | `/` | Monorepo-aware |
| `CHANGELOG.md` | `/` | Fresh start |
| `.rules` | `/` | Updated for monorepo context |
| `packages/.gitkeep` | `packages/` | Placeholder |

## Files to Move

| From | To |
|------|-----|
| `tools_agent/` | `apps/python/src/react_agent_with_mcp_tools/` |
| `robyn_server/` | `apps/python/src/robyn_server/` |
| `pyproject.toml` | `apps/python/pyproject.toml` |
| `uv.lock` | `apps/python/uv.lock` |
| `langgraph.json` | `apps/python/langgraph.json` |
| `Dockerfile` (root) | `apps/python/Dockerfile.langgraph` |
| `docker-compose.yml` | `apps/python/docker-compose.yml` |
| `Makefile` | `apps/python/Makefile` |
| `openapi.json` | `apps/python/openapi.json` |
| `tests/` | `apps/python/tests/` |
| `scripts/` | `apps/python/scripts/` |
| `static/` | `apps/python/static/` |
| `.github/` | `.github/` (stays, but workflows need updating) |

## Files to Delete

| File | Reason |
|------|--------|
| `.devops/` | Review contents, likely redundant with .github |
| `.langgraph_api/` | Build artifact |
| `.venv/` | Already gitignored, remove from copy |
| `*.egg-info/` | Build artifact |
| `__pycache__/` | Build artifact |
| `.pytest_cache/` | Build artifact |
| `.ruff_cache/` | Build artifact |

---

## Acceptance Criteria

- [ ] `fractal-agents-runtime` repo exists on GitHub, is public, is NOT a fork
- [ ] Bun workspace root with `package.json` defining workspaces
- [ ] `apps/python/` contains all Python source code
- [ ] `apps/ts/` contains scaffolded Bun/TS project
- [ ] `packages/` directory exists (empty with .gitkeep)
- [ ] `bun install` succeeds at root
- [ ] Root `.gitignore` covers both Python and Node artifacts
- [ ] `LICENSE` has dual copyright (ours + LangChain attribution)
- [ ] Root `README.md` describes monorepo structure
- [ ] Initial commit pushed to main

---

## Notes

- Task-02 will handle the Python import renames and `pyproject.toml` updates
- Task-03 will handle CI/CD workflow migration
- This task is purely structural — we move files but don't fix imports yet
- The Nix flake is a collaboration with the user — they'll provide a starting point
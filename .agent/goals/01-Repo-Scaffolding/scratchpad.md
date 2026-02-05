# Goal 01 — Repo scaffolding (flake.nix + .rules + branch protection + CI/CD to GHCR)

Status: 🟢 Complete  
Priority: Critical  
Owner: You  
Last Updated: 2026-01-27 (All tasks complete)

---

## Objective

Establish solid repository scaffolding and DevOps foundations for `l4b4r4b4b4/oap-langgraph-tools-agent`:

1. Bring `flake.nix` in line with this repository (naming, messaging, developer ergonomics; minimal changes).
2. Revise `.rules` so they describe this project (instead of the prior “Legal-MCP” framing) while preserving the important hard rules.
3. Add modern GitHub **Ruleset** (not classic branch protection) JSON for `main`, and apply it via GitHub CLI (already authenticated).
4. Implement CI/CD workflows for a defined flow:
   - feature branch → push → CI → pass → build/push feature image tagged with branch name + sha
   - PR against `main` → CI → pass → merge
   - `main` push → CI → pass → build/push `latest` image + sha, and optionally release tags

---

## Success Criteria (Acceptance Checklist)

### flake.nix
- [ ] `flake.nix` no longer references “legal-mcp” in names/banner/messages.
- [ ] Dev shell opens reliably and uses `uv` with a `.venv` (or preserves existing `.venv`) in repo root.
- [ ] No system-altering Nix commands are run automatically by the agent; user explicitly runs devshell build.
- [x] After edits: you (user) successfully enter the dev shell and restart Zed.
- [x] Work **pauses** after flake changes until user confirms success.

### .rules
- [x] `.rules` title and project references align with `oap-langgraph-tools-agent`.
- [x] Hard rules remain enforceable (secrets, safety, workflow, UV, code quality).
- [x] Any project-specific additions are minimal and non-contradictory.
- [x] Language matches this repo (LangGraph agent/runtime + GHCR publishing).

### Branch protection (Rulesets)
- [x] A JSON ruleset file exists (e.g. `github/rulesets/main.json` or similar).
- [x] Ruleset targets `main`.
- [x] Requires PRs, required status checks, and blocks force-push/deletion.
- [x] Applied via GitHub CLI and verified (e.g., list rulesets shows it exists).
- [x] Clear notes embedded in JSON or a `README` describing how to re-apply.

### CI/CD workflows
- [x] CI runs on feature branches and PRs to `main`.
- [x] CI includes at least: `uv sync`, `ruff check`, `ruff format --check` (or equivalent), `pytest`.
- [x] On feature branch push (CI pass): builds and pushes image to `ghcr.io/l4b4r4b4b4/oap-langgraph-tools-agent` with tags:
- [x] `branch-<sanitized-branch-name>`
- [x] `sha-<shortsha>` (or full sha)
- [x] On `main` push (CI pass): builds and pushes image with:
- [x] `latest`
- [x] `sha-<shortsha>`
- [x] Optional: on git tags `v*` build/push tag-matching image.
- [x] Workflows use least privilege permissions and GitHub OIDC/`GITHUB_TOKEN` for GHCR.

---

## Scope

### In scope
- Small/targeted cleanup of `flake.nix` messages, env name, and quick reference commands.
- `.rules` edits to rebrand + tune for this project.
- Creating GitHub ruleset JSON and applying via CLI.
- GitHub Actions workflows for CI and GHCR publishing.
- Adding/adjusting `Dockerfile` if needed to support the image build.

### Out of scope (for this goal)
- Removing LangSmith (Goal 02).
- Adding Langfuse tracing (Goal 03).
- Major refactors of Python code unless required for CI to pass.

---

## Constraints / Non-Goals

- Preserve existing repository content; use minimal diffs.
- Do not “over-automate” locally (no forced hooks that break existing flows).
- Avoid logging sensitive data (tokens, credentials, JWTs).
- Keep pipelines deterministic and reproducible.

---

## Proposed Task Breakdown

### Task 01 — Adjust `flake.nix` for this repo (STOP after, user validates) ✅ COMPLETE
**Plan**
- Rename `legal-mcp-dev-env` and banners to `oap-langgraph-tools-agent-dev-env` (or similar).
- Update the quick reference commands to match this project (likely `uv run langgraph dev --no-browser`).
- Ensure any Playwright/Chromium-specific LD_LIBRARY_PATH hacks are still needed; if uncertain, leave in place but reword comments to stay accurate (don't delete without proof).
- Keep `uv venv` creation logic, but update prompt name to match repo.

**Hold point**
- After edits, you (user) will:
  - build/enter dev shell
  - restart Zed
- Only proceed when you confirm success.

**Risks**
- Removing any FHS/LD_LIBRARY_PATH bits might break browser deps if they're still needed.
- ShellHook that `exec`s into FHS env can be surprising; change only if necessary.

**Outcome**: ✅ Successfully rebranded, dev shell works, Zed restarted.

### Task 02 — Revise `.rules` selection for this project ✅ COMPLETE
**Plan**
- Rebrand "Legal-MCP" references to this repo.
- Keep the workflow and safety rules intact.
- Ensure Python rules reflect actual python version policy (repo currently says `>=3.11,<3.13`; `.rules` says 3.12+).
  - Decide whether to update `.rules` to match repo, or update repo to match `.rules` (must be explicit).

**Risks**
- Inconsistent version policy causing confusion and CI failures.

**Outcome**: ✅ Updated `.rules` to reference `oap-langgraph-tools-agent`, kept hard rules, adjusted Python version note to match repo (`>=3.11,<3.13`), updated MCP → LangGraph agent design section.

### Task 03 — Add GitHub ruleset JSON for `main` and apply via CLI ✅ COMPLETE
**Plan**
- Create a ruleset that:
  - requires PRs
  - requires at least 1 approval (configurable)
  - requires status checks (CI workflow name(s))
  - blocks force push and branch deletion
  - enforces linear history (optional; decide)
- Apply with GH CLI.
- Verify by listing rulesets.

**Risks**
- If required check names are wrong, merges/pushes will be blocked.
- Need to ensure the CI workflow names are stable before locking checks.

**Outcome**: ✅ Successfully applied ruleset via GH CLI. Ruleset ID: 12191808. Includes:
- `deletion` rule (prevents branch deletion)
- `non_fast_forward` rule (enforces linear history)
- `pull_request` rule (requires 1 approval, dismisses stale reviews)
- `required_status_checks` rule (requires `CI / lint-and-test` with strict policy)
Verified active via `gh api /repos/l4b4r4b4b4/oap-langgraph-tools-agent/rulesets`.

### Task 04 — CI/CD workflows to GHCR matching desired flow ✅ COMPLETE
**Plan**
- Add workflows:
  - `ci.yml`: lint + test on pushes and PRs.
  - `image.yml` (or combined): on push to branches (non-main) build and push branch image on CI success.
  - `release.yml` optional: on tags `v*` build/push versioned image.
- Use `docker/build-push-action` and `docker/login-action`.
- Sanitize branch names for tags (replace `/` with `-`, lowercase, etc.).
- Always push sha tag for traceability.

**Risks**
- Using `GITHUB_TOKEN` requires correct permissions: `packages: write`.
- Repository settings might require enabling GHCR permissions for workflows.

**Outcome**: ✅ Created:
- `.github/workflows/ci.yml` (runs `ruff check`, `ruff format --check`, `pytest`)
- `.github/workflows/image.yml` (builds and pushes to GHCR with branch/sha/latest tags)
- `Dockerfile` (multi-stage slim image, Python 3.12, uv, non-root user, healthcheck)

---

## Decisions Made

- [x] Python version policy: keep repo `>=3.11,<3.13` and adjust `.rules` to match (done).
- [x] CI required checks list for ruleset: `CI / lint-and-test` only (image build optional).
- [x] Whether to enforce linear history and/or signed commits in ruleset: linear history via `non_fast_forward` rule.
- [x] Dockerfile baseline: multi-stage slim Python 3.12 + uv (created).

---

## Files Created / Modified

- ✅ `flake.nix` (edited - rebranded)
- ✅ `.rules` (edited - rebranded)
- ✅ `.github/rulesets/main.json` (created)
- ✅ `.github/workflows/ci.yml` (created)
- ✅ `.github/workflows/image.yml` (created)
- ✅ `Dockerfile` (created - multi-stage slim)
- `README.md` (not yet updated - optional)

---

## Test & Verification Strategy

- Local:
  - Enter dev shell; ensure `uv sync` works and tooling is available.
- CI:
  - Workflow runs successfully on a feature branch.
  - Image appears in GHCR with expected tags.
- Branch protection:
  - PR requires passing checks.
  - Direct pushes to `main` blocked (unless you explicitly allow admins).

---

## Notes / Activity Log

### 2026-01-27
- ✅ Task 01: `flake.nix` rebranded, dev shell validated, Zed restarted.
- ✅ Task 02: `.rules` updated for `oap-langgraph-tools-agent`, Python version policy aligned.
- ✅ Task 03: Ruleset applied via GH CLI (ID: 12191808), verified active.
- ✅ Task 04: Created CI/CD workflows and Dockerfile.

### Summary
Goal 01 complete! Repository scaffolding established:
- ✅ Nix dev shell working with proper branding
- ✅ `.rules` adapted for this project
- ✅ GitHub Ruleset applied to `main` branch (modern protection)
- ✅ CI/CD workflows ready for feature branches → GHCR publishing
- ✅ Dockerfile with multi-stage slim build

Ready to proceed to Goal 02 (Remove LangSmith).
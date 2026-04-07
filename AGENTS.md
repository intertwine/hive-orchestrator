# AGENTS

Hive is a v2-first repository.

Start with the `hive` CLI, not ad hoc markdown edits or compatibility shims.

## First Steps

Read `skills/hive-essentials/SKILL.md` before doing anything else. It explains what Hive is, how entities relate, and the key conventions.

## Working Rules

- If you are just using Hive, prefer an installed `hive` CLI in a clean workspace. Checkout-only helpers in this repo are for maintainers.
- Treat `.hive/tasks/*.md` as the canonical task database.
- Treat `projects/*/AGENCY.md` as the narrative project document.
- Read `projects/*/PROGRAM.md` before autonomous edits or evaluator runs.
- If repo-local docs, skills, memory, and current git state disagree, trust current repo state and tests first, then repo-local docs and `PROGRAM.md`.
- Keep `docs/V2_3_STATUS.md` current for the shipped v2.3 line, and keep `docs/V2_4_STATUS.md` current for the active v2.4 release line.
- Before substantial repo work, prefer `make workspace-status`, or check `git status --short`, `git worktree list`, `gh pr status`, and `hive doctor --json` directly.
- In a fresh maintainer worktree, run `uv sync --extra dev` before `pytest` or `make check` so the test-only dependencies are actually installed.
- Build startup context with `hive context startup --project <project-id> --task <task-id> --json`.
- Use `make session PROJECT=<project-id>` only from a repo checkout when you want a saved context file.
- After task, run, or memory changes, refresh projections with `hive sync projections --json`.
- Use `hive driver doctor <driver>` and `hive sandbox doctor <backend>` when debugging runtime or sandbox behavior.
- Before you commit, run `make check`. If your slice touches `frontend/console/**`, console CI wiring, or packaged console validation, also run `make console-check` before review.
- If you request Claude review, treat it as pending until GitHub shows a new Claude comment or review artifact on the latest PR head. An `eyes` reaction alone does not count as completion.
- For maintainer-critical PRs, local Claude review is an acceptable primary or fallback review path when GitHub-managed review is delayed or ambiguous. The built-in `claude -p "/review <pr-number>"` flow works well for this. Summarize the resulting findings in the PR thread.
- After merging, watch the `push` CI run on `main`. A red merge commit is new blocking work, even if the PR checks were green.

## Skills

Skills live in `skills/` (symlinked from both `.agents/skills/` and `.claude/skills/`).

| Skill | When to use |
|-------|-------------|
| `hive-essentials` | Read first — mental model, entities, conventions |
| `hive-work-loop` | Doing task work: claim → run → finish → promote |
| `hive-project-setup` | Bootstrap, project/task CRUD, evaluator policy |
| `hive-coordination` | Multi-agent work, campaigns, portfolio, memory |
| `hive-mcp` | MCP server integration |
| `hive-maintainer` | Developing Hive itself: PRs, reviews, releases |

## Fast Path

```bash
make workspace-status
hive doctor --json
hive console home --json
hive next --json
hive work <task-id> --owner <your-name> --json
make console-check
hive driver doctor codex
hive sandbox doctor local-safe
hive finish <run-id> --json
make check
```

Use the lower-level `task claim` and `context startup` commands only when you need tighter manual control.

## What Not To Do

- Do not treat checkbox lists in `AGENCY.md` as canonical machine state.
- Do not build new automation on `src/cortex.py`; use `hive` commands instead.
- Do not skip `PROGRAM.md` when a project defines evaluator or path policy.
- Do not let a large PR absorb unrelated fixes just because you are already in the code.
- Do not merge because a PR is "probably fine" if review findings are still unresolved.

<!-- hive:begin compatibility -->
## Hive 2.0 compatibility

1. Use the `hive` CLI first.
2. Prefer `--json` for machine-readable operations.
3. Treat `.hive/tasks/*.md` as canonical task state.
4. Read `projects/*/PROGRAM.md` before autonomous edits.
<!-- hive:end compatibility -->

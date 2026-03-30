# CLAUDE

Use Hive through the v2 substrate and CLI.

This repository is CLI-first. If you are operating here, use the commands and files below.

## Working Rules

- If you are just using Hive, prefer an installed `hive` CLI in a clean workspace. Repo checkout helpers are for maintainers.
- Canonical task state lives in `.hive/tasks/*.md`.
- Human project context lives in `projects/*/AGENCY.md`.
- Autonomy policy lives in `projects/*/PROGRAM.md`.
- If repo-local docs, skills, memory, and current git state disagree, trust current repo state and tests first, then repo-local docs and `PROGRAM.md`.
- Keep `docs/V2_3_STATUS.md` current for the shipped v2.3 line, and keep `docs/V2_4_STATUS.md` current for the active v2.4 release line.
- Before substantial repo work, prefer `make workspace-status`, or check `git status --short`, `git worktree list`, `gh pr status`, and `hive doctor --json` directly.
- In a fresh maintainer worktree, run `uv sync --extra dev` before `pytest` or `make check` so the test-only dependencies are actually installed.
- Build context with `hive context startup --project <project-id> --task <task-id> --json`.
- Use `make session PROJECT=<project-id>` only from a repo checkout when you want a saved startup bundle.
- Refresh projections with `hive sync projections --json` after substrate changes.
- Use `hive driver doctor <driver>` and `hive sandbox doctor <backend>` when debugging runtime or sandbox behavior.
- Run `make check` before you hand work back. Before you ask for PR review on a broad slice, make sure the relevant local validation is green.
- If you request Claude review, treat it as pending until GitHub shows a new Claude comment or review artifact on the latest PR head. An `eyes` reaction alone does not count as completion.
- For maintainer-critical PRs, local Claude review is an acceptable primary or fallback review path when GitHub-managed review is delayed or ambiguous. The built-in `claude -p "/review <pr-number>"` flow works well for this. Summarize the resulting findings in the PR thread.
- After merging, watch the `push` CI run on `main`. A red merge commit is new blocking work, even if the PR checks were green.

## Skills

Skills live in `skills/` (symlinked from both `.agents/skills/` and `.claude/skills/`).

Read `hive-essentials` first — it gives you the mental model. Then use the skill that matches your workflow:

- `skills/hive-essentials/SKILL.md` — mental model, entity hierarchy, orientation (read first)
- `skills/hive-work-loop/SKILL.md` — core agent work cycle: claim → work → finish → promote
- `skills/hive-project-setup/SKILL.md` — workspace bootstrap, project/task CRUD, evaluator policy
- `skills/hive-coordination/SKILL.md` — multi-agent coordination, campaigns, portfolio, briefs, memory
- `skills/hive-mcp/SKILL.md` — MCP server integration for host applications
- `skills/hive-maintainer/SKILL.md` — for developing Hive itself: PR discipline, reviews, releases

## Fast Path

```bash
make workspace-status
hive doctor --json
hive console home --json
hive next --json
hive work <task-id> --owner <your-name> --json
hive driver doctor codex
hive sandbox doctor local-safe
hive finish <run-id> --json
make check
```

Use the lower-level `task claim` and `context startup` commands only when you need tighter manual control.

## What Not To Do

- Do not use checkbox lists in `AGENCY.md` as canonical task state.
- Do not build new product logic on `src/cortex.py`.
- Do not run evaluators without checking `PROGRAM.md`.
- Do not let a large PR absorb unrelated fixes just because you are already in the code.
- Do not merge because a PR is "probably fine" if review findings are still unresolved.

For optional GitHub-triggered Claude automation, see `docs/INSTALL_CLAUDE_APP.md`.

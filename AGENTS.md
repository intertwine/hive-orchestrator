# AGENTS

Hive is a v2-first repository.

Start with the `hive` CLI, not ad hoc markdown edits or compatibility shims.

## Working Rules

- If you are just using Hive, prefer an installed `hive` CLI in a clean workspace. Checkout-only helpers in this repo are for maintainers.
- Treat `.hive/tasks/*.md` as the canonical task database.
- Treat `projects/*/AGENCY.md` as the narrative project document.
- Read `projects/*/PROGRAM.md` before autonomous edits or evaluator runs.
- If repo-local docs, skills, memory, and current git state disagree, trust current repo state and tests first, then repo-local docs and `PROGRAM.md`.
- For the current v2.3 line, keep `docs/V2_3_STATUS.md` current as the compact release ledger.
- Before substantial repo work, prefer `make workspace-status`, or check `git status --short`, `git worktree list`, `gh pr status`, and `hive doctor --json` directly.
- Build startup context with `hive context startup --project <project-id> --task <task-id> --json`.
- Use `make session PROJECT=<project-id>` only from a repo checkout when you want a saved context file.
- After task, run, or memory changes, refresh projections with `hive sync projections --json`.
- Use `hive driver doctor <driver>` and `hive sandbox doctor <backend>` when debugging v2.3 runtime or sandbox behavior.
- Before you commit, run `make check`. Before you ask for PR review on a broad slice, make sure the relevant local validation is green.
- If you request Claude review, treat it as pending until GitHub shows a new Claude comment or review artifact on the latest PR head. An `eyes` reaction alone does not count as completion.
- For maintainer-critical PRs, local Claude review is an acceptable primary or fallback review path when GitHub-managed review is delayed or ambiguous. Summarize the resulting findings in the PR thread.
- After merging, watch the `push` CI run on `main`. A red merge commit is new blocking work, even if the PR checks were green.

## Specialized Skills

For heavier workflows, follow the repo skills instead of inventing your own process:

- `.agents/skills/deep-work-session/SKILL.md` for task-first Hive sessions
- `.agents/skills/multi-agent-coordination/SKILL.md` for multi-agent claims, blockers, and handoffs
- `.agents/skills/hive-v23-execution-discipline/SKILL.md` for long-running v2.3/RFC work, mergeable slice planning, review discipline, delegation, and cleanup hygiene

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

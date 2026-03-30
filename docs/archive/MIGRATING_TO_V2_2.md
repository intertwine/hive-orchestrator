# Migrating From Hive 2.1 To 2.2

Archived note: kept as a historical migration record now that Hive 2.2 is long shipped. Prefer `README.md`,
`docs/START_HERE.md`, `docs/QUICKSTART.md`, and `docs/MAINTAINING.md` for current product and maintainer guidance.

Hive 2.2 is not a substrate rewrite. The task, run, memory, and `PROGRAM.md` model from 2.1 stays in place.

What changes in practice:

- the manager loop becomes the default public story: `next`, `work`, `finish`
- the observe-and-steer console becomes the main dashboard surface
- Program Doctor, onboarding, adoption, campaigns, and briefs become first-class product paths
- the driver layer is explicit and normalized across `local`, `manual`, `codex`, and `claude-code`

## What you do not need to change

- canonical task files under `.hive/tasks/*.md`
- project docs in `projects/*/AGENCY.md`
- `PROGRAM.md` evaluator and path policy
- thin MCP usage through `search` and bounded local `execute`

## What you should update

- teach `hive onboard` and `hive adopt` instead of older bootstrap habits
- teach `hive console serve` instead of treating the UI as optional garnish
- teach `hive next` / `hive work` / `hive finish` before the lower-level claim/start/run primitives
- use `hive program doctor` when a project blocks promotion

## Compatibility notes

- `hive dashboard` remains a compatibility alias, but the real product surface is the React console
- `hive run *`, `hive task claim`, and `hive context startup` still work when you need lower-level control

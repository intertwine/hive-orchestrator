---
last_updated: '2026-03-15T00:00:00Z'
priority: medium
project_id: demo
relevant_files:
- projects/demo/AGENCY.md
status: active
tags:
- example
- tutorial
- v2
---

# Demo Project

## Objective

This is the smallest checked-in Hive project that still feels real. It exists to teach the standard loop:

1. find ready work
2. claim it
3. build task-specific context
4. sync projections and leave a clean handoff

## Recommended Flow

```bash
hive task ready --project-id demo
hive task claim <task-id> --owner <your-name> --ttl-minutes 60
hive context startup --project demo --task <task-id>
hive sync projections
```

If you are working from this repository checkout and want a saved prompt bundle, `make session PROJECT=demo` writes the same startup context to `projects/demo/SESSION_CONTEXT.md`. That is a checkout convenience, not the main product path.

## What This Demo Is For

- getting comfortable with the canonical task flow
- seeing how `AGENCY.md` stays readable while `.hive/tasks/*.md` stays canonical
- practicing a tiny docs-only change before you use Hive on a real project

## Notes

- Keep operational truth in `.hive/tasks/*.md`.
- Keep edits inside `projects/demo/**`, `docs/**`, or `README.md` unless you deliberately widen the exercise.
- Read `PROGRAM.md` before any autonomous run or evaluator work.
- The handoff task is lower priority on purpose so the queue teaches "claim first, improve second, wrap up
  last" instead of presenting all three steps as equally urgent.

<!-- hive:begin task-rollup -->
## Task Rollup

| ID | Status | Priority | Owner | Title |
|---|---|---:|---|---|
| task_01KKRC1MF3AS4RW1BDTHJ85ZAR | ready | 1 |  | Claim the first demo task and capture startup context |
| task_01KKRC1MJHZT4E47AN9FTJC0JP | proposed | 1 |  | Make one small docs-only improvement in the demo project |
| task_01KKRC1MNMRCYBRPRBEP5EDWQT | proposed | 2 |  | Sync projections, record the result, and leave a clean handoff |
<!-- hive:end task-rollup -->

<!-- hive:begin recent-runs -->
## Recent Runs

| Run | Status | Task |
|---|---|---|
| No runs | - | - |
<!-- hive:end recent-runs -->

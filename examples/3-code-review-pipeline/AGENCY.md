---
project_id: code-review-pipeline-example
status: active
priority: medium
tags:
- example
- review
- pipeline
- v2
---

# Code Review Pipeline

## Objective

Show how a task moves through a governed run, evaluator feedback, and a final accept or reject decision.

## Recommended Task Shape

- `Implement authentication module`
- optional refinement task if the run is rejected

Use `PROGRAM.md` to define evaluator commands and policy.

## Suggested Commands

```bash
hive run start <task-id> --json
hive run eval <run-id> --json
hive run accept <run-id> --json
```

## Projection Notes

This file should stay readable for humans while the run artifacts live under `.hive/runs/`.

<!-- hive:begin task-rollup -->
Create the implementation task in `.hive/tasks` and let `PROGRAM.md` govern the review loop.
<!-- hive:end task-rollup -->

<!-- hive:begin recent-runs -->
No runs recorded in this example snapshot.
<!-- hive:end recent-runs -->

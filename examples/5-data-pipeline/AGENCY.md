---
project_id: data-pipeline-example
status: active
priority: medium
tags:
- example
- pipeline
- data
- v2
---

# Data Pipeline Workflow

## Objective

Show a stage-based flow where extract, normalize, enrich, load, and validate each live as canonical tasks.

## Recommended Task Shape

- `Extract source data`
- `Normalize records`
- `Enrich records`
- `Load warehouse tables`
- `Validate pipeline output`

Link each stage to the one before it with `blocked_by`.

## Projection Notes

This pattern works best when each stage leaves clear artifacts or accepted run summaries for the next stage.

<!-- hive:begin task-rollup -->
Model each stage as a task in `.hive/tasks` and let the blocker graph control readiness.
<!-- hive:end task-rollup -->

<!-- hive:begin recent-runs -->
No runs recorded in this example snapshot.
<!-- hive:end recent-runs -->

---
project_id: simple-sequential-example
status: active
priority: medium
tags:
- example
- sequential
- v2
---

# Simple Sequential Workflow

## Objective

Show a clean handoff where one canonical task unlocks the next one.

## Recommended Task Shape

- `Research logging options`
- `Implement logger module`

Link the implementation task with `blocked_by` so it becomes ready only after the research task is complete.

## Suggested Commands

```bash
hive task create --project-id simple-sequential-example --title "Research logging options" --json
hive task create --project-id simple-sequential-example --title "Implement logger module" --json
hive task link <implement-task-id> blocked_by <research-task-id> --json
```

## Projection Notes

Canonical task state lives under `.hive/tasks/*.md`. This file is the human-facing project narrative.

<!-- hive:begin task-rollup -->
This static example does not ship live task records. Create them locally with `hive task create`.
<!-- hive:end task-rollup -->

<!-- hive:begin recent-runs -->
No runs recorded in this example snapshot.
<!-- hive:end recent-runs -->

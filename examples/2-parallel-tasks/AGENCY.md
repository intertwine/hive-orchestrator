---
project_id: parallel-tasks-example
status: active
priority: medium
tags:
- example
- parallel
- v2
---

# Parallel Tasks Workflow

## Objective

Show how multiple agents can claim different ready tasks in the same project without stepping on each other.

## Recommended Task Shape

- `Build validators`
- `Build formatters`
- `Build parsers`
- `Build string helpers`

Keep each task isolated to its own file slice when possible.

## Suggested Commands

```bash
hive task ready --project-id parallel-tasks-example --json
hive task claim <task-id> --owner codex-a --json
hive task claim <task-id> --owner codex-b --json
```

## Projection Notes

The lease lives on the canonical task, not in prose or checkbox state.

<!-- hive:begin task-rollup -->
Create your own parallel task set locally and let each agent claim a different task id.
<!-- hive:end task-rollup -->

<!-- hive:begin recent-runs -->
No runs recorded in this example snapshot.
<!-- hive:end recent-runs -->

---
project_id: complex-application-example
status: active
priority: high
tags:
- example
- application
- full-stack
- v2
---

# Complex Application Workflow

## Objective

Show how a larger project uses decomposition, blockers, governed runs, search, and clear handoffs together.

## Recommended Task Shape

- design tasks
- implementation tasks
- testing tasks
- review or release tasks

Use blockers to express order and `PROGRAM.md` to express policy.

## Suggested Commands

```bash
hive deps --json
hive search "auth middleware" --scope workspace
hive run start <task-id> --json
```

## Projection Notes

This is the right pattern when a project stops fitting into a single agent session.

<!-- hive:begin task-rollup -->
Build the task graph in `.hive/tasks` and keep this document focused on architecture, scope, and decisions.
<!-- hive:end task-rollup -->

<!-- hive:begin recent-runs -->
No runs recorded in this example snapshot.
<!-- hive:end recent-runs -->

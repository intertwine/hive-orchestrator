# Complex Application Workflow

Use this pattern when the project needs several Hive primitives at once: decomposition, blockers, governed runs, search, and clear handoffs.

Typical stack:

- project scaffold
- multiple canonical tasks
- linked blockers between phases
- evaluator-backed runs for risky or review-heavy slices
- search and startup context for each handoff

## Suggested Flow

```bash
hive project create app-demo --title "Complex application example" --json
hive task create --project-id app-demo --title "Design API surface" --json
hive task create --project-id app-demo --title "Implement auth" --json
hive task create --project-id app-demo --title "Ship test coverage" --json
```

Then add blockers where needed and use runs on the slices that deserve policy and review.

## Useful Commands

```bash
hive deps --json
hive search "auth middleware" --scope workspace
hive context startup --project app-demo --json
hive run start <task-id> --json
```

This is the pattern to study when you want the closest thing to a production workflow inside Hive.

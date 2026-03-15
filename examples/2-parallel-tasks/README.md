# Parallel Tasks Workflow

Use this pattern when several tasks can move at the same time.

Typical shape:

- one project
- many ready tasks
- each agent claims a different task id

## Hive v2 Flow

```bash
hive project create parallel-demo --title "Parallel tasks workflow" --json
hive task create --project-id parallel-demo --title "Build validators" --json
hive task create --project-id parallel-demo --title "Build formatters" --json
hive task create --project-id parallel-demo --title "Build parsers" --json
hive task create --project-id parallel-demo --title "Build string helpers" --json
```

Then let each agent claim a different task:

```bash
hive task ready --project-id parallel-demo --json
hive task claim <task-id> --owner codex-a --json
hive task claim <task-id> --owner codex-b --json
```

## Why This Pattern Works

- claims are isolated to task ids
- the ready queue makes the work visible to every agent
- projections stay readable even while several tasks move in parallel

## Optional Extras

Use the coordinator if you need extra lock protection across many shells or machines. Keep the canonical lease in Hive either way.

Useful commands:

```bash
hive context startup --project parallel-demo --json
hive sync projections --json
```

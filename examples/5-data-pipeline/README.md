# Data Pipeline Workflow

Use this pattern for stage-based work where each step should unlock the next one cleanly.

Common stages:

1. extract
2. normalize
3. enrich
4. load
5. validate

## Hive v2 Flow

Create one task per stage, then link each later stage to the previous one:

```bash
hive task create --project-id pipeline-demo --title "Extract source data" --json
hive task create --project-id pipeline-demo --title "Normalize records" --json
hive task create --project-id pipeline-demo --title "Load warehouse tables" --json
```

```bash
hive task link <normalize-task-id> blocked_by <extract-task-id> --json
hive task link <load-task-id> blocked_by <normalize-task-id> --json
```

## Why This Pattern Works

- each stage becomes schedulable only when its inputs are ready
- accepted runs can capture artifacts and summaries per stage
- the dependency summary stays readable even when the pipeline grows

Useful commands:

```bash
hive deps --json
hive context startup --project pipeline-demo --json
hive sync projections --json
```

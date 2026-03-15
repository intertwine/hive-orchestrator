# Code Review Pipeline

Use this pattern when implementation should pass through explicit review gates before it is accepted.

## Recommended Shape

1. implementation task
2. evaluator-backed run
3. refine or accept based on the result

## Hive v2 Flow

```bash
hive project create review-demo --title "Code review pipeline" --json
hive task create --project-id review-demo --title "Implement authentication module" --json
```

Start a governed run:

```bash
hive run start <task-id> --json
hive run eval <run-id> --json
```

If the evaluator passes:

```bash
hive run accept <run-id> --json
```

If it fails:

```bash
hive run reject <run-id> --reason "Address evaluator failures" --json
```

## Why This Pattern Works

- `PROGRAM.md` carries the review policy
- the run directory keeps logs, summaries, patches, and evaluator output together
- acceptance becomes an explicit state transition instead of a vague note in prose

## Good Companion Commands

```bash
hive run show <run-id> --json
hive context handoff --project review-demo --json
hive sync projections --json
```

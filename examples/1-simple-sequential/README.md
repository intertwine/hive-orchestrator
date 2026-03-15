# Simple Sequential Workflow

Use this pattern when one task should unlock the next one.

Typical shape:

1. research or design task
2. implementation task blocked on the first task

## Hive v2 Flow

```bash
hive project create simple-sequential --title "Simple sequential workflow" --json
hive task create --project-id simple-sequential --title "Research logging options" --json
hive task create --project-id simple-sequential --title "Implement logger module" --json
hive task link <implement-task-id> blocked_by <research-task-id> --json
```

Agent A:

```bash
hive task claim <research-task-id> --owner codex --json
hive context startup --project simple-sequential --task <research-task-id> --json
```

After Agent A finishes and releases the task, the implementation task becomes ready:

```bash
hive task release <research-task-id> --json
hive task ready --project-id simple-sequential --json
```

Agent B can then claim the second task and continue.

## Why This Pattern Works

- the blocker is explicit in canonical task state
- the handoff shows up in the ready queue naturally
- startup context can include the prior task and recent accepted runs

## Good Companion Commands

```bash
hive deps --json
hive context handoff --project simple-sequential --json
hive sync projections --json
```

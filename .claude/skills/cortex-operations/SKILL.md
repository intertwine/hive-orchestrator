---
name: cortex-operations
description: Operate Hive's ready, dependency, and projection-sync surfaces. Use this skill when someone asks about Cortex commands, ready work, dependency summaries, or the remaining src.cortex compatibility wrapper.
---

# Cortex Operations

Hive 2.0 is CLI-first. `src.cortex` still exists, but only as a compatibility alias for a small set of read and sync actions.

## Use These Commands First

```bash
hive doctor --json
hive task ready --json
hive deps --json
hive sync projections --json
```

If projections or cache look stale, rebuild first:

```bash
hive cache rebuild --json
hive sync projections --json
```

## Old to New Command Map

| Old habit | Preferred command |
|----------|-------------------|
| `python -m src.cortex` | `hive sync projections --json` |
| `python -m src.cortex --ready` | `hive task ready --json` |
| `python -m src.cortex --deps` | `hive deps --json` |

## When `src.cortex` Is Still Fine

Use `python -m src.cortex` only when you are keeping an older script or workflow alive.

Safe compatibility aliases:

```bash
python -m src.cortex
python -m src.cortex --ready --json
python -m src.cortex --deps --json
```

Do not build new automation on top of `src.cortex.py`.

## Common Workflows

### Check workspace health

```bash
hive doctor --json
```

Use this first when the workspace looks incomplete, tasks are missing, or projections do not match the substrate.

### Find schedulable work

```bash
hive task ready --json
```

This is the canonical ready queue. It already accounts for task status, dependencies, and expired claims.

### Inspect blockers

```bash
hive deps --json
```

Use this when ready work is missing, a task seems stranded, or you want the project dependency summary.

### Refresh human-facing views

```bash
hive sync projections --json
```

This regenerates the bounded sections in `GLOBAL.md`, `projects/*/AGENCY.md`, and `AGENTS.md`.

## Troubleshooting

### Projections look stale

```bash
hive cache rebuild --json
hive sync projections --json
```

### A task should be ready but is not

1. Run `hive task show <task-id> --json`
2. Run `hive deps --json`
3. Check for an active or expired claim
4. Check whether another task still blocks it

### A script still calls Cortex

Keep it working for now, but translate the behavior back to `hive` commands before adding more logic.

---
name: hive-operations
description: Operate Hive through the v2 CLI. Use this skill for ready work, blockers, sync, quickstart, or everyday Hive commands in normal usage. For maintainer implementation, large RFC work, or PR/review discipline in this repo, prefer `hive-v23-execution-discipline`.
---

# Hive Operations

Hive is CLI-first. Start with `hive`, not compatibility wrappers.

## Default commands

```bash
hive doctor --json
hive quickstart demo --title "Demo project" --json
hive task ready --json
hive deps --json
hive sync projections --json
```

## Common workflows

### First run

```bash
hive quickstart demo --title "Demo project" --json
```

Use this in an empty workspace when you want a starter project, starter tasks, and a ready queue right away.

### Check workspace health

```bash
hive doctor --json
```

Use this when the workspace looks incomplete, projections are stale, or you are not sure what the next recommended step is.

### Find ready work

```bash
hive task ready --json
```

This is the canonical ready queue. It already accounts for dependencies, status, and expired claims.

### Inspect blockers

```bash
hive deps --json
```

Use this when ready work is missing, a project looks stranded, or you want the project-level dependency summary.

### Refresh projections

```bash
hive cache rebuild --json
hive sync projections --json
```

Run this when task, run, or memory state changed and you want `GLOBAL.md`, `AGENCY.md`, and `AGENTS.md` to reflect it.

## What not to do

- Do not treat `AGENCY.md` checkboxes as canonical task state.
- Do not build new automation on `src.cortex.py`.
- Do not skip `PROGRAM.md` before autonomous work or evaluator runs.

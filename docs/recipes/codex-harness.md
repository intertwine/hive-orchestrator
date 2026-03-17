# Codex Harness Guide

Use the Codex driver when you want Hive to prepare a strong coding run pack and hand the work off to Codex cleanly.

## Good fit

- implementation-heavy slices
- fast patch/test loops
- work where a dedicated worktree and compiled context pack help

## Typical loop

```bash
hive next --project-id <project-id>
hive work <task-id> --driver codex --owner <your-name>
```

Then attach Codex to the prepared run worktree and finish through Hive:

```bash
hive finish <run-id>
```

## What Hive keeps stable

- the run ID
- the task linkage
- the worktree path
- the context manifest
- steering history
- acceptance evidence

Use Codex for the work. Use Hive to keep the record straight.

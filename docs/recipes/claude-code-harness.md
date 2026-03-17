# Claude Code Harness Guide

Use the Claude Code driver when you want the same Hive run model, but a stronger handoff for repo-wide search and synthesis.

## Good fit

- repo-wide refactors
- architectural analysis
- long-form synthesis or cleanup work

## Typical loop

```bash
hive next --project-id <project-id>
hive work <task-id> --driver claude-code --owner <your-name>
```

Then attach Claude Code to the prepared run worktree and finish through Hive:

```bash
hive finish <run-id>
```

## When to reroute into Claude Code

- the run needs broader repo search
- the task has become more synthesis-heavy than implementation-heavy
- you want to preserve the run record but switch workers

The run stays the same run. Only the driver changes.

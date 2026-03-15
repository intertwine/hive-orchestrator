# Cross-Repo Workflows

Use this pattern when Hive coordinates work that will land in another repository.

## What Hive Owns

- task state
- runs and evaluator output
- project memory
- human-facing projections

## What The Target Repo Owns

- the actual code change
- its own branch and PR lifecycle

## Launch-Ready Way To Do It

Hive is local-workspace-first. The cleanest approach today is:

1. clone or mount the target repo into the same workspace
2. create Hive tasks that reference the relevant files
3. use `hive search` and `hive context startup` against that local copy
4. land code changes in the target repo, not in the coordination repo

## Useful Commands

```bash
hive search "retry middleware" --scope workspace
hive context startup --project cross-repo-demo --json
hive task claim <task-id> --owner codex --json
```

If you keep `target_repo` metadata in `AGENCY.md`, treat it as a narrative helper for humans or adapter code, not as canonical machine state.

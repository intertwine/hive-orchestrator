# AGENTS

Hive is a v2-first repository.

Start with the `hive` CLI, not ad hoc markdown edits or compatibility shims.

## Working Rules

- If you are just using Hive, prefer an installed `hive` CLI in a clean workspace. Checkout-only helpers in this repo are for maintainers.
- Treat `.hive/tasks/*.md` as the canonical task database.
- Treat `projects/*/AGENCY.md` as the narrative project document.
- Read `projects/*/PROGRAM.md` before autonomous edits or evaluator runs.
- Build startup context with `hive context startup --project <project-id> --task <task-id> --json`.
- Use `make session PROJECT=<project-id>` only from a repo checkout when you want a saved context file.
- After task, run, or memory changes, refresh projections with `hive sync projections --json`.
- Before you commit, run `make check`.

## Fast Path

```bash
hive doctor --json
hive task ready --json
hive task claim <task-id> --owner <your-name> --ttl-minutes 60 --json
hive context startup --project <project-id> --task <task-id> --json
make check
```

## What Not To Do

- Do not treat checkbox lists in `AGENCY.md` as canonical machine state.
- Do not build new automation on `src/cortex.py`; use `hive` commands instead.
- Do not skip `PROGRAM.md` when a project defines evaluator or path policy.

<!-- hive:begin compatibility -->
## Hive 2.0 compatibility

1. Use the `hive` CLI first.
2. Prefer `--json` for machine-readable operations.
3. Treat `.hive/tasks/*.md` as canonical task state.
4. Read `projects/*/PROGRAM.md` before autonomous edits.
<!-- hive:end compatibility -->

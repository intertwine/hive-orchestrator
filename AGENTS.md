# AGENTS

Hive is now a v2-first repository.

Start with the `hive` CLI, not ad hoc markdown edits and not the old v1 runtime.

## Working Rules

- Treat `.hive/tasks/*.md` as the canonical task database.
- Treat `projects/*/AGENCY.md` as the narrative project document.
- Read `projects/*/PROGRAM.md` before autonomous edits or evaluator runs.
- Build startup context with `hive context startup --project <project-id> --json`.
- After task, run, or memory changes, refresh projections with `hive sync projections --json`.
- Before you commit, run `make check`.

## Fast Path

```bash
hive doctor --json
hive task ready --json
hive context startup --project <project-id> --json
make check
```

## What Not To Do

- Do not treat checkbox lists in `AGENCY.md` as the machine source of truth.
- Do not extend `src/cortex.py` as a new orchestration engine.
- Do not skip `PROGRAM.md` when a project defines evaluator or path policy.

<!-- hive:begin compatibility -->
## Hive 2.0 compatibility

1. Use the `hive` CLI first.
2. Prefer `--json` for machine-readable operations.
3. Treat `.hive/tasks/*.md` as canonical task state.
4. Read `projects/*/PROGRAM.md` before autonomous edits.
<!-- hive:end compatibility -->

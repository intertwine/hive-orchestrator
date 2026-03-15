# CLAUDE

Use Hive through the v2 substrate and CLI.

This repository is CLI-first. If you are operating here, use the commands and files below.

## Working Rules

- If you are just using Hive, prefer an installed `hive` CLI in a clean workspace. Repo checkout helpers are for maintainers.
- Canonical task state lives in `.hive/tasks/*.md`.
- Human project context lives in `projects/*/AGENCY.md`.
- Autonomy policy lives in `projects/*/PROGRAM.md`.
- Build context with `hive context startup --project <project-id> --task <task-id> --json`.
- Use `make session PROJECT=<project-id>` only from a repo checkout when you want a saved startup bundle.
- Refresh projections with `hive sync projections --json` after substrate changes.
- Run `make check` before you hand work back.

## Fast Path

```bash
hive doctor --json
hive task ready --json
hive task claim <task-id> --owner <your-name> --ttl-minutes 60 --json
hive context startup --project <project-id> --task <task-id> --json
make check
```

## What Not To Do

- Do not use checkbox lists in `AGENCY.md` as canonical task state.
- Do not build new product logic on `src/cortex.py`.
- Do not run evaluators without checking `PROGRAM.md`.

For optional GitHub-triggered Claude automation, see `docs/INSTALL_CLAUDE_APP.md`.

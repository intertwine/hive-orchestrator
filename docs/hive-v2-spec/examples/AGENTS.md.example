# Hive 2.0 workspace instructions

This repository uses Hive 2.0.

## Default workflow

1. Use the `hive` CLI first.
2. Prefer JSON output for machine-readable operations:
   - `hive project list --json`
   - `hive task ready --json`
   - `hive run start <task-id> --json`
   - `hive memory search "<query>" --json`
3. Use `hive context startup --project <project-id> --json` at session start.
4. Read the relevant `projects/*/PROGRAM.md` before autonomous edits.

## Source of truth

- Canonical machine task state: `.hive/tasks/*.md`
- Narrative project docs: `projects/*/AGENCY.md`
- Project contract: `projects/*/PROGRAM.md`
- Generated summaries in `GLOBAL.md` / `AGENCY.md` are bounded by `hive:` markers

## Safety rules

- Do not mark work done without running `hive run eval`.
- Do not manually edit generated sections unless explicitly asked.
- Do not write secrets into memory files or run summaries.
- Claims are leases, not permanent locks.

## Interface preference

- Direct CLI is preferred.
- If a thin Code Mode or MCP adapter exists, use it only when you need to compose multiple Hive operations.

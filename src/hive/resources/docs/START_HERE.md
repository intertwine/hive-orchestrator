# Start Here

Hive is a control plane for multi-agent software work.

Use it when you want one system to keep track of tasks, runs, memory, context, and promotion policy across more than one harness.

## Fast path

1. `hive init`
2. `hive quickstart demo --title "Demo project"`
3. `hive work --project-id demo --driver local --json`
4. `hive finish <run-id> --json`

## Core ideas

- Canonical state lives in `.hive/`.
- Human-facing projections live in `GLOBAL.md`, `AGENTS.md`, and project `AGENCY.md`.
- `PROGRAM.md` decides what a run is allowed to do and what must pass before promotion.
- The console lets one operator observe and steer multiple runs without editing Markdown by hand.

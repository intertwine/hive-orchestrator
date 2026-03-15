---
project_id: proj_01JQREK9B1DKYYQ7J0Q2Y7E0XG
title: Hive 2.0 core
status: active
priority: 0
owner: bryan
---

# Hive 2.0 core

## Goal

Ship the first usable Hive 2.0 vertical slice with structured task files, a CLI-first interface, `PROGRAM.md`, run artifacts, and project-local observational memory.

## Why this exists

Hive v1 proved the value of Markdown and Git-native coordination, but it needs a better machine substrate for stable IDs, graph queries, memory, and evaluator-gated autonomous work.

## Architecture notes

- `.hive/tasks/*.md` are canonical.
- `GLOBAL.md` and `AGENCY.md` keep humans oriented.
- `PROGRAM.md` is mandatory for autonomous runs.
- CLI is primary; a thin Code Mode adapter is optional.

<!-- hive:begin task-rollup -->
## Task rollup

| Task | ID | Status | Priority | Owner | Notes |
|---|---|---:|---:|---|---|
| Define canonical task file schema | task_01JQRF1Y6S0Q2J92VA86G4T45G | done | 0 | bryan | imported and accepted |
| Build CLI-first task surface | task_01JQRF3N0T4SR1Z8ZP6TRV1Q4N | in_progress | 0 | codex | current active slice |
| Add project-local observer / reflector memory | task_01JQRF5QXB0Q3E0A3G6AV6BXZ8 | ready | 1 |  | blocked only on CLI helpers |
| Add thin Code Mode adapter | task_01JQRF7BSAK6M7D5XCA3D2GH4K | ready | 1 |  | optional feature-flagged path |

<!-- hive:end task-rollup -->

<!-- hive:begin recent-runs -->
## Recent accepted runs

- `run_01JQRG4G4E4VKSWZ8SX8D6W7PR` — scaffolded `.hive/` layout and task parser
- `run_01JQRG6QAKY9KX1Y3PAW85TRB1` — projection sync for `AGENCY.md`

<!-- hive:end recent-runs -->

## Human notes

The first release should prove the architecture, not boil the ocean. CLI-first matters more than any optional MCP work.

---
project_id: agent-dispatchers-example
status: active
priority: medium
tags:
- example
- dispatchers
- adapters
- v2
relevant_files:
- src/agent_dispatcher.py
- src/context_assembler.py
- examples/8-agent-dispatchers/README.md
---

# Agent Dispatchers

## Objective

Show how a custom adapter can route ready Hive work into another agent surface without taking ownership of canonical state.

## Recommended Adapter Inputs

- `hive task ready --json`
- `hive context startup --project ... --task ... --json`
- `hive task claim ... --json`

## Projection Notes

Dispatchers should stay thin. They should ask Hive for state, deliver context outward, and then claim the chosen task.

<!-- hive:begin task-rollup -->
Do not mutate this file directly to claim work. Use canonical task claims instead.
<!-- hive:end task-rollup -->

<!-- hive:begin recent-runs -->
No runs recorded in this example snapshot.
<!-- hive:end recent-runs -->

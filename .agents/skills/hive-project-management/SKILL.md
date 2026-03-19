---
name: hive-project-management
description: Manage Hive projects through the v2 substrate and projections. Use this skill when creating projects, tasks, claims, links, or project policy. For repo-maintainer v2.3 implementation and PR trains in this repo, use `hive-v23-execution-discipline` for execution discipline and use this skill only for the substrate operations themselves.
---

# Hive Project Management

Hive project management is substrate-first:

- `.hive/tasks/*.md` is canonical task state
- `projects/*/AGENCY.md` is the narrative project document
- `projects/*/PROGRAM.md` defines evaluator and execution policy
- `GLOBAL.md` and `AGENTS.md` are projections

## Create a Project

```bash
hive project create demo --title "Demo project" --json
hive project show demo --json
```

This scaffolds:

- `projects/demo/AGENCY.md`
- `projects/demo/PROGRAM.md`

## Create and Manage Tasks

Create work in the substrate:

```bash
hive task create --project-id demo --title "Define the first slice" --json
hive task create --project-id demo --title "Implement the first slice" --json
```

Inspect and update:

```bash
hive task list --project-id demo --json
hive task show <task-id> --json
hive task update <task-id> --status in_progress --priority 1 --json
```

Claim and release leases:

```bash
hive task claim <task-id> --owner codex --ttl-minutes 30 --json
hive task release <task-id> --json
```

Link dependencies:

```bash
hive task link <blocked-task-id> blocked_by <unblocking-task-id> --json
```

## Build Context and Refresh Views

```bash
hive context startup --project demo --json
hive sync projections --json
```

Use `hive sync projections` after meaningful task, run, or memory changes so the human-facing docs stay current.

## Use `PROGRAM.md` On Purpose

Read `projects/<project>/PROGRAM.md` before:

- running evaluators
- broad file edits
- autonomous command execution
- accepting or escalating runs

If the work needs new guardrails, update `PROGRAM.md` rather than inventing ad hoc rules in prompts.

## Rules of Thumb

- Do not treat checkbox lists in `AGENCY.md` as machine state.
- Do not use the project `owner` field as the primary locking mechanism.
- Use task claims for work leases and task links for blockers.
- Keep `AGENCY.md` readable and narrative; keep operational truth in `.hive/`.

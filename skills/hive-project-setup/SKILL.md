---
name: hive-project-setup
description: Set up and configure Hive workspaces, projects, tasks, and evaluator policy. Use this skill when bootstrapping, creating projects, managing tasks, or configuring PROGRAM.md.
---

# Hive Project Setup

This skill covers workspace bootstrap, project creation, task management, and evaluator configuration.

## Bootstrap a New Workspace

### Full onboarding (recommended)

```bash
hive onboard <project-slug> --json
```

This creates:
- `.hive/` substrate directory with cache and task storage
- `projects/<slug>/AGENCY.md` — narrative project document
- `projects/<slug>/PROGRAM.md` — execution policy with forgiving defaults
- 3–5 starter tasks with dependency chains
- `local-smoke` evaluator template
- Workspace checkpoint commit

Default PROGRAM.md uses forgiving settings so the first `hive finish` succeeds cleanly:
- `auto_close_task: true`
- `allow_accept_without_changes: true`

Tighten these for production use.

### Minimal init

```bash
hive init --json
```

Creates the `.hive/` layout only. No starter project or tasks.

### Adopt an existing repo

```bash
hive adopt <project-slug> --json
```

Wraps existing v1 state and enables v2 features incrementally.

### Migrate from v1

```bash
hive migrate v1-to-v2 --dry-run --json     # preview
hive migrate v1-to-v2 --project <id> --json # execute
```

## Create and Manage Projects

```bash
hive project create <slug> --title "Project title" --json
hive project list --json
hive project show <project-id> --json
hive project sync --json
```

Each project gets:
- `projects/<slug>/AGENCY.md` — write narrative context here (objective, notes, recommended flow)
- `projects/<slug>/PROGRAM.md` — define execution policy here

## Create and Manage Tasks

### Task CRUD

```bash
hive task create --project-id <id> --title "Task title" --json
hive task create --project-id <id> --title "..." --status ready --json
hive task list --project-id <id> --json
hive task list --status ready,review --json
hive task show <task-id> --json
hive task update <task-id> --status in_progress --priority 1 --json
hive task update <task-id> --title "New title" --label "bug" --json
```

### Task status flow

`proposed` → `ready` → `claimed` → `in_progress` → `review` → `done`

Side states: `blocked` (manual), `archived` (deprecated).

### Priority levels

0 = critical, 1 = high, 2 = medium, 3 = low. `hive next` returns highest priority first.

### Task dependencies

```bash
hive task link <blocked-id> blocked_by <blocker-id> --json
hive task link <parent-id> parent_of <child-id> --json
hive task link <id-a> relates_to <id-b> --json
hive deps --json     # project-level blocker summary
```

Edge types: `blocks`, `parent_of`, `relates_to`, `duplicates`, `supersedes`.

### Claims

```bash
hive task claim <task-id> --owner <name> --ttl-minutes 30 --json
hive task release <task-id> --json
```

Claims are time-limited work leases. Use them, not hand-edited owner fields in AGENCY.md.

## Configure Evaluator Policy

### Inspect current policy

```bash
hive program doctor <project-id> --json
```

This shows the current PROGRAM.md state, available evaluator templates, and any policy issues.

### Add an evaluator

```bash
hive program add-evaluator <project-id> local-smoke --json
```

Available templates:
- `local-smoke` — minimal validation stub, proves the evaluator loop works

Custom evaluators can be defined directly in PROGRAM.md.

### PROGRAM.md structure

```yaml
program_version: 1
mode: workflow
default_executor: local
budgets:
  max_wall_clock_minutes: 30
  max_steps: 25
  max_tokens: 20000
  max_cost_usd: 2.0
paths:
  allow:
    - README.md
    - docs/**
    - projects/<project>/**
  deny:
    - secrets/**
    - infra/prod/**
commands:
  allow: []
  deny:
    - rm -rf /
evaluators: []
promotion:
  allow_unsafe_without_evaluators: false
  auto_close_task: true
  requires_all: []
escalation:
  when_paths_match: []
  when_commands_match: []
```

Read PROGRAM.md before:
- Running evaluators
- Broad file edits
- Autonomous command execution
- Accepting or escalating runs

If work needs new guardrails, update PROGRAM.md rather than inventing ad hoc rules.

## Workspace Maintenance

### Checkpoint

```bash
hive workspace checkpoint --message "before refactor" --json
```

Creates a git commit to freeze workspace state. `hive work` does this automatically before launching runs.

### Refresh projections

```bash
hive cache rebuild --json
hive sync projections --json
```

Run this after task, run, or memory changes so GLOBAL.md, AGENCY.md task rollups, and AGENTS.md stay current.

### Health check

```bash
hive doctor --json              # full workspace health
hive doctor workspace --json    # workspace structure only
hive doctor program --json      # PROGRAM.md policy check
```

## Rules of Thumb

- Canonical task state lives in `.hive/tasks/*.md`. AGENCY.md is narrative, not machine state.
- Keep AGENCY.md readable and human-oriented. Keep operational truth in `.hive/`.
- Use task claims for work leases and task links for blockers.
- Start with forgiving defaults (`auto_close_task`, `allow_accept_without_changes`) and tighten for production.
- Do not use the project `owner` field as the primary locking mechanism — use task claims.

---
name: hive-essentials
description: Hive mental model and orientation. Read this first before using any other Hive skill. Covers the entity hierarchy, observe-and-steer pattern, drivers, sandboxes, console vs CLI, and workspace conventions.
---

# Hive Essentials

Read this before the other Hive skills. It gives you the mental model; the other skills give you the workflows.

## What Hive Is

Hive is an agentic workflow orchestrator. It manages parallel task execution across multiple agents (human or LLM) with governance, evaluation, and observability.

The console is the primary interface for humans. The CLI is the primary interface for agents. Both read and write the same underlying state.

## Entity Hierarchy

```
Workspace
├── Projects          (goals with policy)
│   ├── AGENCY.md     (narrative context for humans)
│   └── PROGRAM.md    (execution policy: budgets, allowed paths, evaluators)
├── Tasks             (units of work, canonical in .hive/tasks/*.md)
│   ├── status        (proposed → ready → claimed → in_progress → review → done)
│   ├── claims        (time-limited work leases)
│   └── links         (blocks, parent_of, relates_to, duplicates, supersedes)
├── Runs              (governed execution attempts on a task)
│   ├── worktree      (isolated git branch)
│   ├── transcript    (event stream)
│   ├── approvals     (driver ↔ human round-trip)
│   └── eval_results  (evaluator decision)
├── Campaigns         (multi-task orchestration with lanes and cadence)
│   └── Lanes         (exploit, explore, review, maintenance)
└── Memory            (observations and reflections, review-gated)
```

## The Observe-and-Steer Pattern

Hive separates execution from judgment:

1. **Agents execute.** They claim tasks, launch runs, produce artifacts.
2. **Evaluators gate.** PROGRAM.md defines what passes. Runs are accepted, rejected, or escalated.
3. **Humans steer.** Via console or CLI, they approve, pause, reroute, or cancel runs. They set policy in PROGRAM.md.

As an agent, your job is to execute within policy and surface decisions that need human judgment. You do not self-approve governed runs unless the evaluator policy allows it.

## Drivers

Drivers are the execution backends that actually run agent work. Each driver has different capabilities.

| Driver | What it does | Key capabilities |
|--------|-------------|------------------|
| `local` | Runs commands in a subprocess | Always available, no scheduling |
| `manual` | Human-in-the-loop placeholder | Interactive, no automation |
| `codex` | OpenAI Codex integration | Async, stateful, supports approvals |
| `claude` | Claude SDK adapter | Async, stateful, supports approvals |
| `pi` | Staged/honest driver | Available, RPC depth deferred |

Check what is available:

```bash
hive drivers list --json
hive driver doctor <driver-name> --json
```

## Sandboxes

Sandboxes provide execution isolation for runs.

| Backend | Isolation | When to use |
|---------|-----------|-------------|
| `podman` | Container (rootless) | Default for safe local runs |
| `docker-rootless` | Container | Alternative to podman |
| `e2b` | Managed cloud | Ephemeral, upload-only sandboxes |
| `daytona` | Remote | Team/self-hosted environments |

Check what is available:

```bash
hive sandbox doctor <backend-name> --json
```

## Console vs CLI

The **console** (`hive console open`) is a React dashboard for humans. It shows:
- Project cards and task queues
- Active runs with progress phases
- Pending approvals and escalations
- Campaign lanes and allocation

The **CLI** (`hive <command> --json`) is for agents and power users. It accesses the same state. Use `--json` on every command for machine-readable output.

As an agent, use the CLI. But be aware that a human may be watching your work in the console and may steer runs or approve requests through it.

## Workspace Layout

```
.hive/
  tasks/          canonical task state (markdown with YAML frontmatter)
  runs/           run metadata, transcripts, artifacts, eval results
  memory/         observations and reflections (per-project and global)
  cache/          SQLite index (rebuildable)
  campaigns/      campaign state and decision logs

projects/
  <project-id>/
    AGENCY.md     narrative project context (human-readable, not machine state)
    PROGRAM.md    execution policy (budgets, paths, evaluators, promotion rules)
```

## Key Conventions

- **`--json` everywhere.** Every CLI command supports `--json` as a global flag. Always use it for structured output.
- **Task state is canonical.** `.hive/tasks/*.md` is the source of truth, not AGENCY.md checkboxes.
- **PROGRAM.md gates autonomy.** Read it before running evaluators, broad file edits, or autonomous commands.
- **Claims are leases.** Use `hive task claim` with `--ttl-minutes` to hold work. Release when done.
- **Projections are derived.** GLOBAL.md, AGENTS.md, and AGENCY.md task rollups are generated from substrate state. Refresh with `hive sync projections --json`.

## Orientation Commands

When you arrive in a Hive workspace:

```bash
hive doctor --json                    # workspace health check
hive task ready --json                # what work is available
hive deps --json                      # dependency/blocker summary
hive console home --json              # dashboard state as JSON
hive drivers list --json              # available execution backends
```

## Bootstrap a New Workspace

```bash
hive onboard <project-slug> --json    # full setup: project, tasks, evaluator template
```

This creates a project with AGENCY.md, PROGRAM.md, starter tasks with dependency chains, and a `local-smoke` evaluator template. The defaults are forgiving: `auto_close_task: true` and `allow_accept_without_changes: true` so first runs succeed cleanly.

`hive quickstart` is a legacy alias for `hive onboard`.

## Next Skills

Once you understand the mental model:

- **`hive-work-loop`** — the core agent work cycle (claim → work → finish → promote)
- **`hive-project-setup`** — creating and configuring projects, tasks, and evaluators
- **`hive-coordination`** — multi-agent patterns, campaigns, and portfolio management
- **`hive-mcp`** — MCP server integration for host applications
- **`hive-maintainer`** — for developing Hive itself (PR discipline, releases)

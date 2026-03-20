# Agent Hive

[![CI](https://img.shields.io/github/actions/workflow/status/intertwine/hive-orchestrator/ci.yml?branch=main&label=CI)](https://github.com/intertwine/hive-orchestrator/actions/workflows/ci.yml)
[![Hive Projection Sync](https://img.shields.io/github/actions/workflow/status/intertwine/hive-orchestrator/projection-sync.yml?branch=main&label=Projection%20Sync)](https://github.com/intertwine/hive-orchestrator/actions/workflows/projection-sync.yml)

![Agent Hive observe-and-steer console](images/launch/console-home.png)

Agent Hive is a repo-native control plane for autonomous work. Keep your favorite worker harness, whether that is Codex, Claude Code, or a local/manual loop, and use Hive to supervise tasks, runs, memory, approvals, and campaigns from one place.

**Keep your agent. Add a control plane.**

If you are already using coding agents and feeling the limits of isolated sessions, Agent Hive is the layer that makes them feel like part of one real system:

- one command center above many runs and many projects
- one governed loop instead of “the agent said it was done”
- one inspectable substrate instead of hidden agent state
- one place to steer Codex, Claude Code, local execution, and manual handoffs

The center of gravity in this repository is the Hive v2 substrate, with the current release line focused on a truthful v2.3 operator surface.

## Why It Feels Different

- The console is not a toy dashboard. It is a real observe-and-steer command center with active runs, inbox items, campaign reasoning, retrieval traces, and run detail in one place.
- Hive does not replace your worker harness. It sits above it, so you can keep using Codex, Claude Code, local execution, or manual loops.
- Agents do not decide when they are done. `PROGRAM.md` evaluators and promotion policy do.
- Machine state stays explicit. Tasks, runs, memory, events, briefs, and campaigns live in predictable files instead of hidden session state.
- You can get to a real governed loop in minutes, not after wiring up a framework.

## Try It In 90 Seconds

The shortest honest path is:

```bash
uv tool install mellona-hive
mkdir my-hive && cd my-hive
git init
hive onboard demo --prompt "Create a small React website about bees."
hive next --project-id demo
hive work --owner <your-name>
```

If you want the live operator view, install `mellona-hive[console]` first and run:

```bash
hive console serve
```

Then finish the run:

```bash
hive finish <run-id>
```

What should happen:

- `hive onboard demo` leaves you with a real workspace, starter project, safe `PROGRAM.md`, and one ready task
- `hive work` starts a governed run, prints the run worktree path, and can write a handoff bundle for your worker harness
- `hive finish` either promotes a real change or cleanly tells you there was nothing to promote yet

If that first `hive finish` reports no changes, that is usually a healthy noop, not a broken setup. To intentionally
see a successful first promotion, make one tiny docs-only change while working the demo task, then finish the run.
Make that change inside the run worktree that `hive work` printed for you, usually `.hive/worktrees/run_<id>/`.

## Start Here

There are three clean ways into Hive:

- [Install Hive](docs/START_HERE.md) if you want a fresh workspace and the shortest path to real work
- [Adopt Hive in an existing repo](docs/ADOPT_EXISTING_REPO.md) if you already have a codebase and want Hive inside it
- [Maintain or publish Hive](docs/MAINTAINING.md) if you are working on this repository itself

If you only read one more page after this README, make it [docs/START_HERE.md](docs/START_HERE.md).

## Install Hive

`mellona-hive` is the package you install. Mellona is the distribution family, Agent Hive is the current product,
and the install gives you the `hive` command.

Use [docs/START_HERE.md](docs/START_HERE.md) for the canonical install matrix, optional extras, and git-install
fallback. The fastest base install for most users is:

```bash
uv tool install mellona-hive
```

```bash
hive --version
hive doctor
```

Add `mellona-hive[console]` when you want `hive console serve`, and add `mellona-hive[mcp]` when you want the thin
`hive-mcp` adapter.

If you plan to use hosted or self-hosted sandbox execution, add the backend extras you need:

- `uv tool install --upgrade 'mellona-hive[sandbox-e2b]'`
- `uv tool install --upgrade 'mellona-hive[sandbox-daytona]'`

Then verify what this machine can really support:

```bash
hive sandbox doctor --json
```

## Five-Minute First Run

Start in an empty directory and let Hive onboard the workspace for you:

```bash
mkdir my-hive
cd my-hive
git init
hive onboard demo --prompt "Create a small React website about bees."
```

That gives you a real workspace with `.hive/`, a starter project, a safe default `PROGRAM.md`, and the first task
chain. If you want the React observe-and-steer console, install `mellona-hive[console]` first, then run
`hive console serve`. The longer walkthrough lives in [docs/QUICKSTART.md](docs/QUICKSTART.md).

Fresh onboarded projects may start with the placeholder `local-smoke` evaluator so the first governed loop works
immediately. Replace it with a real repo-specific evaluator before you trust autonomous promotion.

What a healthy first pass looks like:

- `hive onboard demo` leaves you with one ready task and a safe starter `PROGRAM.md`
- `hive work` starts a governed run, prints the run worktree path, and can write a handoff bundle for your worker harness
- a first `hive finish` may either promote a real change or cleanly say there was nothing to promote yet

If that first `hive finish` reports no changes, that is usually a healthy noop, not a broken setup. To intentionally
see a successful first promotion, make one tiny docs-only change while working the demo task, then finish the run.
Make that change inside the run worktree that `hive work` printed for you, usually `.hive/worktrees/run_<id>/`.

If the promoted task lands in `review`, close it explicitly to unblock the next task in the starter chain:

```bash
hive task update <task-id> --status done
```

Do this in a fresh workspace, not inside this repository checkout. This repo carries its own real maintainer task queue, so `hive task ready` here will show Hive's work unless you filter to `--project-id demo`.

Once the workspace exists, the normal loop is:

```bash
hive next --project-id demo
hive work --owner <your-name>
hive finish <run-id>
```

`hive finish` evaluates the run, accepts or escalates it, and promotes accepted work back into the workspace by
default. Open the console when you want the live run board, inbox, campaigns, project summaries, and run detail in one
place.

## Adopt Hive In An Existing Repo

You do not need to start over to use Hive.

If you already have a repository:

```bash
cd your-repo
hive adopt app --title "App"
```

From there, either keep the guided adoption path or import an older checklist-based Hive setup with
`hive migrate v1-to-v2`. The full path is documented in
[docs/ADOPT_EXISTING_REPO.md](docs/ADOPT_EXISTING_REPO.md).

## Everyday Loop

Once the workspace exists, the daily path is short:

```bash
hive next
hive work --owner <your-name>
hive finish <run-id>
```

If you want to stay closer to the underlying primitives, `hive task ready`, `hive task claim`, `hive context startup`,
and `hive run start` are still there. `--json` is available across the CLI when you want to script Hive instead of
reading it by eye.

When you want the live operator view instead of the raw CLI, install `mellona-hive[console]` first and run:

```bash
hive console serve
```

That starts the observe-and-steer console. From there you can watch active runs, review inbox items, inspect context,
see acceptance rationale, and steer runs without editing Markdown by hand.

When you are defining new work instead of just taking ready work, stay in the CLI:

```bash
hive task create \
  --project-id <project-id> \
  --title "Add the next thin slice" \
  --label launch \
  --relevant-file src/app.py \
  --acceptance "Tests pass for the new slice."
```

## Optional Integrations

These are useful, but the base CLI works fine without them:

- `hive console serve` after installing `mellona-hive[console]`
- `hive-mcp` after installing `mellona-hive[mcp]`
- the optional Claude Code GitHub App flow in [docs/INSTALL_CLAUDE_APP.md](docs/INSTALL_CLAUDE_APP.md)

The MCP surface stays intentionally small: `search` and `execute`. `execute` is a bounded local Python helper, not a
full sandbox.

## Compare Harnesses

Hive does not ask you to switch worker tools. It gives them a shared control layer.

- Codex is strong when you want a powerful coding worker with worktree-aware runs and good local iteration.
- Claude Code is strong when you want broader repo search, longer synthesis, and a handoff-friendly transcript pack.
- Local and manual drivers are useful when you want bounded execution, custom tooling, or a human review step.

The longer comparison lives in [docs/COMPARE_HARNESSES.md](docs/COMPARE_HARNESSES.md).

## Core Model

| File or directory | Purpose |
|---|---|
| `.hive/tasks/*.md` | Canonical task records |
| `.hive/runs/*` | Run artifacts, evaluator output, logs, patch data |
| `.hive/memory/` | Project-local observational memory |
| `.hive/events/*.jsonl` | Append-only audit log |
| `.hive/cache/index.sqlite` | Derived query cache |
| `projects/*/AGENCY.md` | Human project document and bounded rollups |
| `projects/*/PROGRAM.md` | Policy for autonomous work |
| `GLOBAL.md` | Top-level workspace orientation |
| `AGENTS.md` | Short compatibility shim for coding harnesses |

## More Docs

- [docs/START_HERE.md](docs/START_HERE.md) for the lane chooser and install matrix
- [docs/QUICKSTART.md](docs/QUICKSTART.md) for the fresh-workspace walkthrough
- [docs/ADOPT_EXISTING_REPO.md](docs/ADOPT_EXISTING_REPO.md) for existing repositories and legacy imports
- [docs/DEMO_WALKTHROUGH.md](docs/DEMO_WALKTHROUGH.md) for the current demo walkthrough, screenshots, and narration built on the multi-project launch fixture
- [docs/COMPARE_HARNESSES.md](docs/COMPARE_HARNESSES.md) for Codex, Claude Code, and local/manual guidance
- [docs/UI_INFORMATION_ARCHITECTURE.md](docs/UI_INFORMATION_ARCHITECTURE.md) for the console information architecture
- [docs/OPERATOR_FLOWS.md](docs/OPERATOR_FLOWS.md) for the manager loop and steering flows
- [docs/MAINTAINING.md](docs/MAINTAINING.md) for source-checkout work
- [docs/RELEASING.md](docs/RELEASING.md) for tagged releases, PyPI, and Homebrew
- [docs/recipes/sandbox-doctor.md](docs/recipes/sandbox-doctor.md) for sandbox profiles, extras, and doctor output

## Maintainers

This repository runs on the same Hive v2 substrate it ships, but the source checkout is still a maintainer
surface, not the normal installed-user path. If you are here to work on Hive itself, start with
[docs/MAINTAINING.md](docs/MAINTAINING.md).

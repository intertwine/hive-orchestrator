# Agent Hive

[![CI](https://img.shields.io/github/actions/workflow/status/intertwine/hive-orchestrator/ci.yml?branch=main&label=CI)](https://github.com/intertwine/hive-orchestrator/actions/workflows/ci.yml)
[![Hive Projection Sync](https://img.shields.io/github/actions/workflow/status/intertwine/hive-orchestrator/projection-sync.yml?branch=main&label=Projection%20Sync)](https://github.com/intertwine/hive-orchestrator/actions/workflows/projection-sync.yml)

![Agent Hive](images/agent-hive-explainer-image-web.png)

Agent Hive is a CLI-first orchestration platform for autonomous agents. It keeps machine state in a Git-friendly substrate under `.hive/`, keeps human context in Markdown, and gives agents a stable command surface instead of brittle prompt rituals.

The center of gravity in this repository is Hive 2.0:

- `hive` is the primary interface.
- `.hive/tasks/*.md` is the canonical task store.
- `projects/*/AGENCY.md` stays human-readable.
- `projects/*/PROGRAM.md` defines evaluator, path, and command policy.
- `GLOBAL.md` and `AGENTS.md` are bounded projections, not the machine database.

## Why Hive

- It keeps the machine state explicit. Tasks, runs, memory, events, and cache live in predictable files.
- It keeps humans in the loop. Project docs stay readable, diffable, and easy to review.
- It gives agents a real operating surface. Ready work, claims, runs, evaluators, search, context assembly, and migration are all available through the CLI.

## Start Here

There are three clean ways into Hive:

- [Install Hive](docs/START_HERE.md) if you want a fresh workspace and the shortest path to real work
- [Adopt Hive in an existing repo](docs/ADOPT_EXISTING_REPO.md) if you already have a codebase and want Hive inside it
- [Maintain or publish Hive](docs/MAINTAINING.md) if you are working on this repository itself

## Install Hive

Pick the installer you already trust:

```bash
uv tool install agent-hive
```

```bash
pipx install agent-hive
```

```bash
python -m pip install agent-hive
```

```bash
brew tap intertwine/tap
brew install intertwine/tap/agent-hive
```

Then verify:

```bash
hive --version
hive doctor
```

Optional extras:

| Installer | Dashboard | MCP adapter | Notes |
|---|---|---|---|
| `uv tool` | `uv tool install --upgrade 'agent-hive[dashboard]'` | `uv tool install --upgrade 'agent-hive[mcp]'` | Cleanest path for most users |
| `pipx` | `pipx install 'agent-hive[dashboard]'` | `pipx install 'agent-hive[mcp]'` | Best if you already use `pipx` |
| `pip` | `python -m pip install 'agent-hive[dashboard]'` | `python -m pip install 'agent-hive[mcp]'` | Best inside your own virtualenv |
| Homebrew | use one of the Python package installs above | use one of the Python package installs above | Homebrew currently ships the base CLI |

If you are reading this before the first tagged public release lands on PyPI and Homebrew, use the git install:

```bash
uv tool install --from git+https://github.com/intertwine/hive-orchestrator.git agent-hive
```

## Five-Minute First Run

Start in an empty directory and let Hive scaffold the first useful project:

```bash
mkdir my-hive
cd my-hive
git init
hive quickstart demo --title "Demo project"
hive workspace checkpoint --message "Bootstrap Hive workspace"
hive task ready --project-id demo
hive task claim <task-id> --owner <your-name> --ttl-minutes 60
hive context startup --project demo --task <task-id>
```

If you want a reusable bundle for Claude, Codex, or another agent session, write it directly:

```bash
hive context startup --project demo --task <task-id> --output SESSION_CONTEXT.md
```

That gives you a real workspace with `.hive/`, a starter project, a conservative `PROGRAM.md`, and a small task
chain that teaches the normal claim-and-context loop. The longer walkthrough lives in
[docs/QUICKSTART.md](docs/QUICKSTART.md).

Do this in a fresh workspace, not inside this repository checkout. This repo carries its own real maintainer task queue, so `hive task ready` here will show Hive's work unless you filter to `--project-id demo`.

If you want the full governed run loop, checkpoint the new workspace once, then:

```bash
hive run start <task-id>
hive run eval <run-id>
hive run accept <run-id> --promote --cleanup-worktree
```

Use `hive run cleanup --terminal` later if you want to prune old terminal worktrees in one pass.

## Adopt Hive In An Existing Repo

You do not need to start over to use Hive.

If you already have a repository:

```bash
cd your-repo
hive init
```

From there, either create a first project with `hive project create` or import an older checklist-based Hive setup
with `hive migrate v1-to-v2`. The full path is documented in
[docs/ADOPT_EXISTING_REPO.md](docs/ADOPT_EXISTING_REPO.md).

## Everyday Loop

Once the workspace exists, the daily path is short:

```bash
hive task ready
hive task claim <task-id> --owner <your-name> --ttl-minutes 60
hive context startup --project <project-id> --task <task-id>
hive run start <task-id>
```

If you are still following the demo project, use `hive task ready --project-id demo`. In a multi-project workspace, plain `hive task ready` shows the cross-project queue.
`--json` is available across the CLI when you want to script Hive instead of reading it by eye.

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

- `hive dashboard` after installing `agent-hive[dashboard]`
- `hive-mcp` after installing `agent-hive[mcp]`
- the optional Claude Code GitHub App flow in [docs/INSTALL_CLAUDE_APP.md](docs/INSTALL_CLAUDE_APP.md)

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
- [docs/MAINTAINING.md](docs/MAINTAINING.md) for source-checkout work
- [docs/RELEASING.md](docs/RELEASING.md) for tagged releases, PyPI, and Homebrew

## Maintainers

This repository runs on the same Hive 2.0 substrate it ships, but the source checkout is still a maintainer
surface, not the normal installed-user path. If you are here to work on Hive itself, start with
[docs/MAINTAINING.md](docs/MAINTAINING.md).

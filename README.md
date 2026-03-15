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

## Install

### Everyday users

Pick the install path you already trust:

```bash
uv tool install agent-hive
hive --version
hive doctor
```

```bash
pipx install agent-hive
hive --version
hive doctor
```

```bash
brew tap intertwine/tap
brew install intertwine/tap/agent-hive
hive --version
hive doctor
```

If you already manage a virtualenv yourself, `python -m pip install agent-hive` works too.

If you want optional extras, install them explicitly:

- Dashboard: `uv tool install --upgrade 'agent-hive[dashboard]'`
- MCP server: `uv tool install --upgrade 'agent-hive[mcp]'`

If you're reading this before the first tagged public release lands on PyPI and Homebrew, use the git install:

```bash
uv tool install --from git+https://github.com/intertwine/hive-orchestrator.git agent-hive
```

### Maintainers

If you are developing Hive itself, start from a checkout instead:

```bash
git clone https://github.com/intertwine/hive-orchestrator.git
cd hive-orchestrator
make install-dev
make install-tool
```

Use [docs/MAINTAINING.md](docs/MAINTAINING.md) for local development, CI, and release workflow details.

## Five-Minute First Run

Start in an empty directory and let Hive scaffold the first useful project:

```bash
mkdir my-hive
cd my-hive
hive quickstart demo --title "Demo project"
hive task ready
hive context startup --project demo
```

If you want a reusable bundle for Claude, Codex, or another agent, save it directly:

```bash
hive context startup --project demo --output SESSION_CONTEXT.md
```

That gives you a real workspace with `.hive/`, a starter project, a conservative `PROGRAM.md`, and a first task chain with one ready task. The longer walkthrough lives in [docs/QUICKSTART.md](docs/QUICKSTART.md).

`--json` is available for automation. The commands above are the normal human path.

## Everyday Loop

Once the workspace exists, the daily path is short:

```bash
hive task ready
hive task claim <task-id> --owner <your-name> --ttl-minutes 60
hive context startup --project demo --task <task-id>
hive sync projections
```

Optional extras:

- Run `hive dashboard` after installing `agent-hive[dashboard]` if you want a visual workspace view.
- Run `hive-mcp` after installing `agent-hive[mcp]` if you want the thin search and execute MCP surface.

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

## Typical Workflow

1. Create or sync a workspace with `hive init` and `hive sync projections`.
2. Scaffold a project with `hive project create`.
3. Create canonical tasks with `hive task create`.
4. Use `hive task ready` to find work and `hive task claim` to lease it.
5. Start work with `hive context startup` or a governed run via `hive run start`.
6. Evaluate, accept, reject, or escalate with the `hive run` commands.

## What Ships In This Repo

### Core CLI

The CLI covers:

- workspace bootstrap and health checks
- project discovery and scaffolding
- task CRUD, claims, and ready ranking
- governed runs and evaluator execution
- project-local and optional global memory
- startup and handoff context assembly
- workspace search
- one-time import for older checklist-based repos

### Optional adapters

These are useful, but not required:

- Streamlit dashboard via `hive dashboard` when installed with `agent-hive[dashboard]`
- thin search/execute MCP adapter via `hive-mcp` when installed with `agent-hive[mcp]`
- optional GitHub issue dispatcher in `src/agent_dispatcher.py`
- optional Claude GitHub App integration in `docs/INSTALL_CLAUDE_APP.md`

The core CLI does not require an LLM API key.

## Maintainer Links

- [docs/MAINTAINING.md](docs/MAINTAINING.md) for local development and day-to-day repository work
- [docs/RELEASING.md](docs/RELEASING.md) for tagged releases, PyPI, and Homebrew
- [docs/INSTALL_CLAUDE_APP.md](docs/INSTALL_CLAUDE_APP.md) for the optional GitHub App path

## Optional Environment Variables

```bash
HIVE_BASE_PATH=/path/to/workspace
HIVE_GLOBAL_MEMORY_DIR=/custom/global-memory
COORDINATOR_URL=http://localhost:8080
WANDB_API_KEY=your-wandb-api-key
WEAVE_PROJECT=agent-hive
```

`COORDINATOR_URL` and Weave tracing are optional. The core CLI works fine without them.

## Migration

If you are bringing an older repo forward, import it once and then stay in the canonical task flow:

```bash
hive migrate v1-to-v2
```

To replace the old checklist section with a generated rollup:

```bash
hive migrate v1-to-v2 --rewrite
```

## Repository Layout

```text
.
├── .github/workflows/
├── .hive/
├── docs/
├── examples/
├── packaging/homebrew/
├── projects/
├── scripts/
├── src/
└── tests/
```

## Status

This repository runs on the same Hive 2.0 substrate it ships. Projection sync and ready-work snapshots run in GitHub Actions, and the repo carries live canonical task, run, memory, and projection state.

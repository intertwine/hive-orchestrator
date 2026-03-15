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

### Public release channels

Use whichever path fits your setup:

```bash
uv tool install agent-hive
hive --version
hive doctor --json
```

```bash
pipx install agent-hive
hive --version
hive doctor --json
```

If you already manage a virtualenv yourself, `python -m pip install agent-hive` works too. For a standalone CLI install, `uv tool` or `pipx` is the better default.

```bash
brew tap intertwine/tap
brew install intertwine/tap/agent-hive
hive --version
hive doctor --json
```

If you're reading this before the first tagged public release lands on PyPI and Homebrew, use the git-based install path instead:

```bash
uv tool install --from git+https://github.com/intertwine/hive-orchestrator.git agent-hive
hive --version
hive doctor --json
```

### From a local checkout

```bash
git clone https://github.com/intertwine/hive-orchestrator.git
cd hive-orchestrator
make install
make install-tool
hive --version
hive doctor --json
```

If you prefer pipx from a checkout, run `make install-pipx`.

## Fastest First Run

If you are starting from an empty directory, skip the manual bootstrap steps and use the one-command path:

```bash
mkdir my-hive
cd my-hive
hive quickstart demo --title "Demo project" --json
```

That leaves you with:

- a bootstrapped `.hive/` substrate
- a starter project
- a conservative `PROGRAM.md`
- a small task chain with one real ready task

For the full everyday-user path, see [docs/QUICKSTART.md](docs/QUICKSTART.md).

## Five-Minute Tour

Bootstrap a workspace:

```bash
hive init --json
hive doctor --json
```

Create a project and a first task:

```bash
hive project create demo --title "Demo project" --json
hive task create --project-id demo --title "Define the first slice" --json
```

Find ready work and build startup context:

```bash
hive task ready --json
hive context startup --project demo --json
```

Refresh human-facing projections after canonical state changes:

```bash
hive sync projections --json
```

Need a copy-paste startup bundle for an agent session:

```bash
make session PROJECT=demo
```

If you want a visual view, run:

```bash
make dashboard
```

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

- Streamlit dashboard in `src/dashboard.py`
- thin search/execute MCP adapter in `src/hive_mcp/server.py`
- optional GitHub issue dispatcher in `src/agent_dispatcher.py`
- optional Claude GitHub App integration in `docs/INSTALL_CLAUDE_APP.md`

The core CLI does not require an LLM API key.

## Development

Install dev dependencies and run the quality gates:

```bash
make install-dev
make check
```

Build release artifacts:

```bash
make build
```

Run the release smoke checks:

```bash
make release-check
```

## Release Automation

The repository now includes:

- `/.github/workflows/ci.yml` for lint and test gates on push and pull request
- `/.github/workflows/release.yml` for tagged releases, PyPI trusted publishing, and Homebrew tap updates
- `docs/RELEASING.md` for the maintainer release checklist
- `scripts/bump_version.py` for repeatable version bumps
- `scripts/smoke_release_install.sh` for built-artifact install smoke tests
- `scripts/generate_homebrew_formula.py` for Homebrew formula generation from published artifacts

Everyday users should stop at the install section above. Maintainers should use [docs/RELEASING.md](/docs/RELEASING.md) for PyPI, Homebrew, tagging, and verification details.

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
hive migrate v1-to-v2 --json
```

To replace the old checklist section with a generated rollup:

```bash
hive migrate v1-to-v2 --rewrite --json
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

# Agent Hive

Agent Hive is a CLI-first orchestration platform for autonomous agents. It keeps machine state under `.hive/`,
keeps project context in Markdown, and gives agents a stable command surface for task discovery, claiming,
context assembly, governed runs, and search.

## Install

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

If you want optional extras:

- Dashboard: `uv tool install --upgrade 'agent-hive[dashboard]'`
- MCP adapter: `uv tool install --upgrade 'agent-hive[mcp]'`
- Homebrew currently ships the base CLI only, so add extras through `uv tool`, `pipx`, or `pip`

If you are testing before the first tagged public release lands on PyPI and Homebrew, use the git install:

```bash
uv tool install --from git+https://github.com/intertwine/hive-orchestrator.git agent-hive
```

## First Run

Start in an empty directory:

```bash
mkdir my-hive
cd my-hive
git init
hive quickstart demo --title "Demo project"
hive workspace checkpoint --message "Bootstrap Hive workspace"
hive next --project-id demo
hive work --project-id demo --owner <your-name> --output SESSION_CONTEXT.md
```

That gives you a real workspace, a starter project, a conservative `PROGRAM.md`, and a first task chain with one
ready task.

If you want the governed run loop right away, edit `projects/demo/PROGRAM.md` first so it has at least one required
evaluator and lists that evaluator under `promotion.requires_all`. Then continue with:

```bash
hive work --project-id demo --owner <your-name>
hive finish <run-id>
```

Optional extras stay intentionally small:

- `agent-hive[dashboard]` adds the observe-and-steer dashboard
- `agent-hive[mcp]` adds the thin `search` + bounded local `execute` adapter

## Choose The Right Guide

- Start here: [docs/START_HERE.md](https://github.com/intertwine/hive-orchestrator/blob/main/docs/START_HERE.md)
- Fresh workspace walkthrough: [docs/QUICKSTART.md](https://github.com/intertwine/hive-orchestrator/blob/main/docs/QUICKSTART.md)
- Existing repository adoption: [docs/ADOPT_EXISTING_REPO.md](https://github.com/intertwine/hive-orchestrator/blob/main/docs/ADOPT_EXISTING_REPO.md)
- Maintainer and release docs: [docs/MAINTAINING.md](https://github.com/intertwine/hive-orchestrator/blob/main/docs/MAINTAINING.md) and [docs/RELEASING.md](https://github.com/intertwine/hive-orchestrator/blob/main/docs/RELEASING.md)

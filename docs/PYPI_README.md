# Agent Hive

Agent Hive is a repo-native control plane for autonomous work. Use Codex, Claude Code, or local/manual execution to
do the work. Use Hive to supervise tasks, runs, memory, policy, and approvals from one place.

**Keep your agent. Add a control plane.**

`mellona-hive` is the distribution you install from PyPI or Homebrew. Mellona is the package family. Agent Hive is
the current product. The base install gives you the `hive` command. Add `mellona-hive[mcp]` when you want the thin
`hive-mcp` adapter.

## Install

Pick the installer you already trust:

```bash
uv tool install mellona-hive
```

```bash
pipx install mellona-hive
```

```bash
python -m pip install mellona-hive
```

```bash
brew tap intertwine/tap
brew install intertwine/tap/mellona-hive
```

Then verify:

```bash
hive --version
hive doctor
```

The full install matrix, lane chooser, and maintainer split live in
[docs/START_HERE.md](https://github.com/intertwine/hive-orchestrator/blob/main/docs/START_HERE.md).

If you want optional extras:

- Observe console: `uv tool install --upgrade 'mellona-hive[console]'`
- MCP adapter: `uv tool install --upgrade 'mellona-hive[mcp]'`
- Hosted E2B sandbox: `uv tool install --upgrade 'mellona-hive[sandbox-e2b]'`
- Self-hosted Daytona sandbox: `uv tool install --upgrade 'mellona-hive[sandbox-daytona]'`
- Homebrew currently ships the base CLI only, so add extras through `uv tool`, `pipx`, or `pip`

If you install sandbox extras, verify the current machine with:

```bash
hive sandbox doctor --json
```

If you are testing before the first tagged public release lands on PyPI and Homebrew, use the git install:

```bash
uv tool install --from git+https://github.com/intertwine/hive-orchestrator.git mellona-hive
```

## First Run

Start in an empty directory:

```bash
mkdir my-hive
cd my-hive
git init
hive onboard demo --prompt "Create a small React website about bees."
```

That gives you a real workspace, a starter project, a conservative `PROGRAM.md`, and a first task chain with one
ready task. If you want the observe-and-steer console, install `mellona-hive[console]` first, then run
`hive console serve`.

Fresh onboarded projects may start with the placeholder `local-smoke` evaluator so the loop works immediately. Replace
it with a real repo-specific evaluator before you trust autonomous promotion.

If the first `hive finish` later says there was nothing to promote, that is usually a healthy noop rather than a
broken setup. To intentionally see a successful first promotion, make one tiny docs-only change while working the
demo task, then finish the run.
Make that change inside the run worktree that `hive work` printed for you, usually `.hive/worktrees/run_<id>/`.

If the promoted task lands in `review`, close it explicitly to unblock the next task in the starter chain:

```bash
hive task update <task-id> --status done
```

Then use the normal loop:

```bash
hive next --project-id demo
hive work <task-id> --owner <your-name>
hive finish <run-id>
```

Optional extras stay intentionally small:

- `mellona-hive[console]` adds the observe-and-steer console
- `mellona-hive[mcp]` adds the thin `search` + bounded local `execute` adapter

## Choose The Right Guide

- Start here: [docs/START_HERE.md](https://github.com/intertwine/hive-orchestrator/blob/main/docs/START_HERE.md)
- Fresh workspace walkthrough: [docs/QUICKSTART.md](https://github.com/intertwine/hive-orchestrator/blob/main/docs/QUICKSTART.md)
- Existing repository adoption: [docs/ADOPT_EXISTING_REPO.md](https://github.com/intertwine/hive-orchestrator/blob/main/docs/ADOPT_EXISTING_REPO.md)
- Maintainer and release docs: [docs/MAINTAINING.md](https://github.com/intertwine/hive-orchestrator/blob/main/docs/MAINTAINING.md) and [docs/RELEASING.md](https://github.com/intertwine/hive-orchestrator/blob/main/docs/RELEASING.md)

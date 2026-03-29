# Agent Hive

Agent Hive is a repo-native control plane for autonomous work. In v2.4, that means you can still supervise Codex, Claude Code, and local/manual work from one place, while also adding native companion paths for Pi, OpenClaw, and Hermes.

**Keep your agent. Add a control plane.**

`mellona-hive` is the distribution you install from PyPI or Homebrew. Mellona is the package family. Agent Hive is
the current product. Install with the `[console]` extra to get the live operator UI alongside the `hive` CLI.

## Native Harness Paths

If you already work inside Pi, OpenClaw, or Hermes, start there instead of beginning with a generic `hive work` loop:

- Pi: `@mellona/pi-hive` gives you `next/search/open/attach/finish/note/status`
- OpenClaw: the `agent-hive` skill plus `openclaw-hive-bridge` lets you attach a live `sessionKey`
- Hermes: the Agent Hive skill/toolset supports advisory attach and trajectory import fallback

Each path starts with `hive integrate doctor <harness> --json` so setup failures are diagnosable.

## Install

Pick the installer you already trust:

```bash
uv tool install 'mellona-hive[console]'
```

```bash
pipx install 'mellona-hive[console]'
```

```bash
python -m pip install 'mellona-hive[console]'
```

Then verify:

```bash
hive --version
hive doctor
```

> **CLI-only install:** For headless servers or CI, `uv tool install mellona-hive` gives you the base
> CLI without console dependencies.

The full install matrix, lane chooser, and maintainer split live in
[docs/START_HERE.md](https://github.com/intertwine/hive-orchestrator/blob/main/docs/START_HERE.md).

Additional extras (`mellona-hive[mcp]`, `mellona-hive[sandbox-e2b]`, `mellona-hive[sandbox-daytona]`):

- MCP adapter: `uv tool install --upgrade 'mellona-hive[console,mcp]'`
- Hosted E2B sandbox: `uv tool install --upgrade 'mellona-hive[console,sandbox-e2b]'`
- Self-hosted Daytona sandbox: `uv tool install --upgrade 'mellona-hive[console,sandbox-daytona]'`
- Homebrew: `brew install intertwine/tap/mellona-hive` (base CLI only, add extras through pip/uv/pipx)

If you install sandbox extras, verify the current machine with `hive sandbox doctor --json`.

## First Run

Start in an empty directory:

```bash
mkdir my-hive
cd my-hive
git init
hive onboard demo --prompt "Create a small React website about bees."
hive console serve
```

Open `http://127.0.0.1:8787/console/` to see your workspace in the operator console. Then use the
manager loop:

```bash
hive next --project-id demo
hive work --owner <your-name>
hive finish <run-id>
```

Governed edits happen inside the run worktree that `hive work` creates, not in the workspace root.

Fresh onboarded projects start with the placeholder `local-smoke` evaluator so the loop works immediately. Replace
it with a real repo-specific evaluator before you trust autonomous promotion.

If you want the harness-native path instead of the generic first run:

- Pi: [docs/recipes/pi-harness.md](https://github.com/intertwine/hive-orchestrator/blob/main/docs/recipes/pi-harness.md)
- OpenClaw: [docs/recipes/openclaw-harness.md](https://github.com/intertwine/hive-orchestrator/blob/main/docs/recipes/openclaw-harness.md)
- Hermes: [docs/recipes/hermes-harness.md](https://github.com/intertwine/hive-orchestrator/blob/main/docs/recipes/hermes-harness.md)

## Choose The Right Guide

- Start here: [docs/START_HERE.md](https://github.com/intertwine/hive-orchestrator/blob/main/docs/START_HERE.md)
- Fresh workspace walkthrough: [docs/QUICKSTART.md](https://github.com/intertwine/hive-orchestrator/blob/main/docs/QUICKSTART.md)
- Existing repository adoption: [docs/ADOPT_EXISTING_REPO.md](https://github.com/intertwine/hive-orchestrator/blob/main/docs/ADOPT_EXISTING_REPO.md)
- Pi harness guide: [docs/recipes/pi-harness.md](https://github.com/intertwine/hive-orchestrator/blob/main/docs/recipes/pi-harness.md)
- OpenClaw harness guide: [docs/recipes/openclaw-harness.md](https://github.com/intertwine/hive-orchestrator/blob/main/docs/recipes/openclaw-harness.md)
- Hermes harness guide: [docs/recipes/hermes-harness.md](https://github.com/intertwine/hive-orchestrator/blob/main/docs/recipes/hermes-harness.md)
- Maintainer and release docs: [docs/MAINTAINING.md](https://github.com/intertwine/hive-orchestrator/blob/main/docs/MAINTAINING.md) and [docs/RELEASING.md](https://github.com/intertwine/hive-orchestrator/blob/main/docs/RELEASING.md)

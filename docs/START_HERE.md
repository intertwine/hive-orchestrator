# Start Here

Hive is a control plane for multi-agent software work. Use this page to pick the path that matches where you already work.

Best first experience:
- if you already live in Pi, OpenClaw, or Hermes, start with the native harness path below
- if you want a fresh generic Hive workspace, install Hive and create one with `hive onboard demo`

## Choose Your Lane

| If you want to... | Start here |
|---|---|
| keep working inside Pi | [Pi harness guide](./recipes/pi-harness.md) |
| keep working inside OpenClaw | [OpenClaw harness guide](./recipes/openclaw-harness.md) |
| keep working inside Hermes | [Hermes harness guide](./recipes/hermes-harness.md) |
| install Hive and create a fresh workspace | [Quickstart](./QUICKSTART.md) |
| bring Hive into an existing repository | [Adopt Hive In An Existing Repo](./ADOPT_EXISTING_REPO.md) |
| work on Hive itself, ship releases, or update packaging | [Maintaining Hive](./MAINTAINING.md) and [Releasing Hive](./RELEASING.md) |

## Install Hive

Install `mellona-hive` with the console extra, then use the `hive` command. Mellona is the package family.
Agent Hive is the current product. The console gives you a live operator UI to observe and steer your agents.

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

> **CLI-only install:** For headless servers, CI, or minimal setups, `uv tool install mellona-hive`
> gives you the base CLI without the console web UI dependencies.

If you want the latest unreleased checkout before the next tagged release or before package
indexes catch up, use the git install instead:

```bash
uv tool install --from 'git+https://github.com/intertwine/hive-orchestrator.git' 'mellona-hive[console]'
```

## Native Harness Paths

These are the v2.4-native first-value paths. They all start with `hive integrate doctor` so setup failures are diagnosable before you edit any config by hand.

### Pi

Install Hive and the Pi companion:

```bash
uv tool install 'mellona-hive[console]'
npm install -g @mellona/pi-hive
```

Verify readiness:

```bash
hive integrate doctor pi --json
hive integrate pi
```

Then stay inside Pi:

```bash
pi-hive connect
pi-hive next --project-id <project-id>
pi-hive open <task-id> --json
```

Or attach a live session:

```bash
pi-hive attach <native-session-ref> --task-id <task-id> --json
```

Use the full guide in [recipes/pi-harness.md](./recipes/pi-harness.md).

### OpenClaw

Install Hive plus the bridge, then add the `agent-hive` skill from ClawHub:

```bash
uv tool install 'mellona-hive[console]'
npm install -g openclaw-hive-bridge
```

Verify the bridge and gateway path:

```bash
hive integrate doctor openclaw --json
hive integrate openclaw
```

Then attach the live session:

```bash
hive integrate attach openclaw <session-key>
```

OpenClaw is attach-only in v2.4 and always advisory. Use the full guide in [recipes/openclaw-harness.md](./recipes/openclaw-harness.md).

### Hermes

Install or update Hive:

```bash
uv tool install 'mellona-hive[console]'
```

Verify the Hermes path and load the Agent Hive skill/toolset:

```bash
hive integrate doctor hermes --json
hive integrate hermes
```

Then attach the current session:

```bash
hive integrate attach hermes <session-id>
```

If live attach is unavailable, import a trajectory later:

```bash
hive integrate import-trajectory hermes /path/to/hermes-export.jsonl --project-id <project-id>
```

Hermes private memory is never bulk-imported automatically. Use the full guide in [recipes/hermes-harness.md](./recipes/hermes-harness.md).

## Additional Extras

| Extra | Install | Purpose |
|---|---|---|
| MCP adapter | `uv tool install --upgrade 'mellona-hive[console,mcp]'` | Thin `hive-mcp` search + execute surface |
| E2B sandbox | `uv tool install --upgrade 'mellona-hive[console,sandbox-e2b]'` | Hosted sandbox execution |
| Daytona sandbox | `uv tool install --upgrade 'mellona-hive[console,sandbox-daytona]'` | Self-hosted sandbox execution |
| Homebrew | `brew install intertwine/tap/mellona-hive` | Base CLI only (no extras) |

`mellona-hive[mcp]` keeps the adapter deliberately small: `search` and `execute` only. `execute` is a bounded local
Python helper, not a full sandbox.

If you plan to use hosted or self-hosted sandbox execution, install the backend extras as needed:

- `uv tool install --upgrade 'mellona-hive[sandbox-e2b]'`
- `uv tool install --upgrade 'mellona-hive[sandbox-daytona]'`

After installing those extras, verify the current machine truthfully with:

```bash
hive sandbox doctor --json
```

## Fresh Workspace

If you want the shortest path to a real Hive workspace:

```bash
mkdir my-hive
cd my-hive
git init
hive onboard demo --prompt "Create a small React website about bees."
hive console serve
```

Open `http://127.0.0.1:8787/console/` to see your workspace in the operator console.

That path is covered in the full [Quickstart](./QUICKSTART.md). `hive onboard` is the recommended fresh-workspace
bootstrap. `hive init` only creates the substrate layout. `hive onboard` bootstraps the workspace, detects the local
driver situation, creates a starter project, runs Program Doctor, and leaves you with a safe first task chain.

The manager loop from the CLI:

```bash
hive next
hive work --owner <your-name>
hive finish <run-id>
```

Governed edits happen inside the run worktree that `hive work` creates, not in the workspace root.
The console shows the same information in a live dashboard — use whichever interface fits your workflow.

## Existing Repo

If you already have a repository and want Hive inside it:

```bash
cd your-repo
hive adopt app --title "App"
hive console serve
```

The console shows your project, tasks, and governance policy. From the CLI:

```bash
hive next
hive work --owner <your-name>
hive finish <run-id>
```

The full guide lives in [Adopt Hive In An Existing Repo](./ADOPT_EXISTING_REPO.md).

## Maintainers

If you are here to work on Hive itself, use a source checkout:

```bash
git clone https://github.com/intertwine/hive-orchestrator.git
cd hive-orchestrator
make install-dev
make install-tool
hive --version
python -m hive --version
```

From that point on, stay in the maintainer docs:

- [Maintaining Hive](./MAINTAINING.md)
- [Releasing Hive](./RELEASING.md)
- [Installing the Claude Code GitHub App](./INSTALL_CLAUDE_APP.md)
- [Sandbox Doctor](./recipes/sandbox-doctor.md)

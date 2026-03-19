# Start Here

Hive is a control plane for multi-agent software work. Use this page to pick the right path into it.

## Choose Your Lane

| If you want to... | Start here |
|---|---|
| install Hive and create a fresh workspace | [Quickstart](./QUICKSTART.md) |
| bring Hive into an existing repository | [Adopt Hive In An Existing Repo](./ADOPT_EXISTING_REPO.md) |
| work on Hive itself, ship releases, or update packaging | [Maintaining Hive](./MAINTAINING.md) and [Releasing Hive](./RELEASING.md) |

## Install Hive

Install `mellona-hive`, then use the `hive` command. Mellona is the package family. Agent Hive is the current
product.

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

If you are testing before the first tagged public release lands, use the git install instead:

```bash
uv tool install --from git+https://github.com/intertwine/hive-orchestrator.git mellona-hive
```

## Optional Extras

| Installer | Base CLI | Observe console | MCP adapter | Notes |
|---|---|---|---|---|
| `uv tool` | `uv tool install mellona-hive` | `uv tool install --upgrade 'mellona-hive[console]'` | `uv tool install --upgrade 'mellona-hive[mcp]'` | Cleanest path for most users |
| `pipx` | `pipx install mellona-hive` | `pipx install 'mellona-hive[console]'` | `pipx install 'mellona-hive[mcp]'` | Good if you already live in `pipx` |
| `pip` | `python -m pip install mellona-hive` | `python -m pip install 'mellona-hive[console]'` | `python -m pip install 'mellona-hive[mcp]'` | Best when you manage your own virtualenv |
| Homebrew | `brew install intertwine/tap/mellona-hive` | use one of the Python package installs above | use one of the Python package installs above | Homebrew currently ships the base CLI |

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
hive onboard demo --title "Demo project" --objective "Ship one governed slice."
```

That path is covered in the full [Quickstart](./QUICKSTART.md). `hive onboard` is the recommended fresh-workspace
bootstrap. `hive init` only creates the substrate layout. `hive onboard` bootstraps the workspace, detects the local
driver situation, creates a starter project, runs Program Doctor, and leaves you with a safe first task chain.

Once the workspace exists, the shortest manager-style loop is:

```bash
hive next
hive work --owner <your-name>
hive finish <run-id>
```

Install `mellona-hive[console]` first when you want the observe-and-steer console on top of that loop:

```bash
hive console serve
```

## Existing Repo

If you already have a repository and want Hive inside it:

```bash
cd your-repo
hive adopt app --title "App"
```

After that, run the manager loop:

```bash
hive next
hive work --owner <your-name>
```

Install `mellona-hive[console]` first if you want `hive console serve`.

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

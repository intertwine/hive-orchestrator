# Start Here

Use this page to pick the right path into Hive.

## Choose Your Lane

| If you want to... | Start here |
|---|---|
| install Hive and create a fresh workspace | [Quickstart](./QUICKSTART.md) |
| bring Hive into an existing repository | [Adopt Hive In An Existing Repo](./ADOPT_EXISTING_REPO.md) |
| work on Hive itself, ship releases, or update packaging | [Maintaining Hive](./MAINTAINING.md) and [Releasing Hive](./RELEASING.md) |

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

If you are testing before the first tagged public release lands, use the git install instead:

```bash
uv tool install --from git+https://github.com/intertwine/hive-orchestrator.git agent-hive
```

## Optional Extras

| Installer | Base CLI | Dashboard | MCP adapter | Notes |
|---|---|---|---|---|
| `uv tool` | `uv tool install agent-hive` | `uv tool install --upgrade 'agent-hive[dashboard]'` | `uv tool install --upgrade 'agent-hive[mcp]'` | Cleanest path for most users |
| `pipx` | `pipx install agent-hive` | `pipx install 'agent-hive[dashboard]'` | `pipx install 'agent-hive[mcp]'` | Good if you already live in `pipx` |
| `pip` | `python -m pip install agent-hive` | `python -m pip install 'agent-hive[dashboard]'` | `python -m pip install 'agent-hive[mcp]'` | Best when you manage your own virtualenv |
| Homebrew | `brew install intertwine/tap/agent-hive` | use one of the Python package installs above | use one of the Python package installs above | Homebrew currently ships the base CLI |

## Fresh Workspace

If you want the shortest path to a real Hive workspace:

```bash
mkdir my-hive
cd my-hive
hive quickstart demo --title "Demo project"
hive task ready --project-id demo
```

That path is covered in the full [Quickstart](./QUICKSTART.md).

## Existing Repo

If you already have a repository and want Hive inside it:

```bash
cd your-repo
hive init
```

After that, either create a first project with `hive project create` or import an older checklist-based Hive setup
with `hive migrate v1-to-v2`. The full guide lives in [Adopt Hive In An Existing Repo](./ADOPT_EXISTING_REPO.md).

## Maintainers

If you are here to work on Hive itself, use a source checkout:

```bash
git clone https://github.com/intertwine/hive-orchestrator.git
cd hive-orchestrator
make install-dev
make install-tool
```

From that point on, stay in the maintainer docs:

- [Maintaining Hive](./MAINTAINING.md)
- [Releasing Hive](./RELEASING.md)
- [Installing the Claude Code GitHub App](./INSTALL_CLAUDE_APP.md)

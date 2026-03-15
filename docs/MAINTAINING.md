# Maintaining Hive

This guide is for people working on Hive itself.

If you just want to use Hive in your own workspace, stop here and use the install and quickstart path in [README.md](../README.md) instead.

## Local Setup

```bash
git clone https://github.com/intertwine/hive-orchestrator.git
cd hive-orchestrator
make install-dev
make install-tool
```

That gives you:

- the editable development environment
- the `hive` CLI installed from this checkout
- the optional dashboard, MCP, coordinator, and tracing dependencies used by the test suite

## Daily Commands

```bash
make check
make test
make lint
make build
make release-check
```

Useful local commands:

- `make dashboard` opens the dashboard from this checkout
- `make session PROJECT=demo` writes a startup bundle into the project directory
- `make verify-claude` checks the optional GitHub App setup against the current workspace
- `make brew-formula` regenerates the Homebrew formula from the current package metadata

## Install Paths While Developing

Use the public install paths when you want to test what end users will see:

```bash
uv tool install --force --from . agent-hive
pipx install --force .
```

If you need optional extras while testing:

```bash
uv tool install --force --from . 'agent-hive[dashboard]'
uv tool install --force --from . 'agent-hive[mcp]'
```

For local checkout smoke tests, prefer `uv tool install --force --from . ...` or a throwaway
virtualenv install over `uv tool run --from . ...`. The install path reliably rebuilds the local
checkout, while `uv tool run --from .` can reuse a stale cached build when the package version has
not changed yet.

## CI And Release Surfaces

This repository ships:

- `/.github/workflows/ci.yml` for lint and test gates
- `/.github/workflows/release.yml` for tagged releases and Homebrew updates
- `scripts/smoke_release_install.sh` for built-artifact install smoke tests
- `scripts/generate_homebrew_formula.py` for formula generation

Use [docs/RELEASING.md](./RELEASING.md) for the release checklist and publishing flow.

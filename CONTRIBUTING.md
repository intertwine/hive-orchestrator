# Contributing to Agent Hive

Thanks for contributing. Hive is now a v2-first codebase, so the safest way to work here is to stay close to the CLI, the `.hive/` substrate, and the generated projection model.

## Ground Rules

- Treat `.hive/tasks/*.md` as canonical task state.
- Treat `projects/*/AGENCY.md` as human-facing context, not the machine database.
- Read `projects/*/PROGRAM.md` before changing evaluator or execution behavior.
- Keep human-facing docs concrete, specific, and easy to read aloud.
- Run `make check` before you open or update a PR.

## Local Setup

Prerequisites:

- Python 3.11+
- [`uv`](https://github.com/astral-sh/uv)

Setup:

```bash
git clone https://github.com/intertwine/hive-orchestrator.git
cd hive-orchestrator
make install-dev
make install-tool
hive doctor --json
```

If you want a fresh local workspace state:

```bash
hive init --json
```

## Daily Development Loop

```bash
make format
make check
```

What those gates cover:

- `make format`: `black`
- `make lint`: `pylint` with a repo fail-under of `9.0`
- `make test`: `pytest`

## What To Build On

Prefer these surfaces:

- `src/hive/` for CLI, substrate, runs, memory, projections, and search
- `src/hive_mcp/server.py` for the thin MCP adapter
- `src/dashboard.py` for the optional dashboard

Treat these as compatibility surfaces unless you are explicitly fixing them:

- `src/cortex.py`
- legacy checklist parsing helpers
- any docs that describe direct `AGENCY.md` mutation as the primary workflow

## Writing and Docs

- Update [README.md](README.md) for user-facing workflow changes.
- Update [AGENTS.md](AGENTS.md) and [CLAUDE.md](CLAUDE.md) when agent-facing guidance changes.
- Keep examples aligned with the current CLI-first model.
- When rewriting docs, prefer plain language over generic product copy.

## Tests

Add or update tests whenever behavior changes.

Good places to extend coverage:

- `tests/test_hive_v2.py` for CLI and substrate behavior
- `tests/test_hive_run_worktree.py` for run lifecycle behavior
- `tests/test_security.py` for sanitization and hardening
- `tests/test_start_session.py` for session bootstrap UX

## Pull Requests

1. Branch from `main`.
2. Keep the PR scoped to one coherent change.
3. Include tests for behavior changes.
4. Update docs when the user-facing story changes.
5. Make sure `make check` passes before requesting review.

## Questions

- Open a [Discussion](https://github.com/intertwine/hive-orchestrator/discussions)
- Check [README.md](README.md), [AGENTS.md](AGENTS.md), and [CLAUDE.md](CLAUDE.md)

Thanks for helping make Hive easier to use, easier to trust, and easier to extend.

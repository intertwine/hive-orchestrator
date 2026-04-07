# Maintaining Hive

This guide is for people working on Hive itself.

If you just want to use Hive in your own workspace, stop here and use [START_HERE.md](./START_HERE.md) and
[QUICKSTART.md](./QUICKSTART.md) instead.

## Local Setup

```bash
git clone https://github.com/intertwine/hive-orchestrator.git
cd hive-orchestrator
make install-dev
make install-tool
hive --version
python -m hive --version
```

That gives you:

- the editable development environment
- the `hive` CLI installed from this checkout
- the optional observe console, MCP, and tracing dependencies used by the test suite

## Daily Commands

```bash
make console-check
make check
make test
make lint
make build
make release-check
```

Useful local commands:

- `make console` opens the packaged observe-and-steer console from this checkout
- `make console-check` runs the console unit, accessibility, and real-browser validation path used by v2.5 console work
- `make workspace-status` shows branch, worktrees, PR state, Hive doctor output, worker processes, and untracked `.hive/events`
- `make session PROJECT=demo` writes a startup bundle into the project directory
- `make verify-claude` checks the optional GitHub App setup against the current workspace
- `make brew-formula` regenerates the Homebrew formula from the current package metadata
- `hive workspace checkpoint --message "Checkpoint workspace"` creates a clean Git checkpoint before a run
- `hive run cleanup --terminal` prunes linked worktrees left behind by terminal runs
- `uv run hive sandbox doctor --json` reports truthful backend availability and configuration for `local-safe`, `local-fast`, E2B, and Daytona

Keep [docs/V2_3_STATUS.md](./V2_3_STATUS.md) as the compact ledger for the shipped v2.3 line and its scope-lock notes.
Keep [docs/V2_4_STATUS.md](./V2_4_STATUS.md) as the compact shipped ledger for the v2.4 release line.
For the active v2.5 draft release line, use [docs/V2_5_STATUS.md](./V2_5_STATUS.md) as the compact execution ledger,
[docs/V2_5_RELEASE_WALKTHROUGH.md](./V2_5_RELEASE_WALKTHROUGH.md) as the maintainer walkthrough and release-cut plan, and
[docs/hive-post-v2.4-rfcs/docs/HANDOFF_TO_CODEX.md](./hive-post-v2.4-rfcs/docs/HANDOFF_TO_CODEX.md) plus
[docs/hive-post-v2.4-rfcs/docs/hive-v2.5-rfc/HIVE_V2_5_COMMAND_CENTER_RFC.md](./hive-post-v2.4-rfcs/docs/hive-v2.5-rfc/HIVE_V2_5_COMMAND_CENTER_RFC.md)
as the planning reference bundle.

## Install Paths While Developing

Use the public install paths when you want to test what end users will see:

```bash
uv tool install --force --from . mellona-hive
pipx install --force .
```

If you need optional extras while testing:

```bash
uv tool install --force --from . 'mellona-hive[console]'
uv tool install --force --from . 'mellona-hive[mcp]'
uv tool install --force --from . 'mellona-hive[sandbox-e2b]'
uv tool install --force --from . 'mellona-hive[sandbox-daytona]'
```

If you are iterating on the React console itself:

```bash
cd frontend/console
pnpm install
pnpm exec playwright install chromium
pnpm dev
```

The backend for that frontend lives behind `hive console serve`.

The MCP extra intentionally stays thin. It exposes `search` plus bounded local `execute`, not a large tool catalog
or a full sandbox.

For local checkout smoke tests, prefer `uv tool install --force --from . ...` or a throwaway
virtualenv install over `uv tool run --from . ...`. The install path reliably rebuilds the local
checkout, while `uv tool run --from .` can reuse a stale cached build when the package version has
not changed yet.

When you invoke the CLI from a source checkout, prefer the public surfaces:

```bash
hive doctor --json
python -m hive doctor --json
```

Do not use `python -m src.hive.cli.main`. That path is an internal module layout detail, not part of the
supported maintainer or user experience.

## CI And Release Surfaces

This repository ships:

- `/.github/workflows/ci.yml` for lint and test gates
- `/.github/workflows/release.yml` for tagged releases and Homebrew updates
- `scripts/smoke_release_install.sh` for built-artifact install smoke tests
- `scripts/generate_homebrew_formula.py` for formula generation

Use [docs/RELEASING.md](./RELEASING.md) for the release checklist and publishing flow.

GitHub is also configured to auto-delete merged branches. That keeps normal feature and PR branches from piling up after merges.

This repo does not ship a custom Claude GitHub Actions review workflow anymore. For PR review, prefer Anthropic's
managed Code Review GitHub App flow. Use manual `@claude review` requests or the repository's configured review
behavior in Anthropic admin settings. Keep GitHub Actions for repository-owned CI and scheduled maintenance only.

For maintainer-critical PRs, local Claude review is an acceptable primary or fallback path when GitHub-managed review
is delayed or ambiguous. The built-in `claude -p "/review <pr-number>"` path works well for this. If you use local
review, summarize the findings and resolutions in the PR thread so the review state stays visible.

When you do request `@claude review`, treat the review as pending until GitHub shows a new Claude comment or review
artifact on the latest PR head. An `eyes` reaction or acknowledgement on the request comment is not completion.

After merging, watch the `push` CI run on `main`. If the merge commit goes red, treat that as immediate new blocking
work rather than assuming the green PR checks were sufficient.

For bot-generated review branches, this repo also ships [`.github/workflows/branch-hygiene.yml`](../.github/workflows/branch-hygiene.yml). It runs weekly and can be triggered manually in dry-run mode when you want to preview what it would prune. The cleanup is intentionally conservative:

- merged `codex/*`, `claude/*`, and `copilot/*` branches are safe to delete
- stale `claude/*` and `copilot/*` branches with no open PR are deleted after 7 days
- unmerged `codex/*` branches are left alone unless they have already landed in `main`

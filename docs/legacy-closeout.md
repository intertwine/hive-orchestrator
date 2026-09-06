# Legacy closeout

September 6, 2026. Agent Hive (`hive-orchestrator`, PyPI package `mellona-hive`) is
**unmaintained legacy software**. The final release is **2.4.1**. No feature updates,
compatibility updates, or security fixes are promised. Existing source, package
names, releases, and the MIT license remain available. The repository is retained
on GitHub, archived, for reference and forks, not ongoing support.

## What to use instead

Nothing from Intertwine supersedes Agent Hive. Keep required project rules in
reviewed repository documentation or your agent's own instruction files
(`AGENTS.md`, `CLAUDE.md`), and use the native task, run, and memory features of
the agent you already work in (Codex, Claude Code, Pi, OpenClaw, Hermes).

## How existing users should proceed

- `.hive/tasks/*.md`, `.hive/runs/*`, and `projects/*/AGENCY.md` are plain Markdown,
  JSON, and Git history. They stay readable without an installed `hive` runtime.
  Keep them in your repository or export them; nothing needs to be migrated
  through Hive itself.
- If you keep running the CLI, pin the final version: `mellona-hive==2.4.1`
  (`uv tool install "mellona-hive==2.4.1"` or `pip install "mellona-hive==2.4.1"`).
  Homebrew users can keep the tap formula they already have installed; the tap is
  not updated after the closeout unless the final release workflow ran.
- Do not expect this package to track future releases of the agents it drives
  (Codex app-server protocol, Claude Code SDK, MCP). Driver breakage after the
  closeout is expected, not a bug to report here.
- To remove Hive from a repository, delete `.hive/` (after committing or exporting
  anything you want to keep) and the `<!-- hive:begin compatibility -->` block that
  `hive` projected into `AGENTS.md`. Nothing else is installed into a project.

## Final state

- Final commit line: `main` on GitHub, tagged `v2.4.1` once the owner publishes.
- `pyproject.toml` reads `2.4.1`, description marked legacy, classifier
  `Development Status :: 7 - Inactive`. `src/hive/common.py` `HIVE_VERSION` matches.
- Version 2.4.1 contains no functional change over 2.4.0. It exists so that the
  package index and the installed CLI both carry the unmaintained status, and so
  that the packaging fix below is what the final artifacts were built with.
- GitHub Actions on the repository were disabled on 2026-09-06 and the repository
  archived, so the scheduled `projection-sync`, `branch-hygiene`,
  `agent-assignment`, and ready-work workflows no longer run. Actions may be
  re-enabled briefly only to run the tagged release workflow.
- Repository Actions secrets (`ANTHROPIC_API_KEY`, `HOMEBREW_TAP_GITHUB_TOKEN`,
  `OPENAI_API_KEY`, `OPENROUTER_API_KEY`) and the PyPI trusted-publisher binding
  for environment `pypi` were left in place at closeout; the owner may remove them.

## Known issues at closeout

### Packaging CI (`packaging-smoke`) and the release build

The `packaging-smoke` CI job and `make release-check` failed on the 2.4.0 line with
`twine check: InvalidDistribution: '2.5' is not a valid metadata version`.

Root cause: `[build-system]` required an unpinned `hatchling`, so every build
resolved the newest backend. hatchling 1.32.0 (2026-08-11) began writing
`Metadata-Version: 2.5`; the dev extras lock `twine` 6.2.0 with `packaging` 25.0,
which only understands metadata up to 2.4. The pinned
`pypa/gh-action-pypi-publish` commit used by `release.yml` bundles twine 6.1.0 and
packaging 25.0 as well, so an upload of a 2.5 artifact would have failed at the
publish step even if `twine check` were skipped.

Fix in 2.4.1: `requires = ["hatchling>=1.27,<1.32"]`, which produces
`Metadata-Version: 2.4` artifacts that both the locked twine and the pinned publish
action accept. Nothing else in the packaging path changed. A future fork that lifts
the cap should upgrade `twine` to 7.x (packaging 26.1+) and move the publish action
to a release that ships twine 7 at the same time.

### Unmerged sibling branches

Two branches were left unmerged and are not part of 2.4.1:

- `codex/github-actions-hardening` (last commit `a4ec580`): CI/workflow hardening.
- `codex/v25-inbox-notifications` (last commit `4f297f4`, plus a `wip:` commit
  preserving uncommitted console-preferences and inbox-state work): part of the
  v2.5 draft line described in `docs/V2_5_STATUS.md`, which was never released.

The v2.5 draft release line (`docs/V2_5_STATUS.md`,
`docs/V2_5_RELEASE_WALKTHROUGH.md`, `docs/hive-post-v2.4-rfcs/`) is historical
planning material, not a commitment.

### Run artifacts under `.hive/worktrees`

`.hive/worktrees/*` in the original checkout are historical Hive run worktrees
(`codex/v25-acceptance-ledger`, `codex/v25-launch-collateral`,
`codex/v25-release-walkthrough`) left by the dogfooding runs recorded in
`.hive/runs`. They are artifacts of past runs, not pending work. They are not
tracked in Git and do not exist in a fresh clone.

## Verification scope

The closeout was validated locally on macOS with Python 3.11 from the repository's
own `uv.lock`: `uv build` produced Metadata-Version 2.4 artifacts, the locked
`twine check` passed, and the focused release-tooling and maintainer-surface tests
passed. No live publish, Homebrew tap update, or driver run against a current
Codex or Claude Code release is implied by those results. See
`docs/RELEASE-2.4.1.md` for the release notes and the retirement receipt under
`docs/retirement/2026-09-06/` for the GitHub-side state captured at archive time.

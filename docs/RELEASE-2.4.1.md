# Agent Hive v2.4.1 (`mellona-hive` 2.4.1)

Final legacy closeout, September 6, 2026. **Unmaintained:** no future feature,
compatibility, or security updates are promised. See
[legacy closeout](legacy-closeout.md). Existing installations are not disabled by
this patch release.

## Changes

- Cap the build backend at `hatchling<1.32` so release artifacts carry
  `Metadata-Version: 2.4`. hatchling 1.32.0 writes 2.5, which the locked twine 6.2.0
  and the pinned PyPI publish action reject; this was the `packaging-smoke` CI
  failure on the 2.4.0 line.
- Mark the package, its PyPI description, `README.md`, `AGENTS.md`, and
  `CONTRIBUTING.md` as unmaintained legacy software; classifier moved to
  `Development Status :: 7 - Inactive`.
- No functional change to the `hive` CLI, `hive-mcp`, drivers, or console over 2.4.0.

## Verification scope

Local `uv build` plus locked `twine check` and the focused release-tooling tests on
Python 3.11. No live PyPI upload, Homebrew verification, or driver run against a
current agent release is implied. See the closeout receipt for the actual outputs.

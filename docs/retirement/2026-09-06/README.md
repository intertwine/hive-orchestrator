# Retirement receipt — hive-orchestrator

Captured 2026-09-06T12:18:34Z. Owner approved archiving this repository untouched, with a note, on 2026-09-06.

This directory holds configuration metadata only. Secret payloads, environment values, and data are not included. It is not a data backup.

What was done: an archive note was added to `README.md` and a one-line retired note above the compatibility block in `AGENTS.md` (which `CLAUDE.md` symlinks to); GitHub Actions were disabled; the repository was archived on GitHub. No code, packaging, or CI change was made; the failing `packaging-smoke` job (Twine rejects metadata version `2.5`) was left as-is. The PyPI package `mellona-hive` (2.4.0) was neither published nor yanked.

What remains for the owner: four repository Actions secrets (`ANTHROPIC_API_KEY`, `HOMEBREW_TAP_GITHUB_TOKEN`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`) were left in place, and the PyPI trusted-publisher binding for environment `pypi` still exists. The sibling worktrees and the local directory were left in place. See `retirement-receipt.json`.

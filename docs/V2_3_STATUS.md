# Hive v2.3 Status

Status: active
Last updated: 2026-03-19
Purpose: compact execution ledger for the current v2.3 release line

This file is the maintainer-facing status ledger for v2.3. Update it when a v2.3
merge changes release readiness or moves the next blocker.

## Scope Lock

The v2.3 release scope is now explicitly locked to the work that is already close
to release quality:

- Codex and Claude must ship as deep, truthful, live drivers.
- Local, hosted, and self-hosted sandbox paths must meet the release acceptance bar.
- Retrieval must be packaged, explainable, and traceable in installed environments.
- Campaigns, console surfaces, and docs/demo material must match the shipped product.

The following items are explicitly deferred from blocking the v2.3 release:

- Pi remains available as an honest staged driver, but full RPC depth moves to a later release.
- The full hybrid retrieval stack from the proposed RFC (for example LanceDB, FastEmbed,
  and Qdrant-backed retrieval) moves to a later release.

## Release Gate Ledger

| Gate | Status | Evidence | Remaining blocker |
|---|---|---|---|
| Runtime contract, truthful capabilities, and standardized run artifacts | Complete | `#118`, `#119`, `#122`, `#123`, `src/hive/runtime/*`, `src/hive/runs/paths.py` | Keep compatibility and docs aligned as the remaining gates land |
| Deep Codex live driver with approval bridging | Complete | `#116`, `#120`, `#123`, `tests/test_hive_drivers.py` | Final release/demo validation only |
| Deep Claude live driver with SDK adapter and approval bridging | Complete | `#122`, `#127`, `#130`, `#136`, `src/hive/drivers/claude_sdk.py` | Final release/demo validation only |
| One real local sandbox path | Complete | `#117`, `#128`, `src/hive/sandbox/runtime.py`, `src/hive/sandbox/registry.py`, `docs/recipes/sandbox-doctor.md`, `.github/workflows/ci.yml`, `tests/test_local_safe_acceptance.py` | Final release/demo validation only |
| One real hosted sandbox path | Complete | `#124`, `#132`, `src/hive/runs/executors.py`, `docs/recipes/sandbox-doctor.md`, `docs/hive-v2.3-rfc/HIVE_V2_3_ACCEPTANCE_TESTS.md`, `tests/test_remote_sandbox_acceptance.py` | Final release/demo validation only |
| One real self-hosted sandbox path | Complete | `#125`, `#127`, `#133`, `src/hive/runs/executors.py`, `docs/recipes/sandbox-doctor.md`, `tests/test_remote_sandbox_acceptance.py`, `2026-03-19 live Daytona proof (1 passed)` | Final release/demo validation only |
| Explainable retrieval, packaged corpus, and traces | Partial | `retrieval/trace.json`, `retrieval/hits.json`, `src/hive/runs/paths.py`, `src/hive/console/state.py`, `tests/test_install_story.py` | Final installed-package usefulness check and docs/demo alignment |
| Campaign candidate and decision artifacts | Complete | `candidate-set.json`, `decision.json`, `src/hive/control/campaigns.py`, `frontend/console/src/routes/CampaignDetailPage.tsx`, `frontend/console/src/test/observeConsole.smoke.test.tsx` | Final release/demo validation only |
| Observe-and-steer console at RFC depth | Complete | `frontend/console/src/routes/RunDetailPage.tsx`, `frontend/console/src/routes/InboxPage.tsx`, `frontend/console/src/routes/CampaignDetailPage.tsx`, `tests/test_console_frontend_story.py`, `frontend/console/src/test/observeConsole.smoke.test.tsx` | Final release/demo validation only |
| Pi driver at acceptance bar | Deferred | `src/hive/drivers/pi.py`, `docs/hive-v2.3-rfc/HIVE_V2_3_RUNTIME_AND_SANDBOX_SPEC.md` | Keep staged truthfulness intact and carry full RPC depth to the next release line |
| Release docs, demo, and acceptance alignment | Pending | `docs/`, `docs/hive-v2.3-rfc/`, `tests/test_v23_runtime_foundation.py` | Tighten scope and prove the final release story end-to-end |

## Current Read

What is real now:

- the v2.3 runtime substrate is real enough to build on
- Codex and Claude are both substantially real as live supervised drivers
- approval truthfulness and runtime event/artifact plumbing are no longer just scaffolding
- local, hosted, and self-hosted sandbox paths all exist in code and tests
- the shipped operator console now surfaces capability truth, sandbox policy, retrieval traces, approval actions, and campaign decision reasoning
- Pi no longer blocks the v2.3 release; the current staged driver remains available and honest
- the release retrieval bar is now explainability, provenance, packaged corpus coverage, and trace persistence rather than the full hybrid backend stack
- sandbox doctor and install docs now describe the real backend shapes and optional extras instead of leaving them buried in the RFC
- the local-safe sandbox path now has a real Podman-backed CI proof instead of only mocked contract coverage
- the Daytona self-hosted proof now passed in a credentialed environment using `DAYTONA_API_URL` + `DAYTONA_API_KEY`

What is still holding back a clean release call:

- installed-package retrieval usefulness and final operator-grade retrieval/docs validation
- docs, console, and demo alignment so the shipped story matches the implementation

## Next Blocker

Close the remaining acceptance-driven train against the scope-locked release:

1. align public docs and demo collateral with the real v2.3 operator story
2. finish the installed-package retrieval usefulness and release-demo validation pass
3. make the final release call against the now-closed runtime and sandbox gates

## Update Rule

When a v2.3 PR merges:

- update the affected gate row
- record the PR or commit evidence
- rewrite `Next Blocker` if the critical path changed

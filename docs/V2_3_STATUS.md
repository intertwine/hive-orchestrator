# Hive v2.3 Status

Status: v2.3.1 released
Last updated: 2026-03-21
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

- Pi driver removed; full RPC harness integration (Pi, Hermes, OpenClaw) deferred to a focused design sprint.
- Hybrid retrieval (LanceDB + FastEmbed) is now available as the optional `[retrieval]` extra. Qdrant remote backend deferred to a later release.

## Release Gate Ledger

| Gate | Status | Evidence | Remaining blocker |
|---|---|---|---|
| Runtime contract, truthful capabilities, and standardized run artifacts | Complete | `#118`, `#119`, `#122`, `#123`, `src/hive/runtime/*`, `src/hive/runs/paths.py` | Keep compatibility and docs aligned as the remaining gates land |
| Deep Codex live driver with approval bridging | Complete | `#116`, `#120`, `#123`, `tests/test_hive_drivers.py` | Final release/demo validation only |
| Deep Claude live driver with SDK adapter and approval bridging | Complete | `#122`, `#127`, `#130`, `#136`, `src/hive/drivers/claude_sdk.py` | Final release/demo validation only |
| One real local sandbox path | Complete | `#117`, `#128`, `src/hive/sandbox/runtime.py`, `src/hive/sandbox/registry.py`, `docs/recipes/sandbox-doctor.md`, `.github/workflows/ci.yml`, `tests/test_local_safe_acceptance.py` | Final release/demo validation only |
| One real hosted sandbox path | Complete | `#124`, `#132`, `src/hive/runs/executors.py`, `docs/recipes/sandbox-doctor.md`, `docs/hive-v2.3-rfc/HIVE_V2_3_ACCEPTANCE_TESTS.md`, `tests/test_remote_sandbox_acceptance.py` | Final release/demo validation only |
| One real self-hosted sandbox path | Complete | `#125`, `#127`, `#133`, `src/hive/runs/executors.py`, `docs/recipes/sandbox-doctor.md`, `tests/test_remote_sandbox_acceptance.py`, `2026-03-19 live Daytona proof (1 passed)` | Final release/demo validation only |
| Explainable retrieval, packaged corpus, and traces | Complete | `retrieval/trace.json`, `retrieval/hits.json`, `src/hive/runs/paths.py`, `src/hive/console/state.py`, `scripts/smoke_release_install.sh`, `tests/test_install_story.py`, `tests/test_release_tooling.py` | Final release/demo validation only |
| Hybrid dense retrieval (LanceDB + FastEmbed) | Complete | `src/hive/retrieval/dense.py`, `pyproject.toml[retrieval]`, `tests/test_hive_retrieval_dense.py` | Optional `[retrieval]` extra; Qdrant remote backend deferred |
| Campaign candidate and decision artifacts | Complete | `candidate-set.json`, `decision.json`, `src/hive/control/campaigns.py`, `frontend/console/src/routes/CampaignDetailPage.tsx`, `frontend/console/src/test/observeConsole.smoke.test.tsx` | Final release/demo validation only |
| Observe-and-steer console at RFC depth | Complete | `frontend/console/src/routes/RunDetailPage.tsx`, `frontend/console/src/routes/InboxPage.tsx`, `frontend/console/src/routes/CampaignDetailPage.tsx`, `tests/test_console_frontend_story.py`, `frontend/console/src/test/observeConsole.smoke.test.tsx` | Final release/demo validation only |
| Pi driver at acceptance bar | Removed | `src/hive/drivers/pi.py`, `docs/hive-v2.3-rfc/HIVE_V2_3_RUNTIME_AND_SANDBOX_SPEC.md` | Driver demoted; RPC harness integration deferred to focused design sprint for Pi/Hermes/OpenClaw |
| Release docs, demo, and acceptance alignment | Complete | `#148`, `README.md`, `docs/DEMO_WALKTHROUGH.md`, `docs/OPERATOR_FLOWS.md`, `docs/START_HERE.md`, `docs/RELEASING.md`, `docs/hive-v2.3-rfc/HIVE_V2_3_ACCEPTANCE_TESTS.md`, `tests/test_launch_collateral.py`, `tests/test_maintainer_surfaces.py`, `scripts/smoke_release_install.sh`, `tests/test_release_tooling.py` | Final release/demo validation only |

## Current Read

What is real now:

- the v2.3 runtime substrate is real enough to build on
- Codex and Claude are both substantially real as live supervised drivers
- approval truthfulness and runtime event/artifact plumbing are no longer just scaffolding
- local, hosted, and self-hosted sandbox paths all exist in code and tests
- the shipped operator console now surfaces capability truth, sandbox policy, retrieval traces, approval actions, and campaign decision reasoning
- Pi driver removed from registry; RPC harness integration (Pi, Hermes, OpenClaw) deferred to a focused design sprint
- hybrid dense retrieval (LanceDB + FastEmbed) is available as the optional `[retrieval]` extra, with graceful degradation to FTS5-only when not installed
- retrieval traces now report real dense candidate counts instead of hardcoded zeros
- sandbox doctor and install docs now describe the real backend shapes and optional extras instead of leaving them buried in the RFC
- the local-safe sandbox path now has a real Podman-backed CI proof instead of only mocked contract coverage
- the Daytona self-hosted proof now passed in a credentialed environment using `DAYTONA_API_URL` + `DAYTONA_API_KEY`
- the public README, demo walkthrough, operator flows, and acceptance/release docs now describe the scoped v2.3 operator story instead of the older v2.2 launch framing
- the built-artifact release smoke path now proves installed-package `hive search` returns packaged API/RFC and recipe hits with explanations

## Release History

| Version | Date | Notes |
|---|---|---|
| `v2.3.0` | 2026-03-20 | Foundation hardening: driver correctness, executor policy, workflow reliability |
| `v2.3.1` | 2026-03-21 | Console-first human onboarding UX redesign (`#158`): forgiving demo defaults, human mental model summary, getting-started empty state, console-first doc rewrite, better dead-end CLI guidance |
## Next Blocker

v2.3.2 release pending: truthfulness closure sprint (`#161`) and hybrid retrieval landed. Version bump and tag still needed.

## Update Rule

When a v2.3 PR merges:

- update the affected gate row
- record the PR or commit evidence
- rewrite `Next Blocker` if the critical path changed

# Hive v2.3 Status

Status: active
Last updated: 2026-03-19
Purpose: compact execution ledger for the current v2.3 release line

This file is the maintainer-facing status ledger for v2.3. Update it when a v2.3
merge changes release readiness or moves the next blocker.

## Release Gate Ledger

| Gate | Status | Evidence | Remaining blocker |
|---|---|---|---|
| Runtime contract, truthful capabilities, and standardized run artifacts | Complete | `#118`, `#119`, `#122`, `#123`, `src/hive/runtime/*`, `src/hive/runs/paths.py` | Keep compatibility and docs aligned as the remaining gates land |
| Deep Codex live driver with approval bridging | Complete | `#116`, `#120`, `#123`, `tests/test_hive_drivers.py` | Final release/demo validation only |
| Deep Claude live driver with SDK adapter and approval bridging | Complete | `#122`, `#127`, `#130`, `#136`, `src/hive/drivers/claude_sdk.py` | Final release/demo validation only |
| One real local sandbox path | Partial | `#117`, `#128`, `src/hive/sandbox/runtime.py`, `src/hive/sandbox/registry.py` | Final release-grade validation of `local-safe` versus `local-fast`, docs, and operator guidance |
| One real hosted sandbox path | Partial | `#124`, `#132`, `src/hive/runs/executors.py` | Final acceptance validation for E2B behavior and docs |
| One real self-hosted sandbox path | Partial | `#125`, `#127`, `#133`, `src/hive/runs/executors.py` | Final acceptance validation for Daytona behavior and docs |
| Retrieval traces and explainability | Partial | `retrieval/trace.json`, `retrieval/hits.json`, `src/hive/runs/paths.py`, `src/hive/console/state.py` | Full hybrid retrieval engine is still not landed |
| Campaign candidate and decision artifacts | Complete | `candidate-set.json`, `decision.json`, `src/hive/control/campaigns.py`, `frontend/console/src/routes/CampaignDetailPage.tsx`, `frontend/console/src/test/observeConsole.smoke.test.tsx` | Final release/demo validation only |
| Observe-and-steer console at RFC depth | Complete | `frontend/console/src/routes/RunDetailPage.tsx`, `frontend/console/src/routes/InboxPage.tsx`, `frontend/console/src/routes/CampaignDetailPage.tsx`, `tests/test_console_frontend_story.py`, `frontend/console/src/test/observeConsole.smoke.test.tsx` | Final release/demo validation only |
| Pi driver at acceptance bar | Pending | none | Decide whether Pi remains a v2.3 requirement or explicitly moves to later |
| Release docs, demo, and acceptance alignment | Pending | `docs/`, `docs/hive-v2.3-rfc/`, `tests/test_v23_runtime_foundation.py` | Tighten scope and prove the final release story end-to-end |

## Current Read

What is real now:

- the v2.3 runtime substrate is real enough to build on
- Codex and Claude are both substantially real as live supervised drivers
- approval truthfulness and runtime event/artifact plumbing are no longer just scaffolding
- local, hosted, and self-hosted sandbox paths all exist in code and tests
- the shipped operator console now surfaces capability truth, sandbox policy, retrieval traces, approval actions, and campaign decision reasoning

What is still holding back a clean release call:

- final acceptance and operator-grade validation for the sandbox matrix
- final decision on Pi scope for v2.3
- retrieval and campaign depth versus the RFC bar
- docs, console, and demo alignment so the shipped story matches the implementation

## Next Blocker

Lock the remaining release scope and turn the rest of v2.3 into a short
acceptance-driven train:

1. decide whether Pi and the full hybrid retrieval stack stay in v2.3 scope or are explicitly deferred
2. land the sandbox acceptance-and-docs slice for `local-safe`, E2B, and Daytona
3. align public docs and demo collateral with the real v2.3 operator story

## Update Rule

When a v2.3 PR merges:

- update the affected gate row
- record the PR or commit evidence
- rewrite `Next Blocker` if the critical path changed

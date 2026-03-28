# Hive v2.4 Status

Status: in progress
Last updated: 2026-03-28 (Pi milestone landed; Hermes is next)
Purpose: compact execution ledger for the current v2.4 release line

This file is the maintainer-facing status ledger for v2.4.
Update it when a v2.4 merge changes release readiness or moves the next blocker.

## Scope Lock

The v2.4 release scope is explicitly locked to the ecosystem-integration work defined in `docs/hive-v2.4-rfc/`:

- adapter-model correction: WorkerSession vs DelegateGateway
- Hive Link
- Pi native companion + attach + managed integration
- OpenClaw native companion + Gateway attach integration
- Hermes native companion + attach integration
- truthful advisory vs governed console/doc surfaces
- install/onboarding/doctor flows for all three harnesses

The following items are explicitly deferred from blocking v2.4:

- OpenClaw managed mode
- Hermes managed mode
- broader sandbox parity work deferred from v2.3
- remote vector backend work
- future continual-learning/backtesting implementation
- optional `mellona-hermes` alias/meta-package

## Release Gate Ledger

| Gate | Status | Evidence | Remaining blocker |
|---|---|---|---|
| Adapter-model correction | Landed | 47 tests, src/hive/integrations/ | — |
| Hive Link and normalized trajectory capture | Landed | src/hive/link/, src/hive/trajectory/, tests | — |
| Pi companion package | Landed | `packages/pi-hive/`, `src/hive/drivers/pi.py`, `src/hive/integrations/pi.py`, `tests/test_v24_pi_runtime.py` | — |
| Pi attach mode | Landed | `hive integrate attach pi`, `pi-hive attach`, advisory run persistence, steering round-trip tests | — |
| Pi managed mode | Landed | `hive run start --driver pi`, `pi-hive open`, `pi-hive-runner`, managed-run lifecycle tests | — |
| OpenClaw skill + bridge | Landed | `packages/openclaw-hive-bridge/` NDJSON protocol, ClawHub `agent-hive` skill + action wrappers, `src/hive/integrations/openclaw.py` | real Gateway HTTP calls in bridge |
| OpenClaw attach mode | Landed | delegate persistence, trajectory write-through, `hive integrate attach/detach`, bridge protocol tests | real Gateway session binding |
| Hermes companion integration | Landed | `src/hive/integrations/hermes.py`, `packages/hermes-skill/`, `hive integrate hermes`, 38 tests | — |
| Hermes trajectory import fallback | Landed | `import_hermes_trajectory()`, `hive integrate import-trajectory`, event kind mapping, provenance preservation | — |
| Truthful advisory/governed surfaces | Landed | console /integrations, driver doctor, run detail | — |
| Install docs and doctor flows | Landed | `hive integrate doctor pi/openclaw/hermes`, setup flows, READMEs | — |

## Current Read

What is real now:
- v2.3 closed the major Codex/Claude/runtime/retrieval/campaign/operator gaps
- Pi/Hermes/OpenClaw remain intentionally deferred from that line
- the next product opportunity is native ecosystem presence, not another generic RPC adapter
- the v2.4 RFC bundle and status ledger now live at stable repo paths and are wired into packaged-doc search surfaces
- Pi now has a real `pi` driver, live managed-run lifecycle wiring, advisory attach-run creation, native `pi-hive open/attach` commands, and persisted trajectory/steering artifacts
- OpenClaw companion + attach landed earlier in the line and remains green
- Hermes is now the remaining major harness milestone on the release line

## Next Blocker

Start Milestone 4 — Hermes companion + attach integration:
- ship the Hermes-native skill/toolset and doctor/setup flow
- attach a live Hermes session to Hive as an advisory delegate session
- persist normalized Hermes trajectories, including import fallback
- close the remaining harness parity gap for the v2.4 release line

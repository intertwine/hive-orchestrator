# Hive v2.4 Status

Status: in progress
Last updated: 2026-03-28 (Pi foundation slice in progress)
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
| Pi companion package | In progress | `packages/pi-hive/`, `src/hive/integrations/pi.py`, `tests/test_v24_pi_integration.py` | live Pi SDK link flow |
| Pi attach mode | In progress | attach-session scaffolding + trajectory persistence tests | manual attach CLI + live session binding |
| Pi managed mode | In progress | `src/hive/integrations/pi_managed.py`, `pi-hive-runner`, managed-session tests | real run-engine launch + Pi SDK session |
| OpenClaw skill + bridge | Landed | `packages/openclaw-hive-bridge/` NDJSON protocol, ClawHub `agent-hive` skill + action wrappers, `src/hive/integrations/openclaw.py` | real Gateway HTTP calls in bridge |
| OpenClaw attach mode | Landed | delegate persistence, trajectory write-through, `hive integrate attach/detach`, bridge protocol tests | real Gateway session binding |
| Hermes companion integration | Proposed | RFC only | skill/toolset + attach |
| Hermes trajectory import fallback | Proposed | RFC only | importer + tests |
| Truthful advisory/governed surfaces | Landed | console /integrations, driver doctor, run detail | — |
| Install docs and doctor flows | In progress | `hive integrate doctor pi/openclaw`, `hive integrate pi/openclaw`, bridge READMEs | Hermes parity + smoke paths |

## Current Read

What is real now:
- v2.3 closed the major Codex/Claude/runtime/retrieval/campaign/operator gaps
- Pi/Hermes/OpenClaw remain intentionally deferred from that line
- the next product opportunity is native ecosystem presence, not another generic RPC adapter
- the v2.4 RFC bundle and status ledger now live at stable repo paths and are wired into packaged-doc search surfaces
- Pi now has a real companion package skeleton, doctor/setup assistant payloads, and managed/attach session scaffolding in the repo

## Next Blocker

Finish Milestone 2 — Pi live attach and managed execution wiring:
- bind `pi-hive` to Hive Link without placeholder attach/open flows
- connect Pi managed launch into the real run lifecycle instead of session scaffolding only
- round-trip steering through the live Pi session
- expand PI-1/PI-2/PI-3 acceptance from foundation scaffolding to end-to-end behavior

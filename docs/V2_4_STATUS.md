# Hive v2.4 Status

Status: in progress
Last updated: 2026-03-28
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
| Adapter-model correction | Proposed | RFC only | implement base contracts |
| Hive Link and normalized trajectory capture | Proposed | RFC only | implement protocol + tests |
| Pi companion package | Proposed | RFC only | package skeleton + integration |
| Pi attach mode | Proposed | RFC only | session attach flow |
| Pi managed mode | Proposed | RFC only | managed runner |
| OpenClaw skill + bridge | Proposed | RFC only | bridge + skill assets |
| OpenClaw attach mode | Proposed | RFC only | Gateway session mapping |
| Hermes companion integration | Proposed | RFC only | skill/toolset + attach |
| Hermes trajectory import fallback | Proposed | RFC only | importer + tests |
| Truthful advisory/governed surfaces | Proposed | RFC only | console + doctor |
| Install docs and doctor flows | Proposed | RFC only | docs + smoke tests |

## Current Read

What is real now:
- v2.3 closed the major Codex/Claude/runtime/retrieval/campaign/operator gaps
- Pi/Hermes/OpenClaw remain intentionally deferred from that line
- the next product opportunity is native ecosystem presence, not another generic RPC adapter
- the v2.4 RFC bundle and status ledger now live at stable repo paths and are wired into packaged-doc search surfaces

## Next Blocker

Land Milestone 1 foundation work:
- add the adapter-family split (`WorkerSessionAdapter` vs `DelegateGatewayAdapter`)
- define Hive Link protocol/types and normalized trajectory helpers
- prove packaged/searchable dummy integration coverage
- surface advisory vs governed truth in the console and doctor flows

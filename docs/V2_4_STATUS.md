# Hive v2.4 Status

Status: v2.4.0 released
Last updated: 2026-04-06 (tag `v2.4.0`, PyPI publish, GitHub release, Homebrew update, and fresh public-install verification are complete)
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
| OpenClaw skill + bridge | Landed | `packages/openclaw-hive-bridge/` real gateway-backed NDJSON bridge, ClawHub `agent-hive` skill + action wrappers, `src/hive/integrations/openclaw.py` | — |
| OpenClaw attach mode | Landed | delegate persistence, real Gateway session binding, live follow bridge tests, `hive integrate attach/detach`, bridge protocol tests | — |
| Hermes companion integration | Landed | `src/hive/integrations/hermes.py`, `packages/hermes-skill/`, `hive integrate hermes`, 38 tests | — |
| Hermes trajectory import fallback | Landed | `import_hermes_trajectory()`, `hive integrate import-trajectory`, event kind mapping, provenance preservation | — |
| Truthful advisory/governed surfaces | Landed | console /integrations, driver doctor, unified run/delegate detail truth surfaces | — |
| Console truth + attach visibility proof | Landed | `tests/test_console_api.py`, frontend observe-console smoke, 3-second refresh wiring, delegate detail truth panels | — |
| Console inbox / exception parity | Landed | delegate blocked/note/error/approval inbox derivation, `tests/test_console_api.py`, frontend inbox smoke | — |
| Install docs and doctor flows | Landed | `hive integrate doctor pi/openclaw/hermes`, setup flows, READMEs | — |

## Current Read

What is real now:
- v2.3 closed the major Codex/Claude/runtime/retrieval/campaign/operator gaps
- Pi/Hermes/OpenClaw were intentionally deferred from that line and are now all landed on v2.4
- the next product opportunity is native ecosystem presence, not another generic RPC adapter
- the v2.4 RFC bundle and status ledger now live at stable repo paths and are wired into packaged-doc search surfaces
- Pi now has a real `pi` driver, live managed-run lifecycle wiring, advisory attach-run creation, native `pi-hive open/attach` commands, and persisted trajectory/steering artifacts
- OpenClaw now has real gateway-backed attach parity, persisted live-follow trajectory updates, and truthful detach/doctor behavior
- Hermes now has native companion integration, attach parity, and shared doctor contract fields
- the console now shows unified run/delegate truth across Pi, OpenClaw, and Hermes, and attached delegates appear within one refresh cycle at the RFC 3-second bound
- attached advisory sessions can now raise inbox-visible delegate exceptions and inbound notes without being dropped from operator views
- v2.4 implementation and launch/docs polish are now complete against the currently tracked RFC gates
- the repo version and maintainer release surfaces now read `2.4.0`
- the `v2.4.0` tag is published, the GitHub release is live, and PyPI serves the expected wheel and source tarball
- the release workflow, including PyPI publish and Homebrew verification/update, passed on GitHub Actions
- a fresh installed-tool verification on Python 3.11 proved packaged-doc search, `quickstart demo`, `console home`, and `task ready` against the public artifact instead of the repo checkout

## Release History

| Version | Date | Notes |
|---|---|---|
| `v2.4.0` | 2026-04-06 | Native ecosystem release: Pi/OpenClaw/Hermes companion flows, Hive Link + adapter-family truth surfaces, packaged docs/search, and public install verification from the shipped artifact. |

## Next Blocker

No current blocker. Next planned work: execute the v2.5 command-center foundations slice on top of the shipped v2.4.0 baseline, starting with the shell/design-token/app-IA work defined in the v2.5 Hive project.

## Update Rule

When a v2.4.x maintenance or follow-up PR merges:

- update the affected release-gate evidence or shipped read
- record the release or verification evidence if the shipped story changed
- rewrite `Next Blocker` if a new v2.4.x follow-up becomes the critical path

# Agent Hive v2.4 Implementation Plan

Status: Proposed  
Date: 2026-03-27

## 1. Delivery strategy

This release line should be built in **five milestones**.

Do not parallelize everything at once. The adapter model correction must land first or the rest will drift.

## 2. Milestone 0 — RFC and status wiring

### Deliverables
- add `docs/hive-v2.4-rfc/`
- add `docs/V2_4_STATUS.md`
- wire packaging includes for the new docs bundle
- link the new RFC from maintainer/release docs

### Acceptance
- installed package search can return v2.4 RFC hits
- maintainers have a new status ledger before feature work starts

## 3. Milestone 1 — Adapter-model correction and Hive Link

### Deliverables
- `WorkerSessionAdapter` base contract
- `DelegateGatewayAdapter` base contract
- `IntegrationLevel` enum
- `GovernanceMode` enum
- `CapabilitySnapshot` model
- `trajectory.jsonl` schema helpers
- `hive link serve`
- `hive integrate list`
- `hive integrate doctor`
- `hive attach`
- core console support for attached advisory sessions

### Code areas
- `src/hive/integrations/base.py`
- `src/hive/integrations/models.py`
- `src/hive/link/server.py`
- `src/hive/link/protocol.py`
- `src/hive/trajectory/*`
- CLI wiring
- console state/store/routes

### Acceptance
- a dummy adapter can attach and stream normalized events
- the console can display advisory vs governed truth
- `hive integrate doctor --json` returns declared/probed/effective capabilities

## 4. Milestone 2 — Pi integration

### Deliverables
- `packages/pi-hive`
- Pi companion actions
- Pi attach flow
- Pi managed runner
- Pi capability doctor
- Pi docs and first-run guide

### Code areas
- `packages/pi-hive/*`
- `src/hive/integrations/pi.py`
- `src/hive/integrations/pi_managed.py`
- tests for attach + managed
- docs/compare/install/operator pages

### Acceptance
- a Pi user can install one package and connect to Hive in under 5 minutes
- an existing Pi session can attach to Hive without relaunch
- Hive can launch a governed Pi managed run
- steering works in both attach and managed modes
- normalized trajectories are persisted

## 5. Milestone 3 — OpenClaw integration

### Deliverables
- `packages/openclaw-hive-bridge`
- `agent-hive` ClawHub skill assets/docs
- Gateway attach support
- sessionKey ↔ Hive mapping
- steering back to Gateway
- OpenClaw integration doctor

### Code areas
- `packages/openclaw-hive-bridge/*`
- `src/hive/integrations/openclaw.py`
- delegate-session persistence
- console detail views for delegate sessions
- docs/install and gateway attach guides

### Acceptance
- an OpenClaw user can install the skill and bridge, then attach a live Gateway session in under 5 minutes
- live transcript/history appears in Hive without transcript copy/paste
- steering round-trips back to OpenClaw
- integration truth clearly says advisory and names the actual sandbox owner

## 6. Milestone 4 — Hermes integration

### Deliverables
- built-in Hermes integration
- exportable Hermes skill/toolset bundle
- gateway/CLI attach support
- trajectory import fallback
- Hermes integration doctor
- Hermes setup docs

### Code areas
- `src/hive/integrations/hermes/*`
- `packages/hermes-skill/*`
- docs/Hermes install and attach pages
- console delegate/advisory surfaces
- tests for live attach and fallback import

### Acceptance
- a Hermes user can enable Hive support and attach a live session or cron job
- a Hermes user can still stay in Hermes-native flows
- no private Hermes memory is bulk-imported
- trajectory export fallback imports correctly when live attach is unavailable

## 7. Milestone 5 — Product polish and launch

### Deliverables
- compare-harness docs update
- operator flow update for companion/attach
- demos/screenshots for all three harnesses
- FAQ for advisory vs governed
- release smoke paths
- launch collateral

### Acceptance
- README/Start Here reflect the real v2.4 story
- the console makes attach/advisory truth obvious
- release docs and status ledger are aligned

## 8. Suggested issue tree

### Epic A — adapter model
- A1 base adapter split
- A2 Hive Link protocol
- A3 trajectory schema
- A4 console surfaces
- A5 doctor surfaces

### Epic B — Pi
- B1 package skeleton
- B2 companion actions
- B3 managed runner
- B4 attach bridge
- B5 docs/demo/tests

### Epic C — OpenClaw
- C1 bridge skeleton
- C2 Gateway session attach
- C3 skill assets
- C4 steering path
- C5 docs/demo/tests

### Epic D — Hermes
- D1 integration skeleton
- D2 skill/toolset bundle
- D3 gateway/CLI attach
- D4 trajectory import
- D5 docs/demo/tests

### Epic E — launch polish
- E1 compare docs
- E2 operator flows
- E3 smoke installs
- E4 release notes
- E5 metrics dashboards

## 9. Rollout order for coding agent execution

Give Codex or Claude this exact order:

1. wire the RFC/status docs into the repo
2. land Milestone 1 adapter contracts and dummy integration tests
3. finish Pi end to end
4. finish OpenClaw end to end
5. finish Hermes end to end
6. polish console/docs and close release gates

Do not start OpenClaw/Hermes before Milestone 1 stabilizes.

## 10. Compatibility and truthfulness rules

### 10.1 Backward compatibility
- existing Codex/Claude/live drivers remain unchanged
- existing `hive next/work/finish` manager loop stays intact
- new attach/integrate surfaces add capability; they do not replace the current loop

### 10.2 Truthfulness
- if an integration cannot steer, say so
- if an integration cannot export structured tool events, say so
- if Hive does not own the sandbox, say so
- if the session is advisory only, say so

## 11. Telemetry and v2.5 setup

Every v2.4 integration must record:
- harness name + native version
- integration level
- governance mode
- capability snapshot
- native session handle
- trajectory
- steering and approval events
- finish/escalate disposition

This is the minimum substrate for later backtesting and continual learning.

## 12. Release call

Call v2.4 done only when:
- Pi companion + attach + managed are real
- OpenClaw companion + attach are real
- Hermes companion + attach are real
- all three are visible and truthful in the console
- onboarding works without hand-edited mystery config

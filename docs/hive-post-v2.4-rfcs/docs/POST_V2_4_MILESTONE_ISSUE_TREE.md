# Post-v2.4 Milestone Issue Tree

## v2.5 — Command Center

### M1 — Design system and shell-ready frontend
- define token system
- standardize layout primitives
- unify action registry
- route cleanup and deep-link rules
- saved-view model
- command palette backend and UI
- notification/event primitives
- UI smoke tests

### M2 — Operator workflows
- inbox grouping / filtering / bulk actions / snooze
- run detail redesign
- run compare
- search preview and provenance
- onboarding wizard
- help / docs surfacing
- preferences and shortcuts
- accessibility pass

### M3 — Desktop beta and launch polish
- Tauri shell bootstrap
- daemon lifecycle management
- tray
- native notifications
- deep-link open
- update-check path
- installer/build docs
- demo/screenshot refresh

## v2.6 — Task Master Foundations

### M1 — Mission state
- state schema
- committed-plan/open-threads/state-evidence artifacts
- mission-state compiler
- console mission-state views

### M2 — Heartbeats and wake loop
- heartbeat schema
- governed heartbeat adapters
- advisory status bridge
- taskmaster service
- wake reasons and action ledger

### M3 — Review broker and explainability
- review broker
- stale-run detection
- status request flows
- policy editor
- circuit breakers
- explain views and CLI explain command

## v2.7 — Mission Governor

### M1 — Autopilot eligibility and launch-next
- autopilot modes
- doctor checks
- next-run launch integration
- harness/sandbox policy selection
- decision log UI

### M2 — Rescue and side quests
- reroute
- research side quests
- merge-back summaries
- blocker-unlock workflows
- review swarm

### M3 — Operational autonomy polish
- daily/overnight briefs
- quiet-autopilot
- better escalations
- autopilot controls in console
- incident/recovery flows

## v3.0 — Hive Lab

### M1 — Case files and graders
- case-file schema
- collector jobs
- grader framework
- benchmark definitions
- lab inspection UI/CLI

### M2 — Proposals and backtests
- proposal artifact schema
- generator for skill/policy/context proposals
- replay harness
- metric reports
- approval workflow

### M3 — Canary and promotion
- canary manager
- rollback
- promotion workflow
- proposal registry
- adoption dashboard

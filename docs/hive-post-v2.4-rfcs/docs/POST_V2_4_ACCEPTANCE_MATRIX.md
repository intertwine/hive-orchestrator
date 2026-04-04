# Post-v2.4 Acceptance Matrix

## v2.5 — Command Center

### Must ship
- browser console GA polish
- design system and action model
- command palette
- inbox overhaul
- run detail overhaul
- search provenance UX
- notifications center
- onboarding wizard
- saved views / preferences

### Nice to ship
- Tauri desktop beta
- run compare against prior accepted runs
- richer activity feed
- packaged demo workspace

### Release gate
The console feels like a product, not a maintainer surface.

## v2.6 — Task Master Foundations

### Must ship
- mission-state artifacts
- structured heartbeats
- taskmaster service
- review broker alpha
- policy / circuit breakers
- explainability surfaces

### Nice to ship
- richer advisory heartbeat coverage for OpenClaw/Hermes
- better quiet-hours model
- smarter stale-state detection

### Release gate
Hive proactively requests status and review so the human is no longer manually shepherding routine coordination.

## v2.7 — Mission Governor

### Must ship
- governed-autopilot mode
- autonomous next-run launch
- reroute and rescue actions
- review swarm
- side-quest handling
- daily/overnight briefs
- operator autopilot controls

### Nice to ship
- multiple autopilot templates
- richer campaign-health heuristics
- more nuanced quiet-autopilot behavior

### Release gate
Healthy governed campaigns can keep moving without the human acting as the invisible foreman.

## v3.0 — Hive Lab

### Must ship
- case-file schema
- graders and benchmark sets
- proposal generation
- backtesting
- canary/rollback
- proposal registry

### Nice to ship
- retrieval tuning proposals
- scheduler/tasmaster policy tuning proposals
- experimental model-adapter lane

### Release gate
Hive can learn from history offline in a way that is evidence-based, reviewable, and rollback-safe.

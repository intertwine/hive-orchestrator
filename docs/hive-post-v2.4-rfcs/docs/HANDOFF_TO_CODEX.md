# Handoff to Codex

Implement these releases in order. Do not collapse them into one giant milestone.

## Hard decisions already made

1. **Publish v2.4 before theme work.**
2. **v2.5 is a console-first release.**
3. **Choose Tauri 2 for the desktop shell path.**
4. **Task Master is the next autonomy theme and stays inside Hive.**
5. **v3.0 remains offline learning, not live self-editing.**

## What not to do

- Do not start with Electron unless Tauri hits a demonstrated blocker.
- Do not create a separate desktop-only product line.
- Do not skip the browser console while chasing desktop packaging.
- Do not implement full mission governor behavior before mission-state, heartbeats, and explainability exist.
- Do not let the future lab mutate production behavior without review and rollback.

## Recommended implementation order

### First
- version bump and publish v2.4
- post-release cleanup
- confirm docs/package includes

### Then v2.5
- build design system and action registry first
- make the browser console excellent before desktop shell work
- keep desktop as beta unless it is clearly production-ready

### Then v2.6
- mission-state compiler
- heartbeat contract
- taskmaster service
- review broker
- explainability surfaces

### Then v2.7
- governed-autopilot
- rescue and reroute
- review swarm
- briefs and autopilot controls

### Then v3.0
- case files
- graders
- proposal generator
- backtesting
- canaries

## Cross-release rules

- Keep CLI and APIs stable and scriptable.
- Keep advisory vs governed truth explicit everywhere.
- Preserve packaged-doc search quality for installed users.
- Treat UX polish as real engineering work, not as post-hoc dressing.

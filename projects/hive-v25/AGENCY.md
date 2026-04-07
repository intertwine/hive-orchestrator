---
priority: 1
project_id: hive-v25
status: active
---

# Hive v2.5 Command Center

## Mission
Deliver RFC 2.5 as a browser-first command center release: polished command-center UX, one action model, trustworthy review ergonomics, onboarding, search provenance, preferences, accessibility, and a thin Tauri 2 desktop beta without regressing CLI or browser parity.

## Notes
Use this document for human context, links, architecture notes, and handoff details.

- Visual direction: adapt the Clay design language from the v2.5 handoff bundle into a dense browser-first operator console rather than a marketing-page clone.
- Sequencing: finish the public v2.4.0 release before claiming substantive v2.5 implementation slices, but keep the v2.5 task tree and policy ready so work can start immediately after the cut.

## Working Rules
- Keep canonical task state in `.hive/tasks/*.md`.
- Read `PROGRAM.md` before autonomous edits or evaluator runs.
- Refresh projections after state changes with `hive sync projections --json`.

<!-- hive:begin task-rollup -->
## Task Rollup

| ID | Status | Priority | Owner | Title |
|---|---|---:|---|---|
| task_01KNHQFZ3JMPSZ0QKYSP0HT99F | done | 1 |  | Add preferences, saved views, and operator-local state persistence |
| task_01KNHQGWQKZXDNEWHWVZ6QS89H | archived | 1 |  | Add preferences, saved views, and operator-local state persistence |
| task_01KNHQFZ4GMPSP19APVZZYB1N5 | done | 1 |  | Add real-time event, notification, and freshness primitives for the browser console |
| task_01KNHQHTYKXVTJXR7SGZGWMNJ9 | archived | 1 |  | Add real-time event, notification, and freshness primitives for the browser console |
| task_01KNHQP3P6SXH8MZB706YYVKQD | done | 1 |  | Add startup wizard, workspace chooser, help surfaces, and safe-first onboarding |
| task_01KNHQBQ773EB9RJSX7AGK1EH0 | done | 1 |  | Bootstrap the v2.5 project, policy, and canonical task tree |
| task_01KNHQEYG1721BBK9JS5EVZP03 | done | 1 | codex | Build the Clay-aligned command-center design system and token library |
| task_01KNHQAX8SBVVSJKRE2FERDPG7 | proposed | 1 |  | Deliver RFC 2.5 Command Center as a browser-first product release |
| task_01KNHQFZ1FE415P7TX42WRYKJD | done | 1 | codex | Implement the shared action registry, action execution APIs, and command palette |
| task_01KNHQGDQN66GEZ5M3HDAS0WC0 | archived | 1 |  | Implement the shared action registry, action execution APIs, and command palette |
| task_01KNHQK443Q889CY875N9QB70Z | archived | 1 |  | Implement the shared action registry, action execution APIs, and command palette |
| task_01KNHQM9P6HGZ50D2GSMTA49RS | archived | 1 |  | Implement the shared action registry, action execution APIs, and command palette |
| task_01KNHQCCFAB4KWR88RGJX2JJTF | proposed | 1 |  | M1: Design system and shell-ready frontend foundations |
| task_01KNHQD1FSKPPQGN4PXVCM6HCD | proposed | 1 |  | M2: Operator workflows, review ergonomics, and adoption polish |
| task_01KNHQKPDZVGABQCEVT9S0VR95 | done | 1 | codex | Overhaul inbox triage, bulk actions, snooze, and the notifications center |
| task_01KNHQQD92MKY1163YSGFHG0WX | ready | 1 |  | Pass accessibility and responsiveness hardening for the primary v2.5 surfaces |
| task_01KNHQMEZWBXKK8CVJ5AJ48HNK | done | 1 | codex | Rebuild run detail with review rails, compare-runs, and explain surfaces |
| task_01KNHQFPPS275AERJPMX8ERTZN | done | 1 |  | Refactor the console shell, routing, and deep-link contract to the full v2.5 IA |
| task_01KNHQFZ0JQ689T9HWY0PGC28M | archived | 1 |  | Refactor the console shell, routing, and deep-link contract to the full v2.5 IA |
| task_01KNHQHEEM0QEC8YK2KH63H58W | archived | 1 |  | Refactor the console shell, routing, and deep-link contract to the full v2.5 IA |
| task_01KNHQJX5VKQE4DGZK4KPHBY4C | done | 1 | codex | Strengthen the console validation harness with component, E2E, and accessibility gates |
| task_01KNHQMXZC3D86Z2JNPR29SQ81 | done | 1 | codex | Upgrade search to explainable unified provenance with previews and open-in-context flows |
| task_01KNHQS6FZW0PECASBK1NW0HWA | ready | 2 |  | Add daemon lifecycle, tray, native notifications, and desktop deep-link handling |
| task_01KNHQPJM4RKGESMF9YV2H3RM6 | done | 2 | codex | Add settings, activity, and keyboard-shortcut help surfaces |
| task_01KNHQRCC2ED8B89SGNJ6C6GCX | ready | 2 |  | Bootstrap the Tauri 2 desktop shell beta around the shared command-center frontend |
| task_01KNHQT4PK1BMNDQK8Z4BS9DBG | ready | 2 |  | Document desktop packaging, permissions, update path, and operator expectations |
| task_01KNHQE7RS8JDFC221XF3N5QGV | proposed | 2 |  | M3: Tauri desktop beta and launch polish |
| task_01KNHQTZ7WVABJPAWSCY2RD1X5 | ready | 2 |  | Refresh demo collateral, screenshots, and launch proof for the v2.5 Command Center |
<!-- hive:end task-rollup -->

<!-- hive:begin recent-runs -->
## Recent Runs

| Run | Status | Task |
|---|---|---|
| No runs | - | - |
<!-- hive:end recent-runs -->

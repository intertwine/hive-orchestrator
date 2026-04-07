# Hive v2.5 Status

Status: draft release candidate
Last updated: 2026-04-07 (the browser-first command center, desktop beta, docs, launch collateral, and acceptance-ledger work are merged on `main`; version bump/tag/publish are intentionally pending the final walkthrough and release cut)
Purpose: compact execution ledger for the active v2.5 draft release line

This file is the maintainer-facing status ledger for v2.5.
Update it when a v2.5 merge changes draft-release readiness, acceptance proof, or the next blocker.

## Scope Lock

The v2.5 draft release scope is explicitly locked to the command-center work defined in `docs/hive-post-v2.4-rfcs/`:

- Clay-aligned browser-first command-center shell, IA, and design system
- one shared action model across visible controls, row menus, keyboard shortcuts, command palette, and deep links
- operator-local preferences, saved views, and persistent console state
- real-time freshness, inbox triage, notifications, and explanation surfaces
- run-detail review ergonomics including compare-runs, acceptance rationale, evaluator truth, and steering history
- unified search with previews, provenance, and open-in-context navigation
- startup wizard, workspace chooser, help surfaces, settings, and activity views
- accessibility, responsiveness, keyboard-complete navigation, and console-focused validation gates
- a thin Tauri 2 desktop beta around the same frontend and local API contract
- updated docs, screenshots, and demo collateral that match the new command-center UX

The following items are explicitly deferred from blocking the v2.5 draft release:

- labeling the desktop shell as GA instead of beta
- cross-platform installer and updater hardening beyond the current beta path
- a public version bump, tag, and publish step for the eventual v2.5 cut

## Release Gate Ledger

| Gate | Status | Evidence | Remaining blocker |
|---|---|---|---|
| Browser-first command-center shell and design system | Landed | `frontend/console/src/styles.css`, `frontend/console/src/components/ConsoleLayout.tsx`, `frontend/console/src/App.tsx`, `tests/test_console_frontend_story.py` | — |
| Shared action model and command palette | Landed | `frontend/console/src/components/ConsoleActions.tsx`, `src/hive/console/actions.py`, `src/hive/console/api.py`, `frontend/console/src/test/consoleLayout.test.tsx` | — |
| Preferences, saved views, and operator-local state | Landed | `frontend/console/src/preferences.ts`, `frontend/console/src/components/ConsolePreferences.tsx`, `frontend/console/src/routes/RunsPage.tsx`, `frontend/console/src/test/consolePreferences.test.ts` | — |
| Real-time freshness, inbox triage, and notifications | Landed | `frontend/console/src/components/ConsoleEventBus.tsx`, `frontend/console/src/routes/InboxPage.tsx`, `frontend/console/src/routes/NotificationsPage.tsx`, `frontend/console/src/test/consoleEventBus.test.tsx`, `tests/test_console_api.py` | — |
| Run-detail review ergonomics and compare/explain truth | Landed | `frontend/console/src/routes/RunDetailPage.tsx`, `src/hive/console/api.py`, `tests/test_console_api.py`, `frontend/console/src/test/observeConsole.smoke.test.tsx` | — |
| Unified search with previews and provenance | Landed | `frontend/console/src/routes/SearchPage.tsx`, `src/hive/console/api.py`, `tests/test_hive_v2.py`, `frontend/console/src/test/consoleAccessibility.test.tsx` | — |
| Onboarding, workspace chooser, settings, activity, and help | Landed | `frontend/console/src/routes/HomePage.tsx`, `frontend/console/src/routes/SettingsPage.tsx`, `docs/START_HERE.md`, `tests/test_console_frontend_story.py` | — |
| Accessibility, responsiveness, and console validation gates | Landed | `frontend/console/src/test/consoleAccessibility.test.tsx`, `frontend/console/src/test/observeConsole.smoke.test.tsx`, `Makefile`, `.github/workflows/ci.yml` | — |
| Desktop beta shell and native affordances | Landed | `frontend/console/src/desktopShell.ts`, `frontend/console/src-tauri/src/lib.rs`, `frontend/console/src-tauri/tauri.conf.json`, `frontend/console/src/test/desktopShell.test.ts`, `tests/test_console_frontend_story.py` | — |
| Desktop permissions, packaging guidance, and operator expectations | Landed | `docs/DESKTOP_BETA.md`, `frontend/console/README.md`, `tests/test_console_frontend_story.py` | — |
| Launch collateral, screenshots, and demo walkthrough | Landed | `README.md`, `docs/DEMO_WALKTHROUGH.md`, `images/launch/`, `frontend/console/scripts/captureDemoAssets.mjs`, `tests/test_launch_collateral.py` | — |
| Draft release acceptance ledger and canonical task reconciliation | Validated locally | `docs/V2_5_STATUS.md`, `projects/hive-v25/AGENCY.md`, `.hive/tasks/task_01KNHQAX8SBVVSJKRE2FERDPG7.md`, `tests/test_maintainer_surfaces.py` | — |

## Current Read

What is real now:

- v2.4.0 is the shipped public line, and v2.5 work is merged on top of that baseline without changing the published package version yet
- the browser console now matches the command-center IA and review model described in the v2.5 RFC
- the primary operator workflows are live: Inbox, Runs, Run Detail, Search, Settings, Activity, Notifications, and workspace onboarding
- saved views, explanation surfaces, compare-runs, and deep links are all part of the merged operator story rather than draft-only concepts
- no normal operator flow should require habitual full-page refresh behavior; the real-time freshness layer and notification model are now part of the console substrate
- the desktop shell is real and dogfoodable, but it is intentionally still described as beta in code, docs, and operator expectations
- launch collateral, screenshots, and the browser-first demo walkthrough now match the current UI instead of the older observe-console scaffold
- the remaining release decision is not implementation completeness; it is when to stage the version bump and publish the eventual v2.5 cut after walkthrough signoff

## Release History

| Milestone | Date | Notes |
|---|---|---|
| Draft release candidate | 2026-04-07 | Browser-first command center, desktop beta, docs, launch collateral, and acceptance-ledger proof are merged on `main`; package version remains `2.4.0` until the public v2.5 cut is intentionally staged. |

## Next Blocker

No implementation blocker. Next planned work: run the final maintainer walkthrough, decide the version-bump/tag/publish plan for v2.5, and cut the release only after that walkthrough is accepted.

## Update Rule

When a v2.5 merge changes the release story:

- update the affected gate evidence or remaining blocker
- keep the desktop-beta language truthful unless the shell is intentionally promoted out of beta
- rewrite `Current Read` and `Next Blocker` so maintainers can tell at a glance whether v2.5 is still a draft candidate or has moved into release execution

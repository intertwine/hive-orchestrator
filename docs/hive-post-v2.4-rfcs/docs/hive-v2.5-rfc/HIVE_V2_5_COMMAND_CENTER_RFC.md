# Hive v2.5 RFC — Command Center

## Thesis

Hive already has the right substrate. v2.5 should make the console the product users actually want to live in.

The goal is not “make the UI prettier.”  
The goal is to turn the current observe-and-steer console into a **first-class command center**:

- instantly legible
- trustworthy
- keyboard-friendly
- review-efficient
- adoption-ready
- desktop-ready

## Product promise

A new user should be able to install Hive, open the console, understand what matters, and take the next correct action with minimal CLI fallback.

A power user should be able to stay fast through keyboard shortcuts, deep links, run compare, saved views, and bulk triage.

A maintainer should be able to demonstrate Hive in a polished way without apologizing for UX rough edges.

## Design principles

1. **Exceptions first.** The home view is for attention and decisions, not browsing files.
2. **Show, don’t bury.** Important state changes, acceptance rationale, blocked reasons, and approval needs must be visible without hunting.
3. **One action model.** Buttons, command palette, row menus, keyboard shortcuts, and deep links should all map to the same small action vocabulary.
4. **Progressive disclosure.** Summary first, evidence on demand.
5. **Trust through provenance.** Every action and every recommendation must expose why it exists.
6. **Mouse and keyboard parity.** The console should feel native to both operators and power users.
7. **Desktop-ready, browser-first.** The console must remain an excellent browser app even if a desktop shell exists.
8. **Accessibility is not optional.** Keyboard navigation, focus order, contrast, and screen-reader labels are release gates.

## Scope

## In scope

### 1. Information architecture cleanup
Refine the core console structure:

- Home
- Inbox
- Runs
- Campaigns
- Projects
- Search
- Settings
- Integrations
- Notifications
- Activity

### 2. Design system
Create a coherent visual and interaction system:

- typography scale
- spacing scale
- color tokens
- severity/status tokens
- action button hierarchy
- layout primitives
- table/list card patterns
- timeline/event patterns
- drawers/modals/sheets
- empty/error/loading states

### 3. Action center / command palette
Add a global command palette that can:

- open run/task/project/campaign
- claim work
- start run
- finish run
- approve / reject / reroute
- send steering note
- pause / resume campaign
- open doctor results
- open search
- open docs
- toggle saved views

### 4. Run detail and review ergonomics
Make the most important inspection view truly excellent:

- timeline scrubber
- sticky action rail
- artifact tabs
- diff and changed-file summaries
- acceptance rationale
- evaluator outputs
- capability truth
- sandbox truth
- retrieval trace
- context inputs
- steering history
- compare current run to previous accepted run

### 5. Inbox triage
Give operators an actually useful inbox:

- grouped by severity and decision type
- bulk dismiss / resolve / assign
- snooze
- deep links
- “why am I seeing this?”
- “what happens if I ignore it?”
- saved filters

### 6. Search and provenance
Upgrade search UX:

- unified result list across tasks, runs, docs, memory, recipes, campaigns, and delegates
- reasons for match
- deduped projections
- preview snippets
- filters by project/source/harness/time
- open in context

### 7. Notifications and activity feed
Add a persistent notification center and compact recent-activity feed:

- inbox-worthy notifications
- informational notifications
- approvals
- delegate notes
- failures / escalations
- campaign brief ready
- release/install warnings

### 8. Onboarding and non-power-user UX
Add a guided path from install to first useful action:

- startup wizard
- workspace chooser
- install/doctor surfaces
- inline explanations
- “what is safe to click?”
- sample/demo workspace path
- concise built-in help

### 9. Preferences and saved views
Operator-local state:

- saved filters
- view density
- default page
- notification preferences
- keyboard shortcuts help
- dark/light/system theme
- hidden columns / pinned panels

### 10. Desktop beta support
Ship a Tauri shell beta that wraps the same frontend and daemon surfaces.

## Out of scope

- full autonomous mission governance
- offline learning/backtesting
- deep new harness types
- major sandbox redesign
- changing the canonical CLI/API substrate

## Experience targets

- No manual refresh or sync buttons in primary flows.
- Top ten operator actions are possible from UI without dropping to CLI.
- Every inbox item and run detail page answers “what happened?” and “what should I do?”.
- The first-run path feels productized, not like maintainers’ internal tooling.

## Architecture

## Frontend
Keep the current web frontend and API model, but make it shell-friendly:

- stateful URL routing
- stable deep links
- optimistic UI where safe
- SSE/websocket updates where appropriate
- cached data with visible freshness
- shared component library
- UI test harness

## Backend
Add or refine endpoints to support the UI without frontend logic spelunking:

- unified inbox API
- notification API
- compare-runs API
- saved views/preferences API
- action execution endpoints
- explain endpoints for decisions and recommendations
- startup wizard endpoints

## Desktop readiness
The web UI must be able to run:

- in a normal browser
- in a local Tauri shell
- from the same local API contract

## Milestones

## M1 — Foundations
Deliver:

- design system
- route cleanup
- shell-friendly frontend structure
- action registry
- command palette
- saved views/preferences model
- unified event/notification primitives

## M2 — Operator excellence
Deliver:

- inbox overhaul
- run detail overhaul
- compare runs
- notifications center
- activity feed
- onboarding wizard
- built-in help and docs surfacing

## M3 — Desktop beta + launch polish
Deliver:

- Tauri beta shell
- tray and notification plumbing
- deep-link handling
- start/stop local daemon
- release packaging docs
- demo polish and screenshots

## Acceptance criteria

### Functional
- The console exposes Home, Inbox, Runs, Campaigns, Projects, Search, Integrations, Notifications, and Settings.
- The top ten operator actions are available from both visible UI controls and a command palette.
- Run detail includes acceptance rationale, evaluator outputs, capability truth, sandbox truth, retrieval trace, and steering history.
- Inbox supports bulk actions, snooze, filters, and deep links.
- Saved views survive restarts.

### UX
- No page requires a manual full refresh to reflect normal run/inbox changes.
- Keyboard users can navigate all primary surfaces without a mouse.
- Axe or equivalent automated accessibility checks show zero critical violations on Home, Inbox, Run Detail, Campaigns, and Search.
- New users can complete install → onboard → console → take first action using the published quick path without reading maintainer docs.

### Trust
- Every recommendation, notification, and inbox item has an explanation surface.
- No raw internal identifier is the only visible label for a user-facing item.
- Empty states explain what the user should do next.

### Performance
- The demo workspace feels responsive on a typical developer laptop.
- Run/inbox updates appear in the console quickly enough to support supervision without habitual refresh behavior.
- Search returns explainable results with previews instead of dumping raw IDs.

### Release
- The browser console is GA-quality.
- The Tauri shell is clearly labeled beta if shipped in v2.5.
- Documentation, screenshots, and demo scripts are updated to match the new UI.

# Hive v2.5 Decision Memo — Desktop Shell

## Decision

Choose **Tauri 2** for the Agent Hive desktop shell path.

Do **not** choose Electron unless Tauri hits a real blocking issue.  
Do **not** choose Wails for this release train.

## Why

Hive already has:

- a local web frontend
- a local daemon / CLI
- a browser-based operator model

The desktop requirement is therefore not “build a second app.”  
It is “wrap the same command center in a good desktop shell with OS integrations.”

Tauri 2 fits that shape well:

- system-webview architecture
- capability-based security model
- plugin permissions
- official updater, tray, dialog, notification, and store plugins
- smaller footprint than Electron
- good fit for a local control-plane app

Electron is still viable and has very mature updater patterns, but it brings a heavier runtime and a larger security/maintenance surface because the app ships Chromium and Node. Wails v3 is still alpha and should not be the bet for a product-facing release.

## Product stance

The desktop app is **not** a separate product line.

It is:

- the same command center frontend
- talking to the same local Hive API/daemon
- with extra OS affordances:
  - tray
  - native notifications
  - file/folder open
  - startup at login (optional)
  - updater
  - local workspace chooser
  - deep links

## Architecture

## Shared pieces
- One frontend codebase.
- One API contract.
- One action registry.
- One URL/deep-link model.

## Desktop-only pieces
- shell launcher
- daemon lifecycle manager
- tray
- updater
- notification bridge
- local file/folder open helpers
- desktop preferences store

## Security rules
- no Node integration model like Electron’s default historical patterns
- minimal Tauri capabilities per window
- plugin permissions scoped tightly
- desktop shell never becomes a second hidden control plane
- all governance truth still comes from Hive, not shell-local state

## Release plan

### v2.5
Ship **desktop beta**:

- start local Hive daemon
- open console window
- tray icon with basic actions
- native notifications for inbox-worthy items
- deep links into runs/tasks/campaigns
- update check path
- workspace picker

### v2.6
Stabilize desktop:

- installer polish
- updater hardening
- crash reporting / diagnostics
- startup/login behavior
- better offline/reconnect handling
- multiple workspace support if needed

### v2.7+
Decide desktop GA based on:
- adoption
- support burden
- telemetry
- cross-platform reliability

## Acceptance criteria

- The same user can use Hive entirely in a browser or entirely in the desktop shell.
- Desktop deep links open the correct run/task/campaign detail page.
- Native notifications can bring the user directly to the relevant item.
- Tray actions can open the app, pause notifications, and quit gracefully.
- The desktop shell starts and stops the local daemon safely.
- Desktop-specific permissions are documented and intentionally constrained.

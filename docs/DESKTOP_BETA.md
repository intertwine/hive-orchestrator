# Command Center Desktop Beta

Hive v2.5 includes a desktop beta built with Tauri 2.

This is not a separate product line. It is the same command center frontend and the same local Hive API contract in a native shell. The browser console remains the primary supported path. The desktop shell is an opt-in beta for operators who want tray behavior, native notifications, and desktop deep links on top of the shared command center.

## Current Product Truth

- Browser-first remains the default and most stable way to use Hive.
- The desktop shell is labeled beta in the native window title and docs.
- `mellona-hive[console]`, Homebrew, and the normal CLI install paths do not currently install a native desktop app.
- The desktop shell is currently a source-build path from this repository, not a published installer track.

## Build And Run From Source

From the repository root:

```bash
cd frontend/console
pnpm install
pnpm run tauri:dev
```

Useful desktop-specific checks:

```bash
cd frontend/console
pnpm run tauri:check
pnpm run tauri:build
```

- `tauri:dev` runs the shared desktop-targeted Vite build plus the native shell.
- `tauri:check` performs a debug desktop build without bundling installers.
- `tauri:build` produces the native bundle targets configured by Tauri.

## Packaging Behavior

The desktop beta is intentionally thin:

- it renders the same command center frontend as the browser path
- it uses a desktop-targeted Vite build output under `frontend/console/dist-desktop`
- it keeps the same local Hive API default at `http://127.0.0.1:8787`
- it keeps the same API base and workspace-path controls inside the shared UI

The shell does not ship a separate backend. On startup it behaves like this:

1. Probe `http://127.0.0.1:8787/health`.
2. If a healthy Hive API is already running, reuse it and do not claim ownership.
3. Otherwise try `uv run hive console api --host 127.0.0.1 --port 8787` from the repo root.
4. If that is unavailable, fall back to `hive console api --host 127.0.0.1 --port 8787`.
5. On quit, only stop the child process that the shell started itself.

That “reuse existing API first, stop only owned child” rule is the key daemon-safety contract for the beta shell.

## Current Desktop Features

The current beta includes:

- a tray menu that currently exposes exactly five actions: `Open Command Center`, `Open Notifications`, `Pause desktop notifications`, `Resume desktop notifications`, and `Quit`
- native notifications driven by the shared notification model
- deep links through the `agent-hive://` custom scheme
- single-instance handoff so a second launch can bring the existing window forward
- close-to-tray behavior instead of immediate process exit

Notification clicks and deep links can still route operators into richer context, including inbox- and run-related surfaces, but those are not separate tray menu entries today.

Deep links reuse the shared browser routing model:

- runs open into the existing run detail route
- campaigns open into the existing campaign route
- tasks resolve into the current task context through search, because the command center still does not have a standalone task-detail page

## Permissions And Security

The desktop beta keeps the permission surface intentionally small.

Current checked-in Tauri capability file for the `main` window grants:

- `core:default`
- `notification:default`

Current desktop plugin/config surface:

- single-instance handoff plugin enabled
- deep-link scheme: `agent-hive`
- native notification plugin enabled

Deep linking is wired through the desktop plugin configuration instead of a separate checked-in entry in the `permissions` array above.

Not currently enabled:

- updater plugin permissions
- filesystem picker/dialog permissions for a native workspace chooser
- shell-open or broad filesystem permissions

This is deliberate. The desktop shell must not become a second hidden control plane, and governance truth still lives in Hive itself rather than shell-local state.

## Update Path

The current beta does not have a native updater or an in-app update check wired yet.

Today, updates are manual:

- pull the latest repository changes
- rebuild or rerun the desktop shell from source

The v2.5 decision memo still treats updater work as part of the desktop roadmap, but the implemented beta has not reached that point yet. For now, document the update story as manual source rebuilds, not automatic desktop updates.

## Workspace Expectations

The current beta does not yet add a native desktop workspace picker. Operators still set:

- API base
- workspace path

through the same shared Settings and top-bar controls used by the browser console.

If you need the simplest supported path today:

1. start with the browser console
2. confirm the workspace and API path there
3. use the desktop beta only when you specifically want tray, notification, or deep-link affordances

## Release Position

For v2.5:

- browser command center: product release path
- desktop shell: beta path

The desktop shell is good enough to dogfood and validate, but it should still be described as beta in docs, reviews, and operator expectations until packaging, update behavior, and cross-platform polish are hardened further.

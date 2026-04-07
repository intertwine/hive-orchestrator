# Hive Observe Console

This is the React/Vite frontend for the Hive Observe Console.

For the browser console, run the packaged Python surface:

```bash
hive console serve --host 127.0.0.1 --port 8787
```

The packaged product path is `hive console serve`, which serves the same console from the Python install artifact.
`hive dashboard` is only a compatibility alias.

For local frontend checks from this directory:

```bash
pnpm install
pnpm test
pnpm build
```

For the desktop beta scaffold from this same console source tree:

```bash
pnpm run tauri:dev
pnpm run tauri:check
pnpm run tauri:build
```

The Tauri shell keeps the browser-first contract intact. It builds a desktop-specific `/`-based
copy of the same React app, points it at the same local Hive API contract on
`http://127.0.0.1:8787`, and then renders the shared command center inside a native window.
During local development it first tries `uv run hive console api --host 127.0.0.1 --port 8787`
from the repo root, then falls back to `hive console api --host 127.0.0.1 --port 8787`.
If a healthy API is already running, the shell reuses it instead of spawning a second daemon.
On quit it only stops the child process that it started itself.

Current desktop beta affordances:

- tray actions for opening the command center or notifications, pausing/resuming desktop notifications, and quitting gracefully
- native notifications routed from the shared notification model
- deep links through the `agent-hive://` custom scheme
- the same API base and workspace-path controls used by the browser console

Current desktop beta limits:

- browser remains the primary supported path
- no native updater or update-check is wired yet
- no native workspace picker is wired yet; workspace selection still happens through the shared UI controls

The current Tauri capability scope is intentionally small: `core:default` plus
`notification:default` for the `main` window. See [Desktop Beta](../../docs/DESKTOP_BETA.md)
for the operator-facing packaging, permissions, and update-path notes.

The frontend reads two pieces of operator state:

- API base URL, defaulting to `http://127.0.0.1:8787`
- workspace path, passed to the API as `?path=...`

Both are editable in the top bar and persisted in local storage so the console can stay pointed at the same workspace between refreshes.

Routes included in this scaffold:

- `/` — Home
- `/runs` — Runs board
- `/inbox` — Operator inbox
- `/campaigns` — Campaign board
- `/projects` — Project summaries and Program Doctor
- `/search` — Unified search
- `/integrations` — Native and advisory integration surfaces
- `/notifications` — Notification center
- `/activity` — Recent activity feed
- `/settings` — Operator-local preferences and environment controls
- `/runs/:runId` — Run detail

Desktop bootstrap files live under `frontend/console/src-tauri/` so the browser shell and desktop
shell keep sharing one frontend codebase instead of forking the UI.

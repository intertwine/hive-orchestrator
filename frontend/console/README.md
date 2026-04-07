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
```

The Tauri shell keeps the browser-first contract intact. It builds a desktop-specific `/`-based
copy of the same React app, points it at the same local Hive API contract on
`http://127.0.0.1:8787`, and then renders the shared command center inside a native window.
During local development it first tries `uv run hive console api --host 127.0.0.1 --port 8787`
from the repo root, then falls back to `hive console api --host 127.0.0.1 --port 8787`.
Daemon lifecycle, tray actions, native notifications, and desktop deep links land in the
follow-on desktop task rather than this bootstrap slice.

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
- `/runs/:runId` — Run detail

Desktop bootstrap files live under `frontend/console/src-tauri/` so the browser shell and desktop
shell keep sharing one frontend codebase instead of forking the UI.

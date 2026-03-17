# Hive Observe Console

This is the React/Vite frontend for the Hive Observe Console.

It assumes the backend API is already running through the existing Python surface, for example:

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

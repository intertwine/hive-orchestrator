# Hermes Harness Guide

Use Hermes when you want Hermes-native skills, advisory attach, and a truthful trajectory-import fallback when live attach is unavailable.

## Five-minute path

Install or update Hive:

```bash
uv tool install 'mellona-hive[console]'
```

Verify the Hermes integration path:

```bash
hive integrate doctor hermes --json
hive integrate hermes
```

Then load the Agent Hive skill/toolset in Hermes and attach the current session:

```bash
hive integrate attach hermes <session-id>
```

If live attach is unavailable, import the trajectory after the fact:

```bash
hive integrate import-trajectory hermes /path/to/hermes-export.jsonl --project-id <project-id>
```

## Truth

- Hermes is attach/import in v2.4, not managed
- governance is always advisory
- private Hermes memory (`MEMORY.md`, `USER.md`) is never bulk-imported automatically

## If something fails

Run:

```bash
hive integrate doctor hermes --json
```

That will tell you whether Hermes is installed, whether the session store is available, and whether the skill/toolset path is ready.

# Agent Hive — Hermes Skill/Toolset

Native Hermes skill for [Agent Hive](https://github.com/intertwine/hive-orchestrator) v2.4 observe-and-steer orchestration.

## What this includes

- `manifest.json` — skill declaration with 6 action intents
- `actions.py` — Python action implementations wrapping `hive` CLI
- Memory policy documentation (private memory never bulk-imported)

## Install

Copy this skill into your Hermes workspace or load it as a toolset:

```bash
# From the hive-orchestrator repo
cp -r packages/hermes-skill/ ~/.hermes/skills/agent-hive/
```

Or reference it directly:

```bash
hive integrate hermes
```

**Note:** The action wrappers in `actions.py` shell out to the `hive` CLI on PATH.
If running from a repo checkout, use `uv run hive` or ensure the installed `hive`
matches the repo version. From an installed `mellona-hive`, the actions work directly.

## Actions

| Intent | Description | CLI equivalent |
|---|---|---|
| `hive_next` | Next recommended task | `hive next --json` |
| `hive_search` | Search workspace | `hive search <query> --json` |
| `hive_attach` | Attach session to Hive | `hive integrate attach hermes <id>` |
| `hive_finish` | Finish/escalate task | `hive finish <run-id>` |
| `hive_note` | Post steering note | `hive steer note <run-id>` |
| `hive_status` | Workspace/run status | `hive console home --json` |

## Memory policy

Hermes private memory (`MEMORY.md`, `USER.md`) is **never** bulk-imported into Hive. Only:
- Project-relevant summary snippets
- Explicitly operator-approved procedures
- Normalized trajectories and artifacts
- Notes marked as exportable

## Trajectory import fallback

If a Hermes session wasn't live-attached, export its trajectory and import after the fact:

```bash
hive integrate import-trajectory hermes /path/to/hermes-export.jsonl --project-id <id>
```

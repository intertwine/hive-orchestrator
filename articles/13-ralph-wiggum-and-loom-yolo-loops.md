# Ralph Wiggum and Loom YOLO Loops

_A practical guide to running Agent Hive in continuous, opt-in dispatch loops across models, agents, repos, and MCP-connected integrations._

## Why YOLO loops exist

Agent Hive already knows how to find ready work, assemble context, and dispatch it. A YOLO loop makes that capability continuous. Instead of a single dispatch run, the dispatcher keeps cycling, looking for new ready tasks and routing them to whichever agent is configured for that project.

These loops are **opt-in** because they can run forever. They’re designed for long-running, largely unmonitored coordination when you want the hive to keep moving.

## Two styles: Ralph Wiggum vs. Loom

Both styles use the same dispatcher. The difference is in how they idle between cycles.

### Ralph Wiggum style

The Ralph Wiggum loop is intentionally aggressive. It runs on a short, fixed sleep interval and does not back off when there’s no work. It keeps checking. It keeps dispatching. It’s the “I’m in danger” setting for teams that want maximum throughput and accept the risk of constant activity.

### Loom style

The Loom loop is a weaving pattern. It does the same work, but it backs off when the hive is idle. No work found? It sleeps longer. Work found? It resets to the base sleep interval. This makes it more stable for long-running, unattended loops.

## How to enable YOLO loops (CLI)

The dispatcher stays single-run by default. YOLO loops are explicit.

```bash
# Loom style (default style for YOLO mode)
python -m src.agent_dispatcher --yolo-loop --yolo-style loom

# Ralph Wiggum style (aggressive, fixed cadence)
python -m src.agent_dispatcher --yolo-loop --yolo-style ralph-wiggum --loop-sleep 5

# Cap a loop to N cycles (useful for testing)
python -m src.agent_dispatcher --yolo-loop --loop-max-cycles 25
```

## Dispatch profiles: choose agents, models, and integrations

A YOLO loop is only useful if it can route to multiple agents and integrations. Agent Hive now supports a lightweight dispatch profile in your `AGENCY.md` metadata. This lets each project opt into a specific agent name, mention handle, and routing labels.

```yaml
---
project_id: search-ops
status: active
priority: high
owner: null

dispatch:
  agent_name: gpt-5-search
  mention: "@opencode"
  labels:
    - model:gpt-5
    - integration:mcp
    - skill:web-search
---
```

**What this does:**
- **agent_name** becomes the project owner on claim.
- **mention** is used in the issue body and follow-up comment to notify the right agent.
- **labels** help external automations or skills know which integrations to attach.

That means a single hive can route:
- **Across models**: claude, gpt-5, gemini, or local models.
- **Across agents**: Claude Code, OpenCode agents, or custom runners.
- **Across repos**: local hive projects or `target_repo` workflows.
- **Across integrations**: MCP servers and skills that subscribe to labels.

## Multi-agent routing in practice

You can still force a default agent on the CLI when you want a single loop runner to handle everything:

```bash
python -m src.agent_dispatcher \
  --yolo-loop \
  --agent-name claude-sonnet-4 \
  --agent-mention @claude \
  --extra-label model:claude-sonnet-4
```

But the real power shows up when different projects declare different dispatch profiles. A single loop can rotate across all of them without manual handoffs.

## Safety notes for infinite loops

YOLO loops are powerful. They’re also easy to let run forever. Best practices:

- Start with Loom style when running unattended.
- Set `loop-max-cycles` for early testing.
- Use labels to drive skills and MCP routing instead of hard-coding behavior.
- Monitor GitHub issue throughput or add tracing if you need auditability.

## Running unattended without GitHub Actions

If you want YOLO loops outside GitHub Actions, run them from a local machine, a VM, or a cloud sandbox. The dispatcher writes a heartbeat JSON file every cycle when you pass `--loop-heartbeat`, which makes it easy to add monitoring or watchdogs.

The repository includes helper scripts for background runs:

```bash
export HIVE_BASE_PATH=/path/to/hive-orchestrator
export YOLO_STYLE=loom
export SLEEP_SECONDS=30
export AGENT_NAME=claude-sonnet-4
export AGENT_MENTION=@claude

scripts/run_yolo_loop.sh
```

For systemd, container, and VM examples, see `docs/yolo-loop-unattended.md`.

## Summary

Ralph Wiggum loops give you speed. Loom loops give you stability. Both are opt-in, both work across models and agents, and both keep the hive moving without manual babysitting.

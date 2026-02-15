# Ralph Wiggum and Loom YOLO Loops

_A practical guide to running Agent Hive in continuous, opt-in dispatch loops across models, agents, repos, and MCP-connected integrations._

## Why YOLO loops exist

Agent Hive already knows how to find ready work, assemble context, and dispatch it. A YOLO loop keeps that capability running. Instead of a single dispatch run, the dispatcher cycles continuously, looking for new ready tasks and routing them to the right agent.

YOLO loops are opt-in because they can run forever. They’re meant for long-running coordination when you want the hive to keep moving without a human watching every cycle.

## Two styles: Ralph Wiggum vs. Loom

Both styles use the same dispatcher. The difference is how they idle between cycles.

### Ralph Wiggum style

The Ralph Wiggum loop is aggressive. It uses a short, fixed sleep interval and does not back off when there’s no work. It keeps checking. It keeps dispatching. It’s the “I’m in danger” setting for teams that want maximum throughput and accept constant activity.

### Loom style

The Loom loop weaves in backoff. If the hive is idle, the sleep interval grows. When work appears, it resets to the base sleep time. This is the safer default for long-running, unattended loops.

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

A YOLO loop only helps if it can route to multiple agents and integrations. Agent Hive supports a lightweight dispatch profile in `AGENCY.md` metadata. Each project can declare its agent name, mention handle, and routing labels.

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

That lets a single hive route work:
- **Across models**: Claude, GPT-5, Gemini, or local models.
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

The real power shows up when different projects declare different dispatch profiles. One loop can rotate across all of them without manual handoffs.

## Safety notes for infinite loops

YOLO loops are powerful. They’re also easy to let run forever. Best practices:

- Start with Loom style when running unattended.
- Set `loop-max-cycles` for early testing.
- Use labels to drive skills and MCP routing instead of hard-coding behavior.
- Monitor GitHub issue throughput or add tracing when you need auditability.

## Running unattended without GitHub Actions

If you want YOLO loops outside GitHub Actions, run them from a local machine, a VM, or a cloud sandbox. The dispatcher can write a heartbeat JSON file every cycle with `--loop-heartbeat`, which makes monitoring straightforward.

The repo includes helper scripts for background runs:

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

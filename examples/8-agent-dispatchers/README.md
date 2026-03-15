# Agent Dispatchers

Use this pattern when you want to route ready Hive work into another interface such as GitHub issues, Slack, MCP clients, or your own queue.

## The Launch-Ready Contract

A dispatcher should do four things:

1. find ready work
2. build context
3. hand the work to an agent surface
4. claim the chosen task lease

The core inputs are:

```bash
hive task ready --json
hive context startup --project <project-id> --task <task-id> --json
hive task claim <task-id> --owner <dispatcher-or-agent> --json
```

## Optional Companion Surfaces

- `hive search` for fast workspace lookup
- the thin MCP `search` and `execute` tools for agent hosts that prefer MCP
- `src/agent_dispatcher.py` as the built-in GitHub issue adapter

## Rules For Custom Dispatchers

- do not mutate `AGENCY.md` directly to claim work
- do not invent your own ready queue when `hive task ready` already exists
- do not skip `PROGRAM.md` when the dispatched work can trigger evaluators or command execution

## Minimal Adapter Outline

1. call `hive task ready --json`
2. pick a task
3. call `hive context startup --project ... --task ... --json`
4. deliver that payload to your target system
5. call `hive task claim ... --json`
6. sync projections after any durable state change

This keeps the dispatcher thin and keeps Hive in charge of state.

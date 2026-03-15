# Hive 2.0 Agent Interface Guide

Status: Proposed  
Audience: Codex and harness integrators

## Positioning

Hive 2.0 is not itself a terminal coding harness. It is a project orchestration layer. That means:

- Codex / Claude Code / OpenCode / Pi / Hermes remain the interactive shells
- Hive provides durable project state, memory, run contracts, and automation workflows
- agents should reach for the Hive CLI first

## Default integration rule

**Use direct CLI before any MCP or Code Mode wrapper.**

Why:

1. the CLI is the most portable path across harnesses
2. shell-based harnesses already know how to run commands
3. CLI output can be versioned and tested as stable JSON
4. direct shell commands avoid recreating tool bloat inside MCP

## CLI-first workflow

Recommended loop for an agent:

```bash
# 1. discover context
hive project list --json
hive context startup --project <project-id> --json

# 2. find work
hive task ready --project <project-id> --json

# 3. claim work
hive task claim <task-id> --owner codex --ttl-minutes 30 --json

# 4. start a run
hive run start <task-id> --json

# 5. inspect the project contract
cat projects/<slug>/PROGRAM.md

# 6. do the coding work in the harness/worktree

# 7. evaluate
hive run eval <run-id> --json

# 8. accept or escalate
hive run accept <run-id> --json
# or
hive run escalate <run-id> --json
```

## Why a thin Code Mode adapter still matters

A Code Mode style adapter is useful when:
- the agent needs to compose multiple Hive calls
- the harness prefers an API over repeated shell commands
- we want to avoid an MCP surface with many tools

The adapter exists for **composition**, not for replacing the CLI.

## Proposed Code Mode surface

Exactly two tools:

### `search`
Search:
- command docs
- JSON schemas
- typed client docs
- examples
- current workspace graph summaries
- memory/query docs

### `execute`
Execute JS/TS or Python against a typed local Hive client with:
- timeout
- environment scrubbing
- bounded working directory
- best-effort network denial

## Typed client shape

Inside `execute`, expose:

```ts
type HiveClient = {
  project: {
    list(input?: { status?: string[] }): Promise<any>,
    show(input: { id: string }): Promise<any>,
  },
  task: {
    list(input?: { projectId?: string, status?: string[] }): Promise<any>,
    ready(input?: { projectId?: string, limit?: number }): Promise<any>,
    show(input: { id: string }): Promise<any>,
    claim(input: { id: string, owner: string, ttlMinutes?: number }): Promise<any>,
    release(input: { id: string, owner?: string }): Promise<any>,
    update(input: { id: string, patch: Record<string, unknown> }): Promise<any>,
    link(input: { srcId: string, edgeType: string, dstId: string }): Promise<any>,
  },
  run: {
    start(input: { taskId: string }): Promise<any>,
    show(input: { id: string }): Promise<any>,
    eval(input: { id: string }): Promise<any>,
    accept(input: { id: string }): Promise<any>,
    reject(input: { id: string, reason?: string }): Promise<any>,
    escalate(input: { id: string, reason?: string }): Promise<any>,
  },
  memory: {
    search(input: { query: string, scope?: string }): Promise<any>,
    observe(input?: { transcriptPath?: string }): Promise<any>,
    reflect(input?: { scope?: string }): Promise<any>,
  },
  context: {
    startup(input: { projectId: string, profile?: 'light' | 'default' | 'deep' }): Promise<any>,
    handoff(input: { projectId: string }): Promise<any>,
  },
  scheduler: {
    next(input?: { projectId?: string }): Promise<any>,
  }
};
```

## When to use direct CLI vs Code Mode

### Use direct CLI when:
- one or two calls are enough
- the harness already has shell access
- debugging or observability matters
- you want exact reproducibility from shell history

### Use Code Mode when:
- you need to search the Hive API first
- you need to compose multiple Hive operations in one turn
- the harness only accepts a small tool surface
- you want a typed client rather than repeated shell parsing

## Thin MCP wrapper

If an MCP server is required, it SHOULD expose only:

- `search`
- `execute`

Everything else is done inside `execute` against the typed client. Do not expose `task_list`, `task_show`, `task_ready`, `task_claim`, `run_start`, `run_eval`, etc. as separate MCP tools unless a specific harness makes that unavoidable.

## Harness-specific notes

### Codex CLI
- default path: CLI + `AGENTS.md`
- optional: use Code Mode adapter if Codex benefits from it
- transcript ingestion can be file polling or explicit `hive memory observe`

### Claude Code
- default path: CLI + SessionStart/SessionEnd hooks
- SessionStart calls `hive context startup`
- SessionEnd calls `hive memory observe`

### OpenCode
- default path: same CLI + skills
- optional thin MCP wrapper is acceptable

### Pi
- keep it simple
- rely on shell + `AGENTS.md`
- no need to force MCP
- let Hive own persistent tasks and plans

### Hermes
- use `AGENTS.md`
- load skills on demand
- cron can trigger reflection or scheduler ticks
- avoid duplicating Hive’s task model inside Hermes-native todos

## Recommended skill set

### `hive-core.md`
- what Hive owns
- CLI-first rules
- generated-section warnings

### `hive-runner.md`
- how to start/evaluate/promote runs
- how to read `PROGRAM.md`

### `hive-memory.md`
- when to use `hive memory search`
- when to trigger observe / reflect

### `hive-codemode.md`
- how to use `search` then `execute`
- when not to use it

## Safety / correctness rules for agents

1. Do not mark a task done without evaluator results.
2. Do not manually edit generated sections unless explicitly told.
3. Do not assume claims are permanent.
4. Do not bypass `PROGRAM.md` path or command restrictions.
5. Do not write secrets into memory files or run summaries.
6. Prefer updating task files or CLI calls over ad hoc notes in random markdown files.

## Practical recommendation

For the first release, implement:
- direct CLI integration
- `AGENTS.md` shim
- one or two harness hook adapters
- optional Code Mode adapter behind a feature flag

That gives the team the Cloudflare-style small-surface pattern without making Hive depend on MCP.

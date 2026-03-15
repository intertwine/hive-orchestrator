---
name: multi-agent-coordination
description: Coordinate work between multiple agents in Hive v2. Use this skill when several agents need to split work, hand off tasks, manage blockers, or add optional real-time coordination.
---

# Multi-Agent Coordination

In Hive v2, agents coordinate on canonical tasks and governed runs.

Primary tools:

- `hive task ready --json`
- `hive task claim ... --json`
- `hive task release ... --json`
- `hive task link ... blocked_by ... --json`
- `hive deps --json`
- `hive context startup --project <project-id> --task <task-id> --json`

## Core Rules

- Coordinate on task ids, not prose.
- Use task claims for leases.
- Use task links for blockers.
- Use `PROGRAM.md` when work needs evaluator or command policy.
- Treat `AGENCY.md` as narrative context, not a lock file.

## Coordination Patterns

### Sequential handoff

Use this when one task should unlock another.

```bash
hive task link <implement-task> blocked_by <research-task> --json
```

Flow:

1. Agent A claims the first task
2. Agent A finishes and releases it
3. Agent B sees the next task enter the ready queue
4. Agent B claims and continues

### Parallel independent work

Use this when several tasks can run at the same time.

```bash
hive task ready --project-id <project-id> --json
```

Have each agent claim a different task id. Avoid overlapping file ownership when possible.

### Review loop

Use a run when the work needs evaluator gates:

```bash
hive run start <task-id> --json
hive run eval <run-id> --json
```

One agent can implement, another can review the run artifacts, and a human can accept or escalate.

## Checking Coordination State

Ready queue:

```bash
hive task ready --json
```

Project blocker summary:

```bash
hive deps --json
```

Focused startup bundle for one task:

```bash
hive context startup --project <project-id> --task <task-id> --json
```

## Optional Real-Time Coordinator

The FastAPI coordinator is an extra layer for distributed or highly parallel sessions. Use it as a live lock service, not as the source of truth.

Guidelines:

- keep canonical state in `.hive/`
- keep coordinator auth enabled outside local development
- use it when you need fast conflict prevention across many shells or machines

## Common Mistakes

- flipping `owner` in `AGENCY.md` instead of claiming the task
- using checkbox text as the dependency graph
- skipping `PROGRAM.md` when runs or evaluators are involved
- leaving long-lived claims around after the task is done
- **@agent-name** - Direct mention for specific agent
- **BLOCKED** - Prefix for blocking issues
- **TODO** - Items for next agent
- **DECISION** - Record important choices

## Best Practices

1. **Always check ownership first** - Never override another agent
2. **Use coordinator for speed** - Faster than git-only coordination
3. **Keep notes detailed** - Other agents depend on your documentation
4. **Release promptly** - Don't hold claims unnecessarily
5. **Manage dependencies** - Keep `blocked_by`/`blocks` accurate
6. **Plan handoffs** - Document what's done and what's next
7. **Respect the protocol** - Coordination only works if everyone follows it

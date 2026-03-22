---
name: hive-coordination
description: Coordinate work across multiple agents and projects in Hive. Covers task claims, blockers, handoffs, campaigns, portfolio management, briefs, and shared memory.
---

# Hive Coordination

This skill covers how agents work together and how work is orchestrated across projects.

## Multi-Agent Task Coordination

Agents coordinate on canonical task state in `.hive/tasks/*.md`, not on prose or checkboxes.

### Core tools

```bash
hive task ready --json                                      # what is available
hive task claim <id> --owner <name> --ttl-minutes 30 --json # take a lease
hive task release <id> --json                               # give it back
hive task link <src> blocked_by <dst> --json                # declare dependency
hive deps --json                                            # blocker summary
hive context startup --project <id> --task <id> --json      # build context for one task
```

### Pattern: Sequential Handoff

When one task should unlock another:

```bash
hive task link <implement-task> blocked_by <research-task> --json
```

1. Agent A claims and completes the research task
2. Agent A releases it, marks it done
3. The implement task enters the ready queue automatically
4. Agent B claims and continues

### Pattern: Parallel Independent Work

When several tasks can run simultaneously:

```bash
hive task ready --project-id <project-id> --json
```

Each agent claims a different task. Avoid overlapping file ownership when possible.

### Pattern: Review Loop

When work needs evaluator gates:

```bash
hive run start <task-id> --json         # agent implements
hive run eval <run-id> --json           # evaluator checks
hive run accept <run-id> --json         # reviewer approves
```

One agent implements, another reviews artifacts, a human accepts or escalates.

### Common Mistakes

- Flipping `owner` in AGENCY.md instead of using `hive task claim`
- Using checkbox text as the dependency graph instead of task links
- Skipping PROGRAM.md when runs or evaluators are involved
- Leaving long-lived claims after the work is done

## Campaigns

Campaigns orchestrate multiple tasks across a project with scheduling and lane-based allocation.

### Create a campaign

```bash
hive campaign create --title "Sprint 1" --goal "Ship MVP features" \
  --project-id <id> --type delivery --driver local --cadence daily --json
```

### Monitor campaigns

```bash
hive campaign list --json                       # all active campaigns
hive campaign list --project-id <id> --json     # scoped to project
hive campaign status <campaign-id> --json       # health, runs, lane allocations
```

### Tick a campaign

```bash
hive campaign tick <campaign-id> --json
```

A campaign tick executes one cycle: recommend tasks → start runs → review results.

### Campaign lanes

Each campaign allocates work across four lanes:

| Lane | Purpose |
|------|---------|
| `exploit` | Production delivery (default) |
| `explore` | Research and experimentation |
| `review` | Evaluation queue management |
| `maintenance` | Technical debt and ops |

Lane quotas are configurable per campaign.

## Portfolio Management

Portfolio commands operate across all projects in the workspace.

### Portfolio status

```bash
hive portfolio status --json
```

Returns all projects, ready tasks, active runs, and the evaluation queue.

### Steer a project

```bash
hive portfolio steer <project-id> --pause --json          # pause project
hive portfolio steer <project-id> --resume --json         # resume project
hive portfolio steer <project-id> --focus-task <id> --json  # focus on one task
hive portfolio steer <project-id> --boost 2 --json        # priority boost
hive portfolio steer <project-id> --force-review --json   # force review cycle
```

### Portfolio tick

```bash
hive portfolio tick --json                      # full state machine tick
hive portfolio tick --mode recommend --json     # recommendation phase only
hive portfolio tick --mode start --json         # launch phase only
hive portfolio tick --mode review --json        # review phase only
hive portfolio tick --mode cleanup --json       # cleanup phase only
```

## Briefs

Generate executive summaries of portfolio activity:

```bash
hive brief daily --json     # daily summary of changes
hive brief weekly --json    # weekly portfolio summary
```

## Shared Memory

Memory lets agents persist and share knowledge across sessions.

### Record observations

```bash
hive memory observe --note "..." --scope project --project <id> --json
hive memory observe --transcript-path <file> --scope global --json
```

### Generate reflections

```bash
hive memory reflect --scope project --project <id> --propose --json
```

Reflections are review-gated. A human must approve before they become canonical:

```bash
hive memory accept --scope project --project <id> --json
hive memory reject --scope project --project <id> --json
```

### Search memory

```bash
hive memory search "query text" --scope all --limit 8 --json
hive memory search "query text" --scope project --json
```

Memory scopes: `project` (per-project knowledge), `global` (workspace-level knowledge), `all`.

## Rules of Thumb

- Coordinate on task IDs, not prose.
- Use task claims for leases and task links for blockers.
- Treat AGENCY.md as narrative context, not a lock file.
- Refresh projections after coordination changes: `hive sync projections --json`.
- Campaign ticks respect lane quotas and budget policies — do not bypass them.
- Memory reflections require human approval. Do not assume proposed reflections are canonical.

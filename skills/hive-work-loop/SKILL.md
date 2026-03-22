---
name: hive-work-loop
description: The core agent work cycle in Hive — from finding a task through claiming, launching a run, handling approvals, finishing, and promoting. Use this skill for task-first project work, governed runs, and clean handoff.
---

# Hive Work Loop

This is the core cycle for getting work done in Hive. It covers the full path from finding a task to promoting the result.

## The Loop

```
find ready work → build context → claim → launch run → monitor
    → handle approvals → finish → evaluate → promote → release
```

## 1. Find Ready Work

```bash
hive next --json                                    # recommended next task
hive task ready --json                              # full ready queue
hive task ready --project-id <project-id> --json    # scoped to one project
```

`hive next` returns the highest-priority unblocked task. It respects dependency constraints and expired claims.

If the queue is empty, check why:

```bash
hive deps --json          # shows blockers
hive task list --json     # shows all tasks regardless of status
```

## 2. Build Context

```bash
hive context startup --project <project-id> --task <task-id> --json
```

This compiles a startup bundle: task description, acceptance criteria, project mission, API docs, code examples, dependency snapshot, and previous notes.

For a saved markdown bundle (from a repo checkout):

```bash
make session PROJECT=<project-id>
```

## 3. Claim the Task

```bash
hive task claim <task-id> --owner <your-name> --ttl-minutes 30 --json
```

Claims are time-limited leases. Other agents can see who holds what. Always claim before starting work so you do not collide.

Read PROGRAM.md before proceeding with autonomous work:

```bash
cat projects/<project-id>/PROGRAM.md
```

## 4. Launch a Run

For governed execution (recommended):

```bash
hive work <task-id> --owner <your-name> --json
```

`hive work` does several things:
- Creates a git worktree with an isolated branch
- Compiles startup context
- Checkpoints workspace state
- Launches the driver
- Emits a run record

For more control over driver and model:

```bash
hive work <task-id> --owner <your-name> --driver codex --model gpt-4 --json
```

For batch mode (no interactive follow-up):

```bash
hive run start <task-id> --driver local --json
```

## 5. Monitor the Run

```bash
hive run status <run-id> --json       # driver progress, health, phase, budget
hive run show <run-id> --json         # full run metadata
hive run artifacts <run-id> --json    # list output artifacts (patch, transcript, eval)
```

Run states flow through: `queued` → `compiling_context` → `launching` → `running` → `awaiting_input` → `completed_candidate` → `accepted`/`rejected`/`escalated`.

## 6. Handle Approvals and Steering

Drivers may request approval for sensitive operations. When a run enters `awaiting_input`:

```bash
hive steer approve <run-id> --json                        # approve pending request
hive steer approve <run-id> --approval-id <id> --json     # approve specific request
hive steer reject <run-id> --approval-id <id> --reason "..." --json
```

Other steering commands:

```bash
hive steer pause <run-id> --reason "..." --json     # pause active run
hive steer resume <run-id> --json                   # resume paused run
hive steer cancel <run-id> --reason "..." --json    # cancel run immediately
hive steer note <run-id> --message "..." --json     # add steering note to event stream
hive steer reroute <run-id> --driver claude --json  # transfer to different driver
```

A human may also steer through the console. Watch for state changes.

## 7. Finish and Evaluate

```bash
hive finish <run-id> --json
```

`hive finish` consults the evaluator policy from PROGRAM.md. Depending on the result:

- **Accepted:** Task can be promoted and closed.
- **Rejected:** Task returns to the ready queue. Fix and re-run.
- **Escalated:** Needs human review. Run enters `awaiting_review`.

For manual evaluation control:

```bash
hive run eval <run-id> --json                               # run evaluator
hive run accept <run-id> --json                             # manually accept
hive run reject <run-id> --reason "tests failed" --json     # manually reject
hive run escalate <run-id> --reason "needs human" --json    # escalate to human
```

## 8. Promote to Main

After acceptance, merge the worktree branch back:

```bash
hive run promote <run-id> --cleanup-worktree --json
```

This merges the run's branch into the current branch and cleans up the git worktree.

## 9. Clean Up and Release

```bash
hive task update <task-id> --status done --json     # mark task complete
hive task release <task-id> --json                  # release claim
hive sync projections --json                        # refresh generated docs
hive run cleanup --terminal --json                  # clean up all finished runs
```

## Record What You Learned

If the work produced durable knowledge:

```bash
hive memory observe --note "..." --scope project --project <project-id> --json
```

For longer transcripts:

```bash
hive memory observe --transcript-path <file> --scope project --project <project-id> --json
```

## Handoff to Another Agent

```bash
hive context handoff --project <project-id> --json
```

This compiles a handoff bundle with current state, open work, and context for the next agent.

## Quick Reference

| Step | Command |
|------|---------|
| Find work | `hive next --json` |
| Build context | `hive context startup --project <id> --task <id> --json` |
| Claim | `hive task claim <id> --owner <name> --ttl-minutes 30 --json` |
| Launch | `hive work <id> --owner <name> --json` |
| Monitor | `hive run status <run-id> --json` |
| Approve | `hive steer approve <run-id> --json` |
| Finish | `hive finish <run-id> --json` |
| Promote | `hive run promote <run-id> --cleanup-worktree --json` |
| Release | `hive task release <id> --json` |
| Handoff | `hive context handoff --project <id> --json` |

## Rules of Thumb

- Start from canonical task state (`hive task ready`), not from old docs or checklists.
- Claim early so other agents see the lease.
- Read PROGRAM.md before autonomous work or evaluator runs.
- If you are blocked, record it in the task or escalate through the run lifecycle — do not hide it in prose.
- Leave the task and projections in a better state than you found them.
- When a run is rejected, read the eval results before re-running. Fix the cause, do not retry blindly.

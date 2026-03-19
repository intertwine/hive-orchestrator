---
name: deep-work-session
description: Enter and manage focused Hive v2 task sessions. Use this skill for task-first project work, startup context, claims, and clean handoff in normal Hive usage. Do not use it as the primary guide for long-running v2.3 maintainer work, PR-driven implementation, or review-heavy merge trains in this repo; use `hive-v23-execution-discipline` for those.
---

# Deep Work Session

This skill is for task-lease-oriented Hive work.

If you are working inside this repository on v2.3, RFC implementation, review debt, merge trains, or other maintainer-heavy work, follow `.agents/skills/hive-v23-execution-discipline/SKILL.md` first and only borrow the task/claim parts from here when they help.

Hive v2 deep work is task-first:

1. find ready work
2. build startup context
3. claim a task lease
4. do the work
5. sync projections and hand off cleanly

## Start a Session

Find work:

```bash
hive task ready --json
```

Build context:

```bash
hive context startup --project <project-id> --json
```

If you want a saved markdown bundle instead of raw JSON:

```bash
make session PROJECT=<project-id>
```

`PROJECT` can be a project id like `demo` or a path like `projects/demo`.

## Claim the Work

```bash
hive task claim <task-id> --owner codex --ttl-minutes 30 --json
```

Use task claims, not hand-edited `owner` fields in `AGENCY.md`.

## During the Session

- Read `PROGRAM.md` before running evaluators or broad autonomous commands.
- Use `hive search` if you need workspace context fast.
- Use `hive memory observe` and `hive memory reflect` when the project benefits from durable notes.
- Keep task state current with `hive task update`.

Example:

```bash
hive task update <task-id> --status in_progress --json
```

## If the Work Uses Governed Runs

```bash
hive run start <task-id> --json
hive run eval <run-id> --json
hive run accept <run-id> --json
```

Reject or escalate when the evaluator or policy says you should:

```bash
hive run reject <run-id> --reason "tests failed" --json
hive run escalate <run-id> --reason "needs human decision" --json
```

## End the Session Cleanly

Before you stop:

1. update the task status
2. sync projections
3. release the task if you are handing it off
4. build handoff context if another agent is continuing

Commands:

```bash
hive task release <task-id> --json
hive sync projections --json
hive context handoff --project <project-id> --json
```

## Rules of Thumb

- Start from canonical task state, not from old checklist docs.
- Claim early so other agents see the lease.
- Leave the task and projections in a better state than you found them.
- If you are blocked, record it in the task or escalate through the run lifecycle instead of hiding it in prose.

# Multi-Agent Coordination Without Chaos

_Parallel work is easy to imagine and hard to keep clean._

---

![Hero: The Promise vs Reality](images/multi-agent-coordination-without-chaos/img-01_v1.png)
_The hard part is not getting multiple agents to work. The hard part is getting them to share a project without corrupting state or tripping over each other._

---

## The Real Coordination Problems

When multiple agents touch related work, the failure modes are predictable:

- two agents take the same task
- downstream work starts before blockers are done
- somebody marks something "done" when it is only locally done
- important decisions never make it into durable state

None of that requires malicious behavior. It is what happens when coordination is implied instead of encoded.

## Hive's Coordination Model

Hive v2 coordinates through explicit state, not through hope.

The main ingredients are:

- canonical task files
- explicit edge types such as `blocks`
- task claims with expiry
- ready queue calculation
- project policy in `PROGRAM.md`
- runs with artifacts and acceptance states

This gives you a coordination loop that does not depend on everybody sharing the same live conversation.

## Claims Are The First Guardrail

If work is worth doing, it is worth claiming:

```bash
hive task claim task_ABC --owner claude-code --ttl-minutes 60 --json
```

That does two useful things:

- it makes ownership visible
- it prevents abandoned claims from blocking work forever

Expiry matters more than people think. Coordination systems rot when a dead session can strand useful work for days.

## Ready Work Should Be Computed, Not Guessed

Hive computes ready work from canonical state:

```bash
hive task ready --json
```

That result already accounts for:

- blockers
- superseded or duplicate tasks
- project scoping
- expired claims

This is much stronger than "look around and see what seems free."

## Dependency Edges Beat Social Conventions

A lot of multi-agent chaos comes from unwritten assumptions:

- "I thought you were waiting on me"
- "I did not realize that task unlocked yours"
- "I assumed that checklist item meant the whole thing was finished"

Hive is better when those relationships are explicit:

```bash
hive task link task_design blocks task_impl --json
```

Once the dependency is encoded, the scheduler and reviewers have something concrete to reason about.

## Runs Add A Second Layer Of Coordination

Claims tell you who is working.
Runs tell you what happened.

For governed work, that matters:

```bash
hive run start task_impl --json
hive run eval run_ABC --json
hive run accept run_ABC --json
```

Now the handoff is not just "trust me, I finished it."

It can include:

- plan
- patch
- summary
- command log
- evaluator result
- accept / reject / escalate decision

That is the difference between informal coordination and a real review loop.

## Human Oversight Is Part Of The Design

Hive is not trying to remove the human from the system.

It is trying to make human intervention cheaper and better timed.

Humans step in to:

- review sensitive changes
- resolve blocked tasks
- adjust policy
- accept or reject runs
- rewrite project narrative when reality changes

That is not a fallback path. It is part of the architecture.

## What Makes Hive Work Across Different Harnesses

Claude Code, OpenCode, Codex, and other harnesses can all behave differently in practice.

Hive absorbs some of that variation because the coordination surface is outside the harness:

- claim through Hive
- build context through Hive
- record work through Hive
- sync projections through Hive

That keeps the shared operating model stable even when the interactive shell changes.

## The Habit That Matters Most

The single best coordination habit is simple:

do not leave important state trapped in a session.

Put it in:

- a canonical task update
- an accepted or rejected run
- memory
- `AGENCY.md`
- projection sync

Multi-agent systems stay sane when the next person can read what matters without replaying the whole session in their head.

## Bottom Line

Hive does not solve multi-agent coordination with a magic conversation loop.

It solves it with explicit claims, explicit dependencies, explicit policy, and explicit artifacts.

That sounds less glamorous than the usual demo. It also scales better once multiple agents and reviewers are touching the same real codebase.

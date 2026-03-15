# Beads and Agent Hive: Two Approaches to Agent Memory

_Two systems trying to solve the same core problem with different instincts._

---

## The Shared Problem

Both beads and Hive start from the same uncomfortable truth:

agents forget, projects do not, and transcripts are a poor substitute for durable state.

That is the real common ground.

The difference is not whether memory matters. The difference is what kind of system you build around it.

## The Beads Instinct

Beads leans toward a more database-shaped, runtime-shaped memory model.

That style buys you:

- fast structured queries
- daemon-friendly operation
- a system that feels closer to an application backend

If you want something that behaves more like an always-on memory service, that instinct makes sense.

## The Hive Instinct

Hive makes a different tradeoff.

It treats memory as one part of a larger repo-native orchestration system:

- canonical task files in `.hive/`
- readable project documents in Markdown
- run artifacts in Git
- policy in `PROGRAM.md`
- CLI-first workflows across different harnesses

Hive wants the coordination system to stay understandable to both machines and humans without requiring a separate service to be running all the time.

## The Real Difference

The easiest way to describe the difference is this:

- beads feels closer to a memory service
- Hive feels closer to an operating system for long-horizon agent work

That single shift changes a lot.

Hive cares not just about recall, but about:

- ready queues
- claims
- governed runs
- evaluator policy
- projection sync
- reviewable artifacts

Memory is part of the picture, not the whole picture.

## Why Hive Keeps Files In The Loop

File-first systems are easy to underestimate.

They do not look flashy. They do not feel like a hosted control plane. They can look almost too simple.

But the benefits are real:

- people can inspect the state with normal tools
- Git history stays meaningful
- recovery is easier when cache is derived rather than authoritative
- the same workspace can survive model and harness churn

That is a strong fit for teams that value reviewability and operational clarity more than maximum centralization.

## Where Hive Borrowed The Lesson

The lesson Hive clearly shares with beads is that durable memory must be designed, not implied.

That shows up in Hive's:

- project-local memory files
- reflection flow
- startup context assembly
- search surface
- accepted run summaries folded back into context

Those are not incidental extras. They are the connective tissue that makes multi-session work hold together.

## Where Hive Stops Short On Purpose

Hive does not try to turn the whole system into a single memory database.

It keeps:

- task state explicit
- policy explicit
- project narrative separate
- cache rebuildable

That separation makes the system less magical, but easier to trust.

## When Hive Is The Better Fit

Hive is usually the better choice when you want:

- repo-native orchestration
- human-readable project docs
- explicit task claims and ready work
- governed runs with artifacts
- a harness-agnostic CLI surface

If memory is only one part of a broader coordination system, Hive fits naturally.

## When A Beads-Like Approach Is Attractive

A more database-centered approach can be appealing when you want:

- centralized query-heavy memory behavior
- service-like operation
- fewer visible files
- a system that feels more like application infrastructure than repo workflow

Those are real benefits. They just optimize for a different center of gravity.

## Bottom Line

Beads and Hive are not enemies. They are two answers to the same question.

Beads asks, "How should durable agent memory behave?"  
Hive asks, "What would a full long-horizon agent operating system look like if memory were built in from the start?"

That difference is why the systems rhyme without collapsing into the same design.

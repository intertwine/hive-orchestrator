# Skills and Protocols: Teaching Agents to Work in Agent Hive

_Good agent systems do not just store state. They teach contributors how to behave around that state._

---

## Why This Matters

Two agents can have access to the same files and still create completely different outcomes.

One makes careful updates, respects policy, and leaves a clean handoff.
The other improvises, edits the wrong source of truth, and leaves no trail.

The difference is usually not raw model quality.
It is whether the system has clear protocol.

## Skills Are The Teaching Layer

Hive uses skills to teach harnesses how to work with the system.

A good skill answers questions like:

- what files matter here
- what command should I run first
- what should I update when I am done
- what counts as blocked
- what is canonical and what is just a projection

That sounds simple, but it is the difference between "the agent has access" and "the agent can work responsibly."

## Protocol Beats Vibes

The Hive protocol is straightforward:

1. inspect ready work
2. claim a task
3. build startup context
4. read `PROGRAM.md`
5. do the work
6. update canonical state
7. sync projections
8. leave a useful handoff

If a harness follows that loop, it behaves like a good Hive citizen even if it comes from a different vendor.

## What Skills Need To Teach In Hive v2

The most important lessons in v2 are different from v1.

Skills should now teach agents that:

- `.hive/tasks/*.md` is the canonical task store
- `AGENCY.md` is a narrative project document, not the machine database
- `PROGRAM.md` is mandatory reading before autonomous work
- `hive context startup` is the normal way to begin a session
- `hive sync projections` is how human-facing docs stay fresh

That shift is subtle, but it is one of the biggest architectural improvements in Hive v2.

## A Minimal Daily Loop

The best everyday skills point agents toward a short, repeatable loop:

```bash
hive task ready --json
hive task claim task_ABC --owner claude-code --json
hive context startup --project demo --task task_ABC --json
```

Then, after work:

```bash
hive task update task_ABC --status review --json
hive sync projections --json
```

There is no reason to make this more mysterious than it is.

## Protocol Makes Multi-Harness Work Possible

Claude Code, OpenCode, Codex, and other harnesses all have different personalities.

Skills are how you normalize them enough to share one workspace.

If the protocol is explicit, the harness can change while the operating model stays stable.

That is one of Hive's best properties.

## The Human Side Of Protocol

Protocol is not just for agents.

Humans benefit from the same structure:

- they can spot whether an agent updated the right layer
- they know where to look for policy
- they know what "done" is supposed to mean
- they can review a run against a visible contract

A system with strong protocol is easier to teach, easier to review, and easier to debug.

## What Good Skills Avoid

Bad skills usually do one of three things:

- they restate generic advice instead of teaching repo-specific behavior
- they point at deprecated surfaces
- they blur the line between human docs and canonical machine state

That is why Hive's v2 skill updates mattered. The architecture changed, so the teaching layer had to change with it.

## Bottom Line

Skills are not garnish in Hive.
They are how the system teaches agents to respect state, policy, and handoff.

If the substrate is the memory layer, skills are the behavior layer.

You need both.

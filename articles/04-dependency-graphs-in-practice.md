# Dependency Graphs in Practice

_A ready queue is only honest if the system understands what is actually blocked._

---

## Why Dependencies Matter

Agent systems waste enormous time on work that should never have started yet.

A task looks available.
An agent grabs it.
Halfway through, it becomes obvious the real prerequisite was still unfinished.

That is not just annoying. It is expensive.

Hive uses explicit dependency edges so the ready queue has something better than intuition to work with.

## Task-Level Dependencies Are The Center

In Hive v2, the most useful dependency relationships live on canonical tasks.

The common one is `blocks`:

```bash
hive task link task_schema blocks task_api --json
hive task link task_api blocks task_docs --json
```

That gives you a real graph:

- schema blocks API
- API blocks docs

Now the scheduler can tell the truth about what is ready.

## Ready Work Comes From The Graph

Once tasks are linked, the ready queue becomes much more valuable:

```bash
hive task ready --json
```

That command is not just listing tasks with a nice status. It is filtering out work that should stay put until upstream tasks move.

This is one of the simplest ways Hive saves teams from busy-looking but low-value agent activity.

## Project-Level Summaries Still Matter

Task edges do most of the real coordination work, but project-level dependency summaries still help humans stay oriented.

Hive keeps a compatibility-style project summary through:

```bash
hive deps --json
```

That gives you a workspace view of which projects are blocked, what they depend on, and where the obvious choke points are.

Use the project view for orientation.  
Use task edges for actual scheduling.

## A Good Dependency Graph Is Boring

The best graphs are not clever. They are explicit and restrained.

Good:

- "Implement API contract" blocks "Build client integration"
- "Write migration" blocks "Run production rollout"

Bad:

- giant webs of vague "related" tasks
- dependencies added because two tasks touch the same theme
- hidden blockers buried in `AGENCY.md` prose

If the relationship changes readiness, encode it.
If it is just context, document it.

## A Practical Pattern

Suppose you are shipping a new authentication feature.

You might model it like this:

```text
task_research -> blocks -> task_design
task_design   -> blocks -> task_impl
task_impl     -> blocks -> task_tests
task_tests    -> blocks -> task_rollout
```

That graph does a few useful things:

- it keeps early exploratory work from colliding with implementation
- it prevents rollout tasks from appearing ready too soon
- it gives reviewers a simple picture of sequencing

The bigger the team, the more this matters.

## What About Parallel Work

Dependencies are not there to force everything into a line.

They are there to tell the truth about what can safely happen in parallel.

For example:

```text
task_design -> blocks -> task_backend
task_design -> blocks -> task_frontend
task_backend -> blocks -> task_integration
task_frontend -> blocks -> task_integration
```

That lets backend and frontend proceed together after design is done, while still holding integration until both are ready.

This is much closer to how real teams work.

## What To Avoid

### Hidden dependency policy

If a reviewer has to infer the graph from comments and conventions, the graph is not explicit enough.

### Over-modeling

You do not need a dependency edge for every tiny relationship. Model the edges that affect readiness and sequencing.

### Stale links

Dependencies are operational data. When a plan changes, update the graph.

## Bottom Line

A good dependency graph does not make a workspace look sophisticated.
It makes the ready queue honest.

That is the whole point.

In Hive, task edges are how you turn a pile of possible work into a reliable picture of what should happen next.

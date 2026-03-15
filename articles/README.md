# Agent Hive Article Series

This library explains Hive as it exists now: a v2, CLI-first orchestration platform with canonical state in `.hive/`, human context in Markdown, and optional adapters around the edges.

If you only read three pieces, start here:

1. [Getting Started: Your First Agent Hive Project](06-getting-started-your-first-agent-hive-project.md)
2. [Solving the Long-Horizon Agent Problem](01-solving-the-long-horizon-agent-problem.md)
3. [Agent Hive vs. The Framework Landscape](07-agent-hive-vs-the-framework-landscape.md)

## Core articles

### 1. [Solving the Long-Horizon Agent Problem](01-solving-the-long-horizon-agent-problem.md)

Why long-running agent work breaks down, and why Hive treats durable state as a first-class primitive instead of an afterthought.

### 2. [Beads and Agent Hive: Two Approaches to Agent Memory](02-beads-and-agent-hive-two-approaches-to-agent-memory.md)

Where Hive overlaps with beads, where it makes different tradeoffs, and why file-first coordination still matters.

### 3. [Multi-Agent Coordination Without Chaos](03-multi-agent-coordination-without-chaos.md)

How claims, ready queues, dependency edges, reviewable runs, and human checkpoints let multiple agents share work without stepping on each other.

### 4. [Dependency Graphs in Practice](04-dependency-graphs-in-practice.md)

How to model blockers and sequencing in canonical task state instead of burying workflow rules in prose.

### 5. [Skills and Protocols: Teaching Agents to Work in Agent Hive](05-skills-and-protocols-teaching-agents-to-work-in-agent-hive.md)

How Hive uses startup context, skills, and explicit protocol to make different harnesses behave consistently.

### 6. [Getting Started: Your First Agent Hive Project](06-getting-started-your-first-agent-hive-project.md)

The best hands-on starting point. Install Hive, bootstrap a workspace, create a project, create tasks, and run your first governed work loop.

### 7. [Agent Hive vs. The Framework Landscape](07-agent-hive-vs-the-framework-landscape.md)

How Hive relates to LangGraph, CrewAI, AutoGen, OpenAI Agents, OpenCode, and MCP.

### 8. [Building Extensible Agent Dispatchers](08-building-extensible-agent-dispatchers.md)

How to route Hive work into GitHub issues, chatops, coding agents, or internal systems without making the dispatcher itself the source of truth.

### 9. [Security in Agent Hive](09-agent-hive-security.md)

The security model behind task files, `PROGRAM.md`, governed runs, optional execution, and human review.

### 10. [Observability with Weave Tracing](10-weave-tracing-observability.md)

How Hive's built-in run artifacts pair with optional Weave tracing when you want richer visibility into model-heavy adapters.

### 11. [Cross-Repo Multi-Agent Workflows](11-cross-repo-multi-agent-workflows.md)

How Hive can coordinate work that targets repositories outside the one hosting the orchestration state.

### 12. [Agent Hive Meets OpenCode](12-opencode-integration.md)

How Hive works with OpenCode as another harness, not as a special case.

## Suggested reading paths

### New to Hive

1. Read [06](06-getting-started-your-first-agent-hive-project.md).
2. Read [01](01-solving-the-long-horizon-agent-problem.md).
3. Read [03](03-multi-agent-coordination-without-chaos.md).

### Evaluating the architecture

1. Read [01](01-solving-the-long-horizon-agent-problem.md).
2. Read [07](07-agent-hive-vs-the-framework-landscape.md).
3. Read [02](02-beads-and-agent-hive-two-approaches-to-agent-memory.md).

### Rolling Hive out in a team

1. Read [06](06-getting-started-your-first-agent-hive-project.md).
2. Read [04](04-dependency-graphs-in-practice.md).
3. Read [08](08-building-extensible-agent-dispatchers.md).
4. Read [09](09-agent-hive-security.md).

### Extending Hive

1. Read [08](08-building-extensible-agent-dispatchers.md).
2. Read [10](10-weave-tracing-observability.md).
3. Read [11](11-cross-repo-multi-agent-workflows.md).
4. Read [12](12-opencode-integration.md).

## Notes

- These articles are launch-facing documents. They describe the v2 substrate and the public `hive` CLI, not the old v1 Cortex-centered workflow.
- Optional adapters such as the dashboard, dispatcher, MCP server, Claude GitHub App, and OpenCode integration show up where they add leverage. They are not the core of the system.

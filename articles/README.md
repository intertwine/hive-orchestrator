# Agent Hive Article Series

This directory contains a series of articles explaining the design philosophy, features, and usage of Agent Hive. These articles accompany the public release of the project.

## Articles

### 1. [Solving the Long-Horizon Agent Problem](01-solving-the-long-horizon-agent-problem.md)

*The foundational article.* Introduces the "shift-change problem" of agent memory across sessions and explains how Agent Hive addresses the challenges identified in Anthropic's research on long-running agents.

**Key topics:** Agent amnesia, context window limitations, AGENCY.md as shared memory, Deep Work sessions, vendor-agnostic design.

### 2. [Beads and Agent Hive: Two Approaches to Agent Memory](02-beads-and-agent-hive-two-approaches-to-agent-memory.md)

*Comparison and acknowledgment.* Compares Agent Hive with Steve Yegge's beads project, exploring what we borrowed, what we didn't, and why you might choose one over the other.

**Key topics:** Database vs. Markdown approach, JSONL vs. human-readable storage, query performance vs. transparency, when to use which.

### 3. [Multi-Agent Coordination Without Chaos](03-multi-agent-coordination-without-chaos.md)

*Practical coordination.* Deep dive into how multiple agents work together without stepping on each other's toes. Covers race conditions, dependency violations, and coordination patterns.

**Key topics:** Ownership protocol, three coordination layers (git, Cortex, coordinator), sequential handoff, parallel independence, ensemble collaboration.

### 4. [Dependency Graphs in Practice](04-dependency-graphs-in-practice.md)

*Real examples.* Shows how to model project relationships using Agent Hive's dependency system. Includes CLI usage, cycle detection, and practical scenarios.

**Key topics:** Four dependency types, ready work detection, cycle detection, visualization, programmatic access.

### 5. [Skills and Protocols: Teaching Agents to Work in Agent Hive](05-skills-and-protocols-teaching-agents-to-work-in-agent-hive.md)

*Agent onboarding.* Explains how skills provide on-demand knowledge and why explicit protocols make multi-agent coordination possible.

**Key topics:** Deep Work protocol, ownership protocol, blocking protocol, communication conventions, MCP tools, creating custom skills.

### 6. [Getting Started: Your First Agent Hive Project](06-getting-started-your-first-agent-hive-project.md)

*Hands-on tutorial.* Step-by-step guide to setting up Agent Hive and creating your first orchestrated project.

**Key topics:** Installation, project creation, dashboard usage, dependencies, Cortex runs, common patterns, troubleshooting.

### 7. [Agent Hive vs. The Framework Landscape](07-agent-hive-vs-the-framework-landscape.md)

*Framework comparison.* Deep dive into how Agent Hive compares to other leading AI agent frameworks including LangGraph, CrewAI, AutoGen, OpenAI Agents SDK, and smolagents.

**Key topics:** Framework philosophies, state management approaches, multi-agent coordination patterns, vendor lock-in considerations, when to use which framework, complementary architectures.

## Reading Order

For newcomers, we recommend reading in order:

1. **Article 1** - Understand the problem and solution
2. **Article 6** - Get hands-on experience
3. **Articles 3-5** - Deep dive into specific features
4. **Articles 2 & 7** - Context on the broader ecosystem and framework comparisons

## Contributing

Found an error? Have suggestions? PRs welcome! These articles are part of the Agent Hive repository and follow the same contribution guidelines.

## License

These articles are part of the Agent Hive project and are released under the MIT License.

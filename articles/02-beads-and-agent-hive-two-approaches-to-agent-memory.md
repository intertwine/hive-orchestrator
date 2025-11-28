# Beads and Agent Hive: Two Approaches to Agent Memory

*This is the second article in a series exploring Agent Hive and the landscape of AI agent orchestration.*

---

## Standing on the Shoulders of Giants

When we released Agent Hive, we acknowledged upfront that several patterns were inspired by Steve Yegge's [beads](https://github.com/steveyegge/beads) project. This wasn't a coincidence—beads emerged from hard-won lessons about what AI agents actually need to work effectively over long time horizons.

In this article, we'll explore both systems: what they share, where they differ, and why you might choose one over the other (or use both).

## The Shared Problem: Agent Amnesia

Both beads and Agent Hive tackle the same fundamental challenge that Steve Yegge memorably calls "agent amnesia":

> "By the start of phase 3 (out of 6), the AI has mostly forgotten where it came from. It wakes up, reads about phase 3, then declares it's going to break it into five phases and create a markdown plan. It begins working on 'phase 1' with no mention of the six outer phases."

This isn't a failure of any particular model—it's a structural limitation. Context windows are finite. Complex projects are not. Without persistent memory, agents become increasingly confused as projects grow.

Both systems solve this through structured persistent state that survives across context windows.

## beads: The Database Approach

beads treats agent memory as a database problem. Under the hood, it's a sophisticated distributed database that happens to use git for synchronization:

### Storage Architecture

```
.beads/
├── issues.jsonl      # Source of truth (committed to git)
├── deletions.jsonl   # Deletion records (committed to git)
└── beads.db          # Local SQLite cache (gitignored)
```

The JSONL files are the canonical state, committed to git. Each machine maintains a local SQLite cache for fast queries. Auto-sync keeps them in alignment with a 5-second debounce.

### Four Dependency Types

beads provides rich dependency modeling with four distinct relationship types:

1. **Blocks** - Issue A must complete before Issue B can start
2. **Related** - Contextual connection without ordering constraints
3. **Parent-Child** - Hierarchical decomposition of work
4. **Discovered-From** - Provenance tracking for issues found during other work

This graph structure enables agents to query for "ready work"—issues with no open blockers—and navigate complex task streams reliably.

### Designed for Speed

beads is optimized for performance. Written in Go as a single binary, it starts instantly and queries resolve in milliseconds. The SQLite cache means agents don't need to parse files or traverse git history—they just query a local database.

```bash
# Find ready work instantly
bd list --ready --json

# Create new issues on the fly
bd create "Implement authentication" --blocks bd-a1b2
```

## Agent Hive: The Markdown Approach

Agent Hive takes a different philosophical stance: **human readability is the primary constraint**.

### Storage Architecture

```
projects/
└── my-project/
    └── AGENCY.md     # Everything in one human-readable file
```

That's it. One Markdown file per project. No databases, no binary formats, no separate source of truth.

### The AGENCY.md File

```markdown
---
project_id: authentication-feature
status: active
owner: claude-sonnet-4
last_updated: 2025-01-15T14:30:00Z
blocked: false
priority: high
dependencies:
  blocked_by: [database-schema]
  blocks: [user-dashboard]
---

# Authentication Feature

## Objective
Implement secure user authentication.

## Tasks
- [x] Research OAuth2 providers
- [ ] Implement login endpoints
- [ ] Write integration tests

## Agent Notes
- **2025-01-15 14:30 - claude-sonnet-4**: Starting implementation...
```

Everything—metadata, tasks, and historical notes—lives in one file that any human (or agent) can read with a text editor.

### Designed for Transparency

Agent Hive optimizes for auditability and human oversight. When something goes wrong, you can read the Markdown. When you need to intervene, you edit text. When you want to understand what happened, you have git history of human-readable documents.

## The Key Differences

### 1. Query Model

**beads**: SQL-style queries over a normalized database
```bash
bd list --ready --json | jq '.[] | select(.priority == "high")'
```

**Agent Hive**: File traversal with in-memory filtering
```bash
uv run python -m src.cortex --ready --json
```

beads is faster for complex queries. Agent Hive doesn't require learning query syntax—you can always just read the files.

### 2. Data Format

**beads**: JSONL for machines, rendered views for humans
```json
{"id":"bd-a1b2","title":"Implement auth","status":"open","blocks":["bd-c3d4"]}
```

**Agent Hive**: Markdown for both humans and machines
```markdown
# Implement Auth
- [x] Research phase complete
- [ ] Implementation in progress
```

beads stores data optimally; Agent Hive stores data readably.

### 3. Vendor Relationship

**beads**: Primarily designed for Steve Yegge's agent workflows, with MCP integration for Claude

**Agent Hive**: Explicitly vendor-agnostic from day one—works equally well with Claude, GPT-4, Grok, Gemini, or manual human operation

### 4. Orchestration Model

**beads**: Agent-driven. The agent queries ready work and drives its own workflow.

**Agent Hive**: Hybrid orchestration. The Cortex engine provides external oversight, analyzing all projects and making state updates. Agents can also self-direct through MCP tools.

### 5. Coordination Layer

**beads**: Built-in agent coordination with "Agent Mail" concepts

**Agent Hive**: Optional HTTP coordinator server, with git-only coordination as the default fallback

## What Agent Hive Borrowed

We explicitly adopted several patterns from beads:

### Ready Work Detection

The ability to query for actionable work without LLM calls. Both systems let agents immediately understand what they can work on.

### Dependency Tracking

The `blocked_by` and `blocks` patterns for modeling task relationships. We support the same four relationship types, though with slightly different naming.

### MCP Integration

First-class Model Context Protocol support so agents can interact programmatically with the orchestration system.

### JSON Output

The `--json` flag pattern for programmatic access to all commands.

## What Agent Hive Didn't Borrow

We consciously diverged on several points:

### JSONL Storage

We kept Markdown as the storage format. The tradeoff—slower queries, larger files—was worth it for human readability.

### SQLite Caching

At current scale, in-memory operations are fast enough. We may add caching if projects grow to thousands of items.

### Single Binary

Agent Hive is Python-based, using the broader ecosystem (Streamlit for dashboard, FastAPI for coordinator). This adds dependencies but increases extensibility.

### Required Daemon

beads auto-syncs via background processes. Agent Hive treats git as the sync mechanism and makes the coordinator explicitly optional.

## When to Use Which

### Choose beads if:

- You're working primarily with Claude/Claude Code
- You have complex, deeply nested project hierarchies
- Query performance is critical
- You prefer database-style thinking
- You want minimal dependencies (single Go binary)

### Choose Agent Hive if:

- You need vendor-agnostic operation (multiple LLM providers)
- Human oversight and auditability are primary concerns
- You want to edit project state with a text editor
- You prefer Markdown-native workflows
- You want external orchestration (Cortex) in addition to agent self-direction

### Use Both if:

The systems aren't mutually exclusive. You could use beads for fine-grained task tracking within a project, while Agent Hive coordinates across projects and provides human oversight. The dependency concepts are compatible enough to bridge.

## The Deeper Pattern

Both beads and Agent Hive are responses to the same realization: **AI agents need infrastructure that matches how they actually work**.

Traditional issue trackers (Jira, GitHub Issues, Linear) were designed for humans coordinating with humans. They assume persistent memory, continuous context, and the ability to hold complex mental models.

AI agents have different characteristics:
- Discrete sessions with hard memory boundaries
- Need for explicit state on every startup
- Tendency to one-shot or prematurely declare victory
- Inability to "remember" informal agreements

Both systems acknowledge these constraints and build memory primitives that work *with* agent limitations rather than against them.

## Conclusion

beads and Agent Hive represent two valid approaches to the same problem. beads optimizes for query performance and agent autonomy. Agent Hive optimizes for transparency and human oversight.

We're grateful to Steve Yegge for open-sourcing beads and articulating the agent amnesia problem so clearly. The AI agent ecosystem benefits from multiple approaches—no single solution fits all contexts.

What matters is that we're collectively recognizing the need for purpose-built agent infrastructure. The era of "just give the agent a TODO file" is ending. The era of structured agent memory is beginning.

---

*Agent Hive is open source at [github.com/intertwine/hive-orchestrator](https://github.com/intertwine/hive-orchestrator). beads is open source at [github.com/steveyegge/beads](https://github.com/steveyegge/beads).*

## Sources

- [beads - A memory upgrade for your coding agent](https://github.com/steveyegge/beads) - Steve Yegge
- [Introducing Beads: A coding agent memory system](https://steve-yegge.medium.com/introducing-beads-a-coding-agent-memory-system-637d7d92514a) - Steve Yegge, Medium
- [The Beads Revolution](https://steve-yegge.medium.com/the-beads-revolution-how-i-built-the-todo-system-that-ai-agents-actually-want-to-use-228a5f9be2a9) - Steve Yegge, Medium

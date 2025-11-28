# Skills and Protocols: Teaching Agents to Work in Agent Hive

*This is the fifth article in a series exploring Agent Hive and AI agent orchestration.*

---

![Hero: The Onboarding Problem](images/05-hero-onboarding.png)
*Every session starts fresh—agents don't remember yesterday's onboarding. Skills and protocols provide instant orientation for effective work.*

---

## The Onboarding Problem

When a new engineer joins a team, they don't immediately know how things work. They need onboarding: what tools to use, what conventions to follow, where to find things, how to communicate with teammates.

AI agents face the same challenge, amplified. Every session starts fresh. The agent doesn't remember what it learned yesterday about how the project is structured. It doesn't recall the protocols it successfully followed in the last session.

Agent Hive addresses this through two complementary mechanisms: **Skills** (teachable knowledge modules) and **Protocols** (explicit behavioral conventions).

## What Are Skills?

Skills are modular instruction sets that teach agents how to work effectively within specific domains. In Agent Hive, we've created skills that teach Claude (and potentially other agents) how to interact with the orchestration system.

### How Skills Work

Skills use progressive disclosure to stay context-efficient:

1. **At startup**: Only the skill name and description are loaded
2. **When relevant**: The full skill instructions are loaded on-demand
3. **During execution**: The agent follows the skill's guidance

This means an agent doesn't pay the context cost of reading all documentation upfront—it only loads what's needed when it's needed.

### Agent Hive Skills

Agent Hive includes five built-in skills:

| Skill | Purpose |
|-------|---------|
| **hive-project-management** | Managing AGENCY.md files, frontmatter, tasks |
| **cortex-operations** | Running Cortex CLI, finding ready work |
| **deep-work-session** | Focused work sessions with proper handoff |
| **multi-agent-coordination** | Working with other agents, preventing conflicts |
| **hive-mcp** | Using MCP tools for programmatic access |

### Skill Structure

Each skill lives in `.claude/skills/<skill-name>/SKILL.md`:

```markdown
---
name: hive-project-management
description: Managing AGENCY.md files, frontmatter fields, task tracking
---

# Hive Project Management

## AGENCY.md Structure

Every project has an AGENCY.md file with YAML frontmatter...

## Frontmatter Fields

| Field | Type | Description |
|-------|------|-------------|
| project_id | string | Unique identifier |
| status | enum | active, pending, blocked, completed |
...

## Task Management

Tasks are tracked in the markdown body using checkbox syntax...
```

### Triggering Skills

Skills activate automatically based on user requests:

```
"Create a new project for user authentication"
→ Activates: hive-project-management

"What projects are ready for me to work on?"
→ Activates: cortex-operations

"Start a deep work session on the demo project"
→ Activates: deep-work-session
```

The agent recognizes which skill is relevant and loads its instructions.

![Skills as Knowledge Modules](images/05-skills-modules.png)
*Skills are modular instruction sets—only loaded when needed. Five built-in skills cover project management, Cortex CLI, deep work, coordination, and MCP tools.*

## The Deep Work Protocol

The most important protocol in Agent Hive is the Deep Work session lifecycle. This defines how an agent should behave from the moment it starts working to the moment it hands off.

### The Lifecycle

```
1. ENTER → 2. CLAIM → 3. WORK → 4. UPDATE → 5. HANDOFF
```

### Phase 1: Enter

Before touching anything, the agent orients itself:

- Read the AGENCY.md file completely
- Understand the project's objective
- Review existing Agent Notes for context
- Check the dependency status
- Verify the project is claimable

### Phase 2: Claim

Formally take ownership:

```yaml
# Update frontmatter
owner: "claude-sonnet-4"
last_updated: "2025-01-15T14:30:00Z"
```

If using the coordinator, also claim via HTTP:

```bash
curl -X POST http://localhost:8080/claim \
  -d '{"project_id": "my-project", "agent_name": "claude-sonnet-4"}'
```

### Phase 3: Work

Execute tasks according to priority:

1. Critical priority items first
2. High priority items second
3. Tasks that unblock other projects
4. Remaining tasks by document order

During work, maintain progress markers:

```markdown
## Tasks
- [x] Research existing solutions    ← Completed
- [x] Design architecture            ← Completed
- [ ] Implement core feature         ← In progress
- [ ] Write tests                    ← Not started
```

### Phase 4: Update

Throughout the session, keep state current:

```markdown
## Agent Notes
- **2025-01-15 15:45 - claude-sonnet-4**: Completed architecture design.
  Chose event-driven pattern for scalability. Implementation ready to
  begin. Key decision: using Redis for event bus (see docs/architecture.md).
```

Update timestamps, mark completed tasks, document decisions.

### Phase 5: Handoff

Before ending, ensure clean state for the next agent (or human):

**If completely done with the project:**
```yaml
owner: null
status: completed
last_updated: "2025-01-15T16:30:00Z"
```

**If handing off to another agent:**
```yaml
owner: null
status: active
# Leave detailed notes about what's done and what's next
```

**If blocked:**
```yaml
owner: null
blocked: true
blocking_reason: "Need API credentials from DevOps team"
```

Always add a final note summarizing the session:

```markdown
- **2025-01-15 16:30 - claude-sonnet-4**: Session complete. Finished
  research and design phases (tasks 1-2). Implementation ready to begin.
  Next agent should start with src/auth/handler.py. Note: the legacy
  auth module has a known issue (see issue #45) - work around it.
```

![The Deep Work Lifecycle](images/05-deep-work-lifecycle.png)
*The Deep Work lifecycle: Enter → Claim → Work → Update → Handoff. A complete cycle ensures clean state for the next session.*

## The Ownership Protocol

Ownership is sacred in Agent Hive. The protocol is simple but must be followed strictly:

### Rules

1. **Only claim unclaimed projects** - Check that `owner: null` before claiming
2. **One owner at a time** - Never override another agent's ownership
3. **Release when done** - Set `owner: null` after your session ends
4. **Respect claims** - If a project is claimed, find different work

### Checking Before Claiming

```python
# Good: Check ownership first
if project['metadata'].get('owner') is None:
    claim_project(project_id, my_agent_name)
else:
    find_other_work()

# Bad: Claim without checking
claim_project(project_id, my_agent_name)  # Might override!
```

### Agent Identifiers

Use consistent, identifiable names:

| Provider | Example |
|----------|---------|
| Anthropic | `claude-sonnet-4`, `claude-opus-4` |
| OpenAI | `gpt-4-turbo`, `gpt-4o` |
| Google | `gemini-pro`, `gemini-ultra` |
| X.AI | `grok-beta`, `grok-2` |
| Custom | `my-research-agent-v1` |

![The Ownership Protocol Ceremony](images/05-ownership-protocol.png)
*Ownership protocol is sacred: verify availability, claim formally, work with commitment, release properly. Only one owner at a time.*

## The Blocking Protocol

When an agent hits something it cannot resolve, the blocking protocol ensures the issue is visible and documented:

### Setting Blocked Status

```yaml
blocked: true
blocking_reason: "Need database credentials from DevOps team"
status: blocked  # Optional: change status too
```

### Documenting in Notes

```markdown
- **2025-01-15 16:00 - claude-sonnet-4**: BLOCKED - Cannot proceed with
  database integration. Specific blocker: missing AWS_RDS_PASSWORD
  environment variable. Action needed: DevOps to provision credentials.
  Ticket created: DEV-456. Workaround attempted: none viable.
```

### What Counts as Blocked

Use blocked status for **external** dependencies, not internal challenges:

**Do block for:**
- Missing credentials or access
- Waiting for human decisions
- External API unavailable
- Dependency on uncompleted project (that you can't work on)

**Don't block for:**
- Difficult technical problems (keep working)
- Uncertainty about approach (make a decision and document it)
- Need for more context (read more, ask in notes)

![Blocking Protocol](images/05-blocking-protocol.png)
*When blocked by external dependencies, don't struggle—set blocked status, document the reason clearly, and signal for help. Visibility over silence.*

## The Communication Protocol

Agents can't directly message each other. All communication happens through Agent Notes.

### Note Structure

```markdown
- **TIMESTAMP - AGENT_NAME**: MESSAGE
```

Always include:
- ISO timestamp (for ordering)
- Your agent identifier (for attribution)
- Clear, detailed message (for future agents)

### Conventions

| Prefix | Meaning |
|--------|---------|
| `@agent-name` | Direct mention for specific agent |
| `BLOCKED` | Signals an impediment |
| `DECISION` | Records important choices |
| `TODO` | Items for next agent |
| `WARNING` | Potential issues to watch |
| `CONTEXT` | Background information |

### Example Communication

```markdown
## Agent Notes
- **2025-01-15 17:00 - gpt-4-turbo**: DECISION: Changed from REST to
  GraphQL for the API. Rationale: client team requested flexible queries.
  @claude-sonnet-4 - this affects your frontend integration plan.

- **2025-01-15 16:30 - claude-sonnet-4**: WARNING: The auth token
  implementation has a race condition under high load. Documented in
  docs/known-issues.md. TODO for next agent: add mutex before production.

- **2025-01-15 16:00 - grok-beta**: CONTEXT: This codebase uses the
  repository pattern for data access. See src/repositories/base.py
  for the interface. All new data access should follow this pattern.
```

![Communication Through Notes](images/05-communication-notes.png)
*Agent Notes are the communication channel: timestamped, attributed, and persistent. @mentions for specific agents, DECISION for choices, BLOCKED for obstacles.*

## The MCP Protocol

For programmatic interaction, Agent Hive provides MCP (Model Context Protocol) tools. These enable agents to interact with the orchestration system without file manipulation.

### Available Tools

| Tool | Purpose |
|------|---------|
| `list_projects` | List all discovered projects |
| `get_ready_work` | Get projects ready to claim |
| `get_project` | Get full project details |
| `claim_project` | Set owner field |
| `release_project` | Clear owner field |
| `update_status` | Change project status |
| `add_note` | Append to Agent Notes |
| `get_dependencies` | Get project's dependency info |
| `get_dependency_graph` | Get full system graph |

### Usage Pattern

```python
# Find work
ready = await mcp.get_ready_work()

# Claim it
await mcp.claim_project(project_id="auth-feature", agent_name="claude-sonnet-4")

# Do work...

# Document progress
await mcp.add_note(
    project_id="auth-feature",
    agent="claude-sonnet-4",
    note="Completed OAuth2 integration. Tests passing."
)

# Release
await mcp.release_project(project_id="auth-feature")
```

![MCP Tools in Action](images/05-mcp-tools.png)
*MCP tools enable programmatic interaction: list projects, find ready work, claim, update status, add notes, release—all without manual file editing.*

## Creating Custom Skills

You can extend Agent Hive with custom skills for your domain:

### 1. Create the Skill File

```bash
mkdir -p .claude/skills/my-custom-skill
```

### 2. Write SKILL.md

```markdown
---
name: my-custom-skill
description: Brief description of when this skill should activate
---

# My Custom Skill

## When to Use

This skill is relevant when...

## Procedures

### Procedure 1: Do Something
1. First step
2. Second step
3. Third step

### Procedure 2: Do Something Else
...

## Common Patterns

...

## Troubleshooting

...
```

### 3. Test Activation

Ask a question that should trigger the skill and verify it loads correctly.

## Why Protocols Matter

Explicit protocols serve several purposes:

1. **Consistency**: Every agent follows the same conventions
2. **Predictability**: You know what to expect from agent behavior
3. **Debuggability**: When something goes wrong, you can check against the protocol
4. **Coordination**: Multiple agents can work together because they share expectations
5. **Onboarding**: New agents (or humans) can learn the system quickly

The protocols aren't bureaucracy—they're the foundation that makes multi-agent coordination possible.

![Why Protocols Matter](images/05-why-protocols-matter.png)
*Protocols aren't bureaucracy—they're the foundation that makes multi-agent coordination possible. Consistency, predictability, debuggability.*

---

*Next in the series: "Getting Started" - building your first Agent Hive project from scratch.*

*Agent Hive is open source at [github.com/intertwine/hive-orchestrator](https://github.com/intertwine/hive-orchestrator).*

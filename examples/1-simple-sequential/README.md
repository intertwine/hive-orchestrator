# Simple Sequential Workflow Example

## Overview

This example demonstrates the most basic Agent Hive pattern: **sequential handoff**. One agent completes research, documents findings, and hands off to another agent for implementation.

## Pattern: Research → Implement

```
┌─────────────┐         ┌──────────────┐
│  Agent A    │────────▶│   Agent B    │
│ (Research)  │         │ (Implement)  │
│   Haiku     │         │   Sonnet     │
└─────────────┘         └──────────────┘
```

## Use Case

Perfect for:
- **Separating concerns**: Research and implementation require different skills
- **Cost optimization**: Use cheaper/faster models for simple tasks, powerful models for complex ones
- **Knowledge transfer**: One agent's work becomes context for the next

## How to Run

Agent Hive supports multiple coordination approaches. Choose based on your setup:

### Method 1: Manual Deep Work Sessions (Any AI Provider)

The simplest approach - works with any AI interface.

```bash
# 1. Generate context for Agent A
make session PROJECT=examples/1-simple-sequential

# 2. Copy context to Claude/ChatGPT/Grok with Haiku model

# 3. Agent A completes research and updates AGENCY.md

# 4. Generate context for Agent B
make session PROJECT=examples/1-simple-sequential

# 5. Copy context to AI agent with Sonnet model

# 6. Agent B reads research and implements logger
```

### Method 2: Automated with Cortex

```bash
# Let Cortex orchestrate the agents
cd /path/to/agent-hive
uv run python src/cortex.py
```

Cortex will:
1. Detect the pending project
2. Assign Agent A (or suggest model)
3. Wait for completion
4. Assign Agent B
5. Mark project complete

### Method 3: Dashboard

```bash
# Start the dashboard
make dashboard

# Open http://localhost:8501
# View project, generate contexts, monitor progress
```

### Method 4: MCP Server (Claude Desktop / AI Agents)

For AI agents with MCP support (like Claude Desktop):

```bash
# Start the MCP server
uv run python -m hive_mcp
```

Configure in `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "hive": {
      "command": "uv",
      "args": ["run", "python", "-m", "hive_mcp"],
      "env": { "HIVE_BASE_PATH": "/path/to/agent-hive" }
    }
  }
}
```

**Agent A workflow (via MCP)**:
1. `claim_project("simple-sequential-example", "claude-haiku")`
2. Complete research tasks
3. `add_note("simple-sequential-example", "claude-haiku", "Research complete")`
4. `release_project("simple-sequential-example")`

**Agent B workflow (via MCP)**:
1. `get_ready_work()` → finds available project
2. `claim_project("simple-sequential-example", "claude-sonnet")`
3. Implement based on research
4. `update_status("simple-sequential-example", "completed")`
5. `release_project("simple-sequential-example")`

### Method 5: HTTP Coordination Server (Real-time Multi-Agent)

For concurrent agents that need real-time conflict prevention:

```bash
# Terminal 1: Start coordination server
uv run python -m src.coordinator

# Terminal 2: Agent A claims work
curl -X POST http://localhost:8080/claim \
  -H "Content-Type: application/json" \
  -d '{"project_id": "simple-sequential-example", "agent_name": "claude-haiku", "ttl_seconds": 1800}'

# ... Agent A works ...

# Agent A releases
curl -X DELETE http://localhost:8080/release/simple-sequential-example

# Agent B checks availability
curl http://localhost:8080/status/simple-sequential-example

# Agent B claims
curl -X POST http://localhost:8080/claim \
  -H "Content-Type: application/json" \
  -d '{"project_id": "simple-sequential-example", "agent_name": "claude-sonnet", "ttl_seconds": 3600}'
```

### Method 6: Combined MCP + Coordination (Production)

For production deployments, use both MCP (for AGENCY.md updates) and Coordination Server (for real-time locks):

```bash
# Set environment variable
export COORDINATOR_URL=http://localhost:8080
uv run python -m hive_mcp
```

**Agent workflow**:
1. `coordinator_claim(...)` - acquire real-time lock
2. `claim_project(...)` - update AGENCY.md
3. Do work
4. `release_project(...)` - update AGENCY.md
5. `coordinator_release(...)` - release real-time lock

## Expected Output

After completion, you should have:

1. **Updated AGENCY.md** with:
   - Research findings from Agent A
   - Implementation notes from Agent B
   - All tasks marked complete
   - Agent notes showing handoff

2. **src/logger.py** - Production-ready logger module

3. **Git history** showing:
   - Agent A's research commit
   - Agent B's implementation commit

## Key Concepts Demonstrated

### 1. Owner Field
```yaml
owner: "anthropic/claude-3.5-haiku"  # Agent A claims work
```
Then later:
```yaml
owner: null  # Agent A releases
```
Then:
```yaml
owner: "anthropic/claude-3.5-sonnet"  # Agent B claims work
```

### 2. Shared Memory via Markdown
Research findings written by Agent A are read by Agent B:
```markdown
## Research Findings
- Use structured logging for production systems
- Loguru offers best developer experience
- Include correlation IDs for request tracing
```

### 3. Task Progression
```markdown
- [x] Research Python logging best practices  ✓ Agent A
- [ ] Implement logger module                 ← Agent B next
```

### 4. Structured Dependencies

The AGENCY.md includes a `dependencies` field for explicit project relationships:

```yaml
dependencies:
  blocked_by: []        # Projects that must complete before this one
  blocks: []            # Projects waiting on this one
  parent: null          # Parent epic (optional)
  related: []           # Non-blocking related projects
```

For sequential projects that depend on each other:
```yaml
# In project-b/AGENCY.md
dependencies:
  blocked_by: [project-a]  # Can't start until project-a completes
```

Use `make deps` to visualize the dependency graph.

## Tips for Success

1. **Clear handoff**: Agent A should explicitly mark completion
2. **Rich context**: More detailed research = better implementation
3. **Model selection**: Match model capabilities to task complexity
4. **Timestamps**: Always update `last_updated` field
5. **Notes**: Document blockers, decisions, and discoveries

## Variations to Try

### Different Model Combinations
- **GPT-4 → Claude Sonnet**: Cross-vendor handoff
- **Haiku → Haiku**: Both tasks simple enough for fast model
- **Sonnet → Opus**: Implementation needs highest capability

### Different Domains
- Research UI frameworks → Implement component library
- Research API design → Implement REST service
- Research database schemas → Implement migrations
- Research security patterns → Implement auth system

### Extended Pipeline
Add more phases:
1. Research (Agent A)
2. Design (Agent B)
3. Implement (Agent C)
4. Test (Agent D)
5. Document (Agent E)

## Troubleshooting

**Agent B starts before Agent A finishes:**
- Check `owner` field - should be `null` when available
- Check tasks - Phase 1 should be marked complete

**No research findings:**
- Agent A must write to "Research Findings" section
- Ensure AGENCY.md is committed to Git

**Cortex doesn't detect project:**
- Verify AGENCY.md has valid YAML frontmatter
- Check `status: pending` or `active`
- Ensure file is in `examples/` directory

## Next Steps

Once you understand sequential handoff:
- Try **Example 2: Parallel Tasks** for concurrent execution
- Try **Example 3: Code Review Pipeline** for iterative refinement
- Try **Example 7: Complex Application** for multi-phase projects

---

**Estimated time**: 15-30 minutes
**Difficulty**: Beginner
**Models required**: 2 (can be same model)

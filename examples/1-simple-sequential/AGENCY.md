---
project_id: simple-sequential-example
status: pending
owner: null
last_updated: 2025-11-23T10:00:00Z
blocked: false
blocking_reason: null
priority: medium
tags: [example, sequential, tutorial]
dependencies:
  blocked_by: []
  blocks: []
  parent: null
  related: []
---

# Simple Sequential Workflow Example

## Objective
Demonstrate a basic sequential handoff pattern where one agent researches a topic and another agent implements code based on that research.

**Scenario**: Research best practices for Python logging, then implement a production-ready logger module.

## Tasks

### Phase 1: Research (Agent A - Fast Model)
- [ ] Research Python logging best practices
- [ ] Document recommended patterns (structured logging, log levels, rotation)
- [ ] Identify popular libraries (loguru, structlog, standard library)
- [ ] Write research summary in this file

### Phase 2: Implementation (Agent B - Capable Model)
- [ ] Read research findings from Agent A
- [ ] Implement a production-ready logger module
- [ ] Include configuration options (file output, rotation, formatting)
- [ ] Add usage examples and documentation

## Research Findings
<!-- Agent A: Add your research findings here -->

## Implementation Notes
<!-- Agent B: Add implementation details here -->

## Agent Notes
<!-- Add timestamped notes as you work -->

## Coordination Approaches

This example supports multiple coordination methods. Choose based on your setup:

### Approach A: Git-Only (Default)
Traditional file-based coordination using `owner` field in frontmatter.

**Agent A (Researcher) - Suggested: `anthropic/claude-3.5-haiku`**
1. Set `owner` to your model name
2. Complete research tasks
3. Update "Research Findings" section with detailed notes
4. Mark Phase 1 tasks complete
5. Set `owner: null` when done

**Agent B (Implementer) - Suggested: `anthropic/claude-3.5-sonnet`**
1. Wait for Agent A to complete (check tasks and owner field)
2. Set `owner` to your model name
3. Read research findings
4. Implement logger module in `src/logger.py`
5. Mark Phase 2 tasks complete
6. Set `status: completed` and `owner: null`

### Approach B: MCP Server (Programmatic)
AI agents use MCP tools for atomic operations.

**Agent A (via MCP)**:
1. Call `claim_project("simple-sequential-example", "claude-haiku")`
2. Call `get_project("simple-sequential-example")` to read context
3. Complete research tasks
4. Call `add_note("simple-sequential-example", "claude-haiku", "Research complete")`
5. Call `release_project("simple-sequential-example")`

**Agent B (via MCP)**:
1. Call `get_ready_work()` to find available projects
2. Call `claim_project("simple-sequential-example", "claude-sonnet")`
3. Implement based on research findings
4. Call `update_status("simple-sequential-example", "completed")`
5. Call `release_project("simple-sequential-example")`

### Approach C: HTTP Coordination (Real-time)
For concurrent environments, use the coordination server for conflict-free claiming.

**Agent A**:
```bash
curl -X POST http://localhost:8080/claim \
  -H "Content-Type: application/json" \
  -d '{"project_id": "simple-sequential-example", "agent_name": "claude-haiku", "ttl_seconds": 1800}'
# ... do work ...
curl -X DELETE http://localhost:8080/release/simple-sequential-example
```

**Agent B**:
```bash
# Check if available
curl http://localhost:8080/status/simple-sequential-example
# If not claimed, proceed
curl -X POST http://localhost:8080/claim \
  -H "Content-Type: application/json" \
  -d '{"project_id": "simple-sequential-example", "agent_name": "claude-sonnet", "ttl_seconds": 3600}'
```

### Approach D: Combined (MCP + Coordination Server)
Best for production: MCP tools automatically use the coordination server when `COORDINATOR_URL` is set.

**Agent workflow**:
1. Call `coordinator_claim("simple-sequential-example", "claude-haiku", 1800)` - real-time lock
2. Call `claim_project(...)` - updates AGENCY.md
3. Do work
4. Call `release_project(...)` - updates AGENCY.md
5. Call `coordinator_release("simple-sequential-example")` - releases real-time lock

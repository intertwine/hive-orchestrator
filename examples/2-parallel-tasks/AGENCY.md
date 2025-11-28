---
project_id: parallel-tasks-example
status: pending
owner: null
last_updated: 2025-11-23T10:00:00Z
blocked: false
blocking_reason: null
priority: medium
tags: [example, parallel, concurrent, tutorial]
dependencies:
  blocked_by: []
  blocks: []
  parent: null
  related: []
---

# Parallel Tasks Workflow Example

## Objective
Demonstrate concurrent execution where multiple agents work on independent tasks simultaneously without blocking each other.

**Scenario**: Build a utility library with multiple independent modules (validators, formatters, parsers) - each developed by a different agent in parallel.

## Tasks

### Task A: Email Validator (Agent A)
- [ ] Implement email validation function
- [ ] Support common email formats
- [ ] Include tests
- [ ] Document in `src/validators.py`

### Task B: Date Formatter (Agent B)
- [ ] Implement date formatting utilities
- [ ] Support multiple format strings (ISO, US, EU)
- [ ] Include timezone handling
- [ ] Document in `src/formatters.py`

### Task C: JSON Parser (Agent C)
- [ ] Implement safe JSON parser with error handling
- [ ] Support streaming for large files
- [ ] Add schema validation
- [ ] Document in `src/parsers.py`

### Task D: String Utilities (Agent D)
- [ ] Implement common string operations (slugify, truncate, sanitize)
- [ ] Include Unicode support
- [ ] Add performance optimizations
- [ ] Document in `src/strings.py`

## Agent Assignments

**All tasks are independent and can run in parallel!**

| Task | File | Agent | Model Suggestion |
|------|------|-------|------------------|
| A | `src/validators.py` | Agent A | `anthropic/claude-haiku-4.5` |
| B | `src/formatters.py` | Agent B | `anthropic/claude-haiku-4.5` |
| C | `src/parsers.py` | Agent C | `anthropic/claude-3.5-sonnet` |
| D | `src/strings.py` | Agent D | `google/gemini-pro` |

## Progress Tracking

### Agent A (Validators) - Status: ⏳ Waiting
- Owner: `null`
- Progress: 0/4 tasks

### Agent B (Formatters) - Status: ⏳ Waiting
- Owner: `null`
- Progress: 0/4 tasks

### Agent C (Parsers) - Status: ⏳ Waiting
- Owner: `null`
- Progress: 0/4 tasks

### Agent D (Strings) - Status: ⏳ Waiting
- Owner: `null`
- Progress: 0/4 tasks

## Agent Notes
<!-- Add timestamped notes as you work -->

## Coordination Approaches

Parallel tasks benefit especially from the HTTP Coordination Server to prevent conflicts.

### Approach A: Git-Only (Simple)
Each agent updates AGENCY.md independently. Works when agents touch different files.

**For Each Agent:**
1. **Claim your task**: Add a note with your agent ID and assigned task
2. **Work independently**: No need to wait for other agents
3. **Update progress**: Mark your subtasks complete as you go
4. **Add notes**: Document decisions and blockers
5. **Release when done**: Add completion note

### Approach B: MCP Server (Programmatic)
AI agents use MCP tools for claiming and tracking.

**Each Agent (via MCP)**:
```
1. claim_project("parallel-tasks-example", "agent-name")
2. Do assigned work on your designated file
3. add_note("parallel-tasks-example", "agent-name", "Completed Task X")
4. release_project("parallel-tasks-example")
```

**Coordination Note**: Since agents work on different files, multiple agents can safely claim this project simultaneously. The `owner` field tracks overall project ownership, but Agent Notes track individual task claims.

### Approach C: HTTP Coordination (Recommended for Parallel)
Use the coordination server to prevent race conditions when multiple agents work concurrently.

**Agent A (Validators)**:
```bash
curl -X POST http://localhost:8080/claim \
  -H "Content-Type: application/json" \
  -d '{"project_id": "parallel-tasks-validators", "agent_name": "claude-haiku", "ttl_seconds": 1800}'
# Work on src/validators.py
curl -X DELETE http://localhost:8080/release/parallel-tasks-validators
```

**Agent B (Formatters)**:
```bash
curl -X POST http://localhost:8080/claim \
  -H "Content-Type: application/json" \
  -d '{"project_id": "parallel-tasks-formatters", "agent_name": "claude-haiku", "ttl_seconds": 1800}'
# Work on src/formatters.py
curl -X DELETE http://localhost:8080/release/parallel-tasks-formatters
```

**Tip**: Use task-specific project IDs for fine-grained locking in parallel scenarios.

### Approach D: Combined MCP + Coordination (Production)
Best for high-concurrency environments:

```bash
export COORDINATOR_URL=http://localhost:8080
uv run python -m hive_mcp
```

**Agent workflow**:
1. `coordinator_claim("parallel-tasks-A", "claude-haiku", 1800)` - task-level lock
2. Do work on assigned file
3. `add_note(...)` - update shared AGENCY.md
4. `coordinator_release("parallel-tasks-A")` - release lock

**Check all reservations**: `coordinator_reservations()` to see who's working on what.

### Important Notes:
- ✅ Tasks are **fully independent** - minimal coordination needed
- ✅ Each agent works on **different files** - no merge conflicts
- ✅ Project is **complete** when all 4 tasks are done
- ✅ Use task-specific claim IDs for fine-grained parallel control

### Example Agent Note:
```markdown
- **2025-11-23 10:30 - Claude Haiku (Agent A)**: Starting work on email validator
- **2025-11-23 10:45 - Claude Haiku (Agent A)**: Completed validators.py, all tests passing
```

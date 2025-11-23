---
project_id: parallel-tasks-example
status: pending
owner: null
last_updated: 2025-11-23T10:00:00Z
blocked: false
blocking_reason: null
priority: medium
tags: [example, parallel, concurrent, tutorial]
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
| A | `src/validators.py` | Agent A | `anthropic/claude-3.5-haiku` |
| B | `src/formatters.py` | Agent B | `anthropic/claude-3.5-haiku` |
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

## Coordination Protocol

### For Each Agent:

1. **Claim your task**: Add a note here with your agent ID and assigned task
2. **Work independently**: No need to wait for other agents
3. **Update progress**: Mark your subtasks complete as you go
4. **Add notes**: Document decisions and blockers
5. **Release when done**: Remove yourself from notes when complete

### Important Notes:
- ✅ Tasks are **fully independent** - no coordination needed
- ✅ Multiple agents can have `owner` field simultaneously (in their notes)
- ✅ Each agent works on **different files** - no merge conflicts
- ✅ Project is **complete** when all 4 tasks are done

### Example Agent Note:
```markdown
- **2025-11-23 10:30 - Claude Haiku (Agent A)**: Starting work on email validator
- **2025-11-23 10:45 - Claude Haiku (Agent A)**: Completed validators.py, all tests passing
```

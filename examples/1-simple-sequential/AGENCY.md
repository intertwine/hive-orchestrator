---
project_id: simple-sequential-example
status: pending
owner: null
last_updated: 2025-11-23T10:00:00Z
blocked: false
blocking_reason: null
priority: medium
tags: [example, sequential, tutorial]
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

## Handoff Protocol

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

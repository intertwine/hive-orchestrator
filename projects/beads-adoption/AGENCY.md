---
project_id: beads-adoption
status: active
owner: null
last_updated: 2025-11-27T12:00:00Z
blocked: false
blocking_reason: null
priority: high
tags: [enhancement, architecture, multi-agent]
dependencies:
  blocks: []
  blocked_by: []
  parent: null
  related: []
---

# Beads Pattern Adoption for Hive Orchestrator

## Project Context

Analysis of the [beads](https://github.com/steveyegge/beads) project revealed several patterns that could significantly improve Hive Orchestrator's multi-agent coordination capabilities while preserving our core philosophy of human-readable Markdown and vendor agnosticism.

## Objective

Adopt key patterns from beads to enhance Hive Orchestrator:
- Deterministic ready-work detection (no LLM required)
- Structured dependency tracking between projects
- MCP server for first-class agent tooling
- JSON output mode for programmatic access
- Optional real-time coordination layer

## Design Principles (Preserve These)

1. **Markdown-First**: All state remains human-readable
2. **Vendor Agnostic**: Works with any LLM provider
3. **Git as Truth**: No required external services
4. **Simple Primitives**: AGENCY.md files are the core abstraction
5. **Human-in-the-Loop**: Transparent, auditable operations

## Implementation Phases

### Phase 1: Ready Work Detection
Add deterministic `ready_work()` function to find actionable projects without LLM calls.

**Tasks:**
- [ ] Add `ready_work()` function to cortex.py
- [ ] Filter: `status == 'active' AND blocked == false AND owner == null`
- [ ] Add CLI command: `make ready` or `uv run python -m src.cortex --ready`
- [ ] Add `--json` output flag for programmatic access
- [ ] Write tests for ready_work functionality

### Phase 2: Structured Dependencies
Enhance AGENCY.md frontmatter with explicit dependency tracking.

**Tasks:**
- [ ] Define dependency schema in AGENCY.md format
- [ ] Update cortex.py to parse `dependencies` field
- [ ] Implement `is_blocked()` that checks dependency graph
- [ ] Add cycle detection for blocking dependencies
- [ ] Update dashboard.py to visualize dependencies
- [ ] Write tests for dependency resolution

### Phase 3: MCP Server (hive-mcp)
Create Model Context Protocol server for agent integration.

**Tasks:**
- [ ] Create `src/hive_mcp/` package structure
- [ ] Implement `list_projects()` tool
- [ ] Implement `get_ready_work()` tool
- [ ] Implement `claim_project(project_id, agent_name)` tool
- [ ] Implement `update_status(project_id, status)` tool
- [ ] Implement `add_note(project_id, note)` tool
- [ ] Add MCP server configuration docs
- [ ] Write tests for MCP tools

### Phase 4: Agent Coordination Layer (Optional)
Add lightweight HTTP coordination for real-time conflict prevention.

**Tasks:**
- [ ] Design reservation API (POST /claim, DELETE /release)
- [ ] Create FastAPI server in `src/coordinator.py`
- [ ] Implement 409 Conflict response for contested claims
- [ ] Add graceful fallback to git-only mode
- [ ] Document deployment options
- [ ] Write integration tests

## Technical Specifications

### Ready Work Query Logic
```python
def ready_work(projects: List[Dict]) -> List[Dict]:
    """Return projects that are actionable right now."""
    return [
        p for p in projects
        if p['metadata'].get('status') == 'active'
        and not p['metadata'].get('blocked', False)
        and p['metadata'].get('owner') is None
        and not has_unresolved_blockers(p)
    ]
```

### Dependency Schema
```yaml
dependencies:
  blocks: [project-b, project-c]  # These wait on us
  blocked_by: [project-a]          # We wait on these
  parent: epic-project-id          # Part of larger epic
  related: [project-d]             # Context only, no blocking
```

### MCP Tool Interface
```python
# Tools exposed via MCP
list_projects() -> List[ProjectSummary]
get_ready_work() -> List[ProjectSummary]
claim_project(project_id: str, agent_name: str) -> ClaimResult
release_project(project_id: str) -> ReleaseResult
update_status(project_id: str, status: str) -> UpdateResult
add_note(project_id: str, agent: str, note: str) -> NoteResult
```

## Success Criteria

- [ ] `ready_work()` returns correct projects in <100ms
- [ ] Dependency graph correctly identifies blocked projects
- [ ] MCP server integrates with Claude Desktop
- [ ] All existing tests continue to pass
- [ ] New functionality has >90% test coverage
- [ ] Documentation updated for new features

## Reference Material

**Beads Repository:** https://github.com/steveyegge/beads

**Key Beads Concepts Adopted:**
- Hash-based IDs for collision prevention
- Four dependency types (blocks, related, parent-child, discovered-from)
- Ready work detection via fast queries
- MCP integration for AI agents
- JSON output for programmatic access

**Key Beads Concepts NOT Adopted:**
- JSONL storage format (keeping Markdown)
- Required daemon process (keeping optional)
- SQLite caching (not needed at current scale)

## Agent Notes

**2025-11-27 - Claude (Opus)**: Created project from analysis of beads repository. Identified 4 implementation phases with Phase 1 (Ready Work Detection) as highest priority due to low effort and high impact. Preserved Hive's core design principles while adopting beads' best patterns.

---

## Next Steps

1. Claim this project by setting `owner` field
2. Start with Phase 1: Ready Work Detection
3. Update tasks as completed with `[x]`
4. Add notes documenting decisions and progress

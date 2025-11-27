---
project_id: agent-coordination
status: pending
owner: null
last_updated: 2025-11-27T20:00:00Z
blocked: false
blocking_reason: null
priority: medium
tags: [enhancement, real-time, coordination, api]
dependencies:
  blocks: []
  blocked_by: []
  parent: beads-adoption
  related: [beads-adoption, hive-mcp]
---

# Agent Coordination Layer (Phase 4)

## Project Context

Part of the beads pattern adoption (Phase 4). Create an optional real-time coordination layer inspired by beads' Agent Mail concept. This enables multiple agents to coordinate in real-time without git conflicts.

> **Note**: This is an **optional** enhancement. Agent Hive works perfectly with git-only coordination. This layer is for scenarios requiring faster conflict resolution.

## Objective

Build a lightweight HTTP coordination server that:
- Prevents multiple agents from claiming the same project
- Provides real-time reservation system
- Falls back gracefully to git-only mode when unavailable
- Remains optional (not required for core functionality)

## Design Principles

1. **Optional**: Never required; git-only mode always works
2. **Lightweight**: Minimal dependencies, fast startup
3. **Stateless-First**: Memory-based by default, optional persistence
4. **Graceful Degradation**: If coordinator unavailable, fall back to git
5. **Simple API**: REST endpoints, no complex protocols

## Implementation Tasks

### Core Server
- [ ] Create `src/coordinator.py` with FastAPI server
- [ ] Implement `/claim` endpoint (POST)
- [ ] Implement `/release` endpoint (DELETE)
- [ ] Implement `/status` endpoint (GET)
- [ ] Implement `/reservations` endpoint (GET all)
- [ ] Add request validation and error handling

### Conflict Resolution
- [ ] Return 409 Conflict when project already claimed
- [ ] Include current owner in conflict response
- [ ] Add optional force-claim with `?force=true` (admin use)
- [ ] Implement claim expiration (configurable TTL)

### Integration
- [ ] Add coordinator client to Cortex class
- [ ] Update MCP server with coordination support
- [ ] Add `COORDINATOR_URL` environment variable
- [ ] Implement graceful fallback when coordinator unavailable
- [ ] Add coordination status to dashboard

### Testing
- [ ] Write unit tests for all endpoints
- [ ] Test concurrent claim scenarios
- [ ] Test fallback behavior
- [ ] Integration tests with MCP server

### Documentation
- [ ] Add deployment instructions to README
- [ ] Document API endpoints
- [ ] Add Docker deployment option
- [ ] Document scaling considerations

## Technical Specifications

### API Endpoints

```
POST   /claim          - Claim a project
DELETE /release/{id}   - Release a project
GET    /status/{id}    - Check claim status
GET    /reservations   - List all active claims
GET    /health         - Health check
```

### Claim Request

```json
{
  "project_id": "my-project",
  "agent_name": "claude-opus",
  "ttl_seconds": 3600
}
```

### Claim Response (Success)

```json
{
  "success": true,
  "claim_id": "uuid-here",
  "project_id": "my-project",
  "agent_name": "claude-opus",
  "expires_at": "2025-11-27T21:00:00Z"
}
```

### Claim Response (Conflict - 409)

```json
{
  "success": false,
  "error": "Project already claimed",
  "current_owner": "grok-beta",
  "claimed_at": "2025-11-27T19:30:00Z",
  "expires_at": "2025-11-27T20:30:00Z"
}
```

### Cortex Integration

```python
class Cortex:
    def __init__(self, coordinator_url: str = None):
        self.coordinator = CoordinatorClient(coordinator_url) if coordinator_url else None

    def claim_project(self, project_id: str, agent_name: str) -> bool:
        # Try coordinator first if available
        if self.coordinator:
            try:
                return self.coordinator.claim(project_id, agent_name)
            except CoordinatorUnavailable:
                pass  # Fall back to git-only

        # Git-only mode: update AGENCY.md directly
        return self._claim_via_git(project_id, agent_name)
```

### Deployment Options

1. **Local Development**: Run alongside dashboard
2. **Docker**: Single container deployment
3. **Cloud Run / Lambda**: Serverless option
4. **Kubernetes**: For multi-replica deployments

## Success Criteria

- [ ] Server starts in <1 second
- [ ] Claims resolve in <50ms
- [ ] Graceful degradation tested
- [ ] No single point of failure (optional component)
- [ ] Memory usage <50MB
- [ ] All tests pass

## Reference Material

**Beads Agent Mail**: https://github.com/steveyegge/beads
- Similar reservation concept
- Real-time coordination for AI agents
- Prevents work duplication

**FastAPI**: https://fastapi.tiangolo.com/
- Modern Python web framework
- Automatic OpenAPI docs
- Fast performance

## Agent Notes

**2025-11-27 - Claude (Opus)**: Created project as Phase 4 of beads adoption. This is intentionally marked as optional - the core Agent Hive functionality works perfectly with git-only coordination. This layer is for teams wanting faster real-time coordination between multiple concurrent agents.

---

## Next Steps

1. Decide on persistence strategy (memory-only vs Redis/SQLite)
2. Define claim TTL defaults
3. Implement core server
4. Add integration tests
5. Document deployment options

---
blocked: false
blocking_reason: null
dependencies:
  blocked_by: []
  blocks: []
  parent: beads-adoption
  related:
  - beads-adoption
  - hive-mcp
last_updated: '2026-03-13T00:03:37.227313Z'
owner: null
priority: medium
project_id: agent-coordination
status: completed
tags:
- enhancement
- real-time
- coordination
- api
---

# Agent Coordination Layer (Phase 4)

> Historical note: this project record preserves the optional coordination work that landed during the v2 migration. Older task titles below still mention `Cortex`, dashboard integration, or project-owner era language because they were imported from that period. The current model is task claims on canonical `.hive/tasks/*.md`, with the coordinator acting only as an optional live lock service.

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
- [x] Create `src/coordinator.py` with FastAPI server
- [x] Implement `/claim` endpoint (POST)
- [x] Implement `/release` endpoint (DELETE)
- [x] Implement `/status` endpoint (GET)
- [x] Implement `/reservations` endpoint (GET all)
- [x] Add request validation and error handling

### Conflict Resolution
- [x] Return 409 Conflict when project already claimed
- [x] Include current owner in conflict response
- [x] Add optional force-claim with `?force=true` (admin use)
- [x] Implement claim expiration (configurable TTL)

### Integration
- [x] Add coordinator client to Cortex class (`src/coordinator_client.py`)
- [x] Update MCP server with coordination support
- [x] Add `COORDINATOR_URL` environment variable support
- [x] Implement graceful fallback when coordinator unavailable
- [ ] Add coordination status to dashboard

### Testing
- [x] Write unit tests for all endpoints
- [x] Test concurrent claim scenarios
- [x] Test fallback behavior
- [x] Integration tests with MCP server

### Documentation
- [x] Add deployment instructions to README
- [x] Document API endpoints
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

### Legacy Integration Sketch

```python
def claim_task(task_id: str, owner: str, coordinator: CoordinatorClient | None) -> bool:
    """Historical sketch: coordinator first, canonical task claim second."""
    if coordinator:
        try:
            return coordinator.claim(task_id, owner)
        except CoordinatorUnavailable:
            pass

    return hive_task_claim(task_id, owner)
```

### Deployment Options

1. **Local Development**: Run alongside dashboard
2. **Docker**: Single container deployment
3. **Cloud Run / Lambda**: Serverless option
4. **Kubernetes**: For multi-replica deployments

## Success Criteria

- [x] Server starts in <1 second
- [x] Claims resolve in <50ms
- [x] Graceful degradation tested
- [x] No single point of failure (optional component)
- [x] Memory usage <50MB
- [x] All tests pass (41 coordinator tests)

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

**2025-11-27 - Claude (Opus)**: Implemented core coordination layer:
- Created `src/coordinator.py` - FastAPI server with /claim, /release, /status, /reservations, /health, /extend endpoints
- Created `src/coordinator_client.py` - Client library with graceful fallback when coordinator unavailable
- Updated MCP server with 4 new tools: coordinator_status, coordinator_claim, coordinator_release, coordinator_reservations
- Added 41 comprehensive tests in `tests/test_coordinator.py` covering server, client, and integration scenarios
- Added FastAPI and uvicorn dependencies to pyproject.toml
- All 152 tests passing, pylint score 10.00/10 for new code
- Remaining: Dashboard integration, documentation, Docker deployment

---

## Next Steps

Core implementation complete! Remaining optional enhancements:

1. Add coordination status to dashboard
2. Docker deployment option
3. Consider persistence strategy (Redis/SQLite) for production
4. Document scaling considerations for high-availability deployments

<!-- hive:begin task-rollup -->
## Task Rollup

| ID | Status | Priority | Owner | Title |
|---|---|---:|---|---|
| task_01KKQGXZRSY4N1SDDE2NEND1PY | done | 2 |  | Add `COORDINATOR_URL` environment variable support |
| task_01KKQGXZRVWGVD1TS5HEN76XBQ | ready | 2 |  | Add coordination status to dashboard |
| task_01KKQGXZRQ5YRSYM9PEGCZYNPB | done | 2 |  | Add coordinator client to Cortex class (`src/coordinator_client.py`) |
| task_01KKQGXZS37VRD157JKKDR6EX9 | done | 2 |  | Add deployment instructions to README |
| task_01KKQGXZS73YKGPD2BW1346A8D | ready | 2 |  | Add Docker deployment option |
| task_01KKQGXZRNNSTMKAWQJ4R81VE6 | done | 2 |  | Add optional force-claim with `?force=true` (admin use) |
| task_01KKQGXZRJZK5QYQS4XJVRZE34 | done | 2 |  | Add request validation and error handling |
| task_01KKQGXZSG3JSCG10WHCN00XS8 | done | 2 |  | All tests pass (41 coordinator tests) |
| task_01KKQGXZSBR8N6PJ4Z1YVKFKF2 | done | 2 |  | Claims resolve in <50ms |
| task_01KKQGXZRC4QPP1P18DB198WAZ | done | 2 |  | Create `src/coordinator.py` with FastAPI server |
| task_01KKQGXZS5PYDAVM17XJ8RBM1X | done | 2 |  | Document API endpoints |
| task_01KKQGXZS8ER4B2SJ0Z72W50MJ | ready | 2 |  | Document scaling considerations |
| task_01KKQGXZSCSPQ665ST5H6PKG7F | done | 2 |  | Graceful degradation tested |
| task_01KKQGXZRESF4YK70HSTW2Y7YA | done | 2 |  | Implement `/claim` endpoint (POST) |
| task_01KKQGXZRFMQB2TFCQ4BPYKS0Q | done | 2 |  | Implement `/release` endpoint (DELETE) |
| task_01KKQGXZRH5ZECMFZ2PC6GA44G | done | 2 |  | Implement `/reservations` endpoint (GET all) |
| task_01KKQGXZRGRE34YENV023Z1Y92 | done | 2 |  | Implement `/status` endpoint (GET) |
| task_01KKQGXZRP3KR1NH6MBRY1AGF8 | done | 2 |  | Implement claim expiration (configurable TTL) |
| task_01KKQGXZRTBTFPB3TAN9P7N7NA | done | 2 |  | Implement graceful fallback when coordinator unavailable |
| task_01KKQGXZRMDPGFZ8FFRVK7TP1C | done | 2 |  | Include current owner in conflict response |
| task_01KKQGXZS2GVX5XY4TKEHS1CYX | done | 2 |  | Integration tests with MCP server |
| task_01KKQGXZSFQV8TNWAJTM069TNM | done | 2 |  | Memory usage <50MB |
| task_01KKQGXZSDW7TXBBP27WWW35PN | done | 2 |  | No single point of failure (optional component) |
| task_01KKQGXZRKEAAE1THGQ4TP4ZJH | done | 2 |  | Return 409 Conflict when project already claimed |
| task_01KKQGXZSAC0AADG1AD5SEQME1 | done | 2 |  | Server starts in <1 second |
| task_01KKQGXZRXQTN2KJV3ZQ9WWSE3 | done | 2 |  | Test concurrent claim scenarios |
| task_01KKQGXZS1W4E6N3PG9182KXVY | done | 2 |  | Test fallback behavior |
| task_01KKQGXZRR35C52FSBQNWNSQV1 | done | 2 |  | Update MCP server with coordination support |
| task_01KKQGXZRWXZSRQS9NYNGEGZRX | done | 2 |  | Write unit tests for all endpoints |
<!-- hive:end task-rollup -->

<!-- hive:begin recent-runs -->
## Recent Runs

| Run | Status | Task |
|---|---|---|
| No runs | - | - |
<!-- hive:end recent-runs -->

# Hive 2.2 Driver and Event Spec

Status: Proposed  
Date: 2026-03-15

## 1. Driver interface

```python
class Driver(Protocol):
    def probe(self) -> DriverInfo: ...
    def launch(self, req: RunLaunchRequest) -> RunHandle: ...
    def resume(self, handle: RunHandle) -> RunHandle: ...
    def status(self, handle: RunHandle) -> RunStatus: ...
    def interrupt(self, handle: RunHandle, mode: InterruptMode) -> Ack: ...
    def steer(self, handle: RunHandle, req: SteeringRequest) -> Ack: ...
    def collect_artifacts(self, handle: RunHandle) -> ArtifactBundle: ...
    def stream_events(self, handle: RunHandle) -> Iterator[DriverEvent]: ...
```

Optional:

```python
class AdvancedDriver(Driver, Protocol):
    def checkpoint(self, handle: RunHandle) -> DriverCheckpoint: ...
    def reroute_export(self, handle: RunHandle) -> RerouteBundle: ...
    def reroute_import(self, bundle: RerouteBundle) -> RunHandle: ...
    def exec_preview(self, req: RunLaunchRequest) -> ExecPreview: ...
```

## 2. Core types

### 2.1 DriverInfo

```json
{
  "driver": "codex",
  "version": "0.0.0",
  "available": true,
  "capabilities": {
    "worktrees": true,
    "resume": true,
    "streaming": true,
    "subagents": true,
    "scheduled": true,
    "remote_execution": false,
    "diff_preview": true,
    "sandbox": "medium",
    "context_files": ["AGENTS.md"],
    "skills": true,
    "interrupt": ["pause", "cancel"],
    "reroute_export": "transcript-aware"
  },
  "notes": []
}
```

### 2.2 RunLaunchRequest

```json
{
  "run_id": "run_01HQ...",
  "task_id": "task_01HQ...",
  "project_id": "proj_01HQ...",
  "campaign_id": null,
  "driver": "codex",
  "model": "gpt-5.4-codex",
  "budget": {
    "max_tokens": 400000,
    "max_cost_usd": 20.0,
    "max_wall_minutes": 60
  },
  "workspace": {
    "repo_root": "/repo",
    "worktree_path": "/repo/.hive/worktrees/run_01HQ...",
    "base_branch": "main"
  },
  "compiled_context_path": ".hive/compiled-context/run_01HQ...",
  "artifacts_path": ".hive/runs/run_01HQ...",
  "program_policy": {
    "network": "ask",
    "paths": ["src/**", "tests/**"],
    "blocked_paths": ["infra/prod/**"],
    "evaluator_policy": "required"
  },
  "steering_notes": [],
  "metadata": {
    "initiator": "human",
    "source": "hive run launch"
  }
}
```

### 2.3 RunHandle

```json
{
  "run_id": "run_01HQ...",
  "driver": "codex",
  "driver_handle": "codex-thread-123",
  "status": "launching",
  "launched_at": "2026-03-15T14:00:00Z"
}
```

### 2.4 RunStatus

```json
{
  "run_id": "run_01HQ...",
  "state": "running",
  "health": "healthy",
  "driver": "codex",
  "progress": {
    "phase": "implementing",
    "message": "Applying patch and running tests",
    "percent": 70
  },
  "waiting_on": null,
  "last_event_at": "2026-03-15T14:08:45Z",
  "budget": {
    "spent_tokens": 112000,
    "spent_cost_usd": 4.31,
    "wall_minutes": 9
  },
  "links": {
    "driver_ui": null
  }
}
```

## 3. Event schema

All events are append-only JSONL records.

## 3.1 Common fields

```json
{
  "event_id": "evt_01HQ...",
  "ts": "2026-03-15T14:08:45Z",
  "type": "run.status.changed",
  "run_id": "run_01HQ...",
  "task_id": "task_01HQ...",
  "project_id": "proj_01HQ...",
  "campaign_id": null,
  "actor": {
    "kind": "system",
    "id": "driver:codex"
  },
  "payload": {}
}
```

## 3.2 Required event types

### Run lifecycle

- `run.queued`
- `run.context_compiled`
- `run.launch_started`
- `run.launched`
- `run.status.changed`
- `run.awaiting_input`
- `run.awaiting_review`
- `run.completed_candidate`
- `run.accepted`
- `run.rejected`
- `run.escalated`
- `run.cancelled`
- `run.failed`

### Artifacts and eval

- `artifact.added`
- `eval.started`
- `eval.completed`
- `eval.failed`
- `review.summary_generated`

### Steering

- `steering.pause`
- `steering.resume`
- `steering.cancel`
- `steering.reroute_requested`
- `steering.rerouted`
- `steering.note_added`
- `steering.budget_changed`
- `steering.approve`
- `steering.reject`
- `steering.rollback`
- `steering.sidequest_created`

### Memory/context

- `context.compiled`
- `memory.proposed`
- `memory.accepted`
- `memory.rejected`

### Campaigns

- `campaign.created`
- `campaign.tick`
- `campaign.goal_updated`
- `campaign.completed`

## 4. SteeringRequest schema

```json
{
  "action": "reroute",
  "reason": "Use Claude Code for broader repo search",
  "target": {
    "driver": "claude-code",
    "model": "claude-opus-4.5"
  },
  "budget_delta": {
    "max_wall_minutes": 30
  },
  "note": "Preserve current patch and transcript if possible"
}
```

## 5. Context manifest schema

```json
{
  "run_id": "run_01HQ...",
  "generated_at": "2026-03-15T13:59:58Z",
  "entries": [
    {
      "id": "ctx_001",
      "source_path": "projects/api/PROGRAM.md",
      "source_type": "program",
      "required": true,
      "tokens_estimate": 320,
      "reason": "governing policy",
      "truncated": false
    },
    {
      "id": "ctx_002",
      "source_path": ".hive/memory/project/profile.md",
      "source_type": "memory",
      "required": false,
      "tokens_estimate": 210,
      "reason": "recent learned conventions for this project",
      "truncated": true
    },
    {
      "id": "ctx_003",
      "source_path": "docs/recipes/react-testing.md",
      "source_type": "search-hit",
      "required": false,
      "tokens_estimate": 90,
      "reason": "matched task tag=testing",
      "truncated": false
    }
  ],
  "outputs": ["run-brief.md", "AGENTS.md", "skills-manifest.json"],
  "totals": {
    "tokens_estimate": 1050,
    "entries": 3
  }
}
```

## 6. Reroute grades

Drivers MUST advertise one of:

- `none`
- `metadata-only`
- `transcript-aware`
- `checkpoint-aware`

Definitions:

- `metadata-only`: carry task/run metadata only
- `transcript-aware`: carry normalized transcript and steering history
- `checkpoint-aware`: additionally carry resumable internal state or workspace checkpoint

## 7. Health model

All runs MUST map to one of:

- `healthy`
- `waiting`
- `attention`
- `blocked`
- `failing`
- `unknown`

Derivation examples:

- no events for N minutes beyond policy threshold -> `attention`
- failed required evaluator -> `blocked`
- awaiting approval -> `waiting`
- driver error -> `failing`

## 8. CLI JSON stability rules

1. Every command used by agents MUST support `--json`.
2. Human-friendly text output MAY change; JSON keys MAY NOT change in minor versions without aliasing.
3. `schema_version` MUST be included in top-level JSON responses.
4. `type` and `id` fields MUST be stable.
5. New fields MAY be added only in backward-compatible ways.

## 9. Driver conformance tests

A driver is “v2.2 compatible” only if it passes:

- probe test
- launch test
- status polling test
- interrupt test
- artifact collection test
- normalized transcript test
- event emission test
- capability declaration test
- reroute declaration test

## 10. Initial driver matrix

| Driver        |  MVP | Resume | Streaming |          Reroute | Notes                          |
| ------------- | ---: | -----: | --------: | ---------------: | ------------------------------ |
| `local`       |  Yes |    N/A |       Yes |    metadata-only | Canonical fallback             |
| `manual`      |  Yes |    N/A |        No |    metadata-only | Human copy/paste bridge        |
| `codex`       |  Yes |    Yes |       Yes | transcript-aware | Primary v2.2 launch driver     |
| `claude-code` |  Yes |    Yes |       Yes | transcript-aware | Primary v2.2 launch driver     |
| `pi`          | Beta |    TBD |       TBD |    metadata-only | Keep contract simple           |
| `hermes`      | Beta |    Yes |       TBD | transcript-aware | Memory-rich adapter            |
| `openclaw`    | Beta |    Yes |       TBD |    metadata-only | Routing/control-plane learning |

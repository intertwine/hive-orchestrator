# Agent Hive v2.3 Runtime and Sandbox Spec

Status: Historical design reference  
Date: 2026-03-17

Current scoped release truth lives in `docs/V2_3_STATUS.md`. This spec remains valuable as a searchable design
reference even where the shipped v2.3 line intentionally narrowed scope or deferred parts of the proposal.

## 1. Purpose

This spec freezes the runtime contract Hive uses to supervise external harnesses and execution environments.

This document is intentionally prescriptive. The goal is not to leave room for stylistic interpretation. The goal is to make the coding agent implement a truthful, durable, backtestable runtime layer.

## 2. Core principles

1. A **driver** talks to the worker harness.
2. A **sandbox backend** constrains execution.
3. A **runpack** is the canonical handoff artifact.
4. An **event normalizer** turns driver output into append-only Hive events.
5. A **capability snapshot** records what is possible, what is available, and what is actually in use.
6. A **run** can be reviewed later without reconstructing hidden state.

## 3. Driver v2 interface

```python
class DriverV2(Protocol):
    name: str

    def probe(self) -> DriverProbe: ...
    def prepare_runpack(self, request: RunLaunchRequest) -> RunPack: ...
    def launch(self, runpack: RunPack, sandbox: SandboxHandle | None) -> RunHandle: ...
    def attach(self, handle: RunHandle) -> RunHandle: ...
    def status(self, handle: RunHandle) -> RunStatus: ...
    def interrupt(self, handle: RunHandle, mode: InterruptMode) -> Ack: ...
    def steer(self, handle: RunHandle, request: SteeringRequest) -> Ack: ...
    def collect_artifacts(self, handle: RunHandle) -> ArtifactBundle: ...
    def stream_events(self, handle: RunHandle) -> Iterator[DriverEvent]: ...
    def terminate(self, handle: RunHandle) -> Ack: ...
```

Optional interfaces:

```python
class CheckpointingDriver(Protocol):
    def checkpoint(self, handle: RunHandle) -> DriverCheckpoint: ...

class RerouteableDriver(Protocol):
    def export_for_reroute(self, handle: RunHandle) -> RerouteBundle: ...
    def import_for_reroute(self, bundle: RerouteBundle) -> RunHandle: ...
```

## 4. Capability snapshot

## 4.1 Why this exists

The current flat capability reporting is too optimistic for staged adapters. v2.3 replaces it with a structured snapshot captured at runtime.

## 4.2 Schema

```json
{
  "driver": "codex",
  "driver_version": "x.y.z",
  "captured_at": "2026-03-17T15:00:00Z",
  "declared": {
    "launch_mode": "app_server",
    "session_persistence": "thread",
    "event_stream": "structured_deltas",
    "approvals": ["command", "file", "network"],
    "skills": "explicit_invoke",
    "worktrees": "host_managed",
    "subagents": "native",
    "native_sandbox": "policy",
    "outer_sandbox_required": true,
    "artifacts": ["diff", "transcript", "plan", "review"],
    "reroute_export": "transcript_plus_context"
  },
  "probed": {
    "binary_present": true,
    "app_server_available": true,
    "exec_available": true,
    "skill_api_available": true,
    "review_api_available": true,
    "sandbox_mode_supported": true
  },
  "effective": {
    "launch_mode": "app_server",
    "session_persistence": "thread",
    "event_stream": "structured_deltas",
    "approvals": ["command", "file"],
    "skills": "explicit_invoke",
    "worktrees": "host_managed",
    "subagents": "native",
    "native_sandbox": "policy",
    "outer_sandbox_required": true,
    "artifacts": ["diff", "transcript", "plan"],
    "reroute_export": "transcript_plus_context"
  },
  "confidence": {
    "launch_mode": "verified",
    "event_stream": "verified",
    "subagents": "declared_only"
  },
  "evidence": {
    "launch_mode": "codex app-server initialize succeeded",
    "event_stream": "turn/started + item/* + turn/completed observed",
    "subagents": "driver supports subagents, but current run does not invoke them"
  }
}
```

## 4.3 Required capability categories

These names are frozen:

- `launch_mode`: `staged | exec | sdk | app_server | rpc | local`
- `session_persistence`: `none | session | thread`
- `event_stream`: `none | status | structured_deltas`
- `approvals`: `[] | ["command"] | ["command","file"] | ...`
- `skills`: `none | file_projection | list | explicit_invoke`
- `worktrees`: `none | host_managed | native | hook_managed`
- `subagents`: `none | native | hive_emulated`
- `native_sandbox`: `none | policy | os_sandbox`
- `outer_sandbox_required`: `true | false`
- `artifacts`: list of artifact kinds
- `reroute_export`: `none | transcript | transcript_plus_context`

## 5. Runpack

The runpack is the canonical pre-launch bundle. It must exist even for local deterministic runs.

```text
.hive/runs/<run-id>/
  manifest.json
  capability-snapshot.json
  sandbox-policy.json
  prompt.md
  context/
    task.md
    project.md
    program.md
    memory.md
    retrieval.json
    skills/
  projections/
    AGENTS.md
    CLAUDE.md
    .claude/skills/
    .pi/
  driver/
    codex.json
    claude.json
    pi.json
  events.ndjson
  approvals.ndjson
  transcript.ndjson
  artifacts/
  eval/
```

## 5.1 Required manifest fields

```json
{
  "run_id": "run_...",
  "task_id": "task_...",
  "project_id": "project_...",
  "campaign_id": "campaign_..." ,
  "driver": "codex",
  "driver_mode": "app_server",
  "sandbox_backend": "podman",
  "sandbox_profile": "workspace-default",
  "workspace": {
    "repo_root": "/repo",
    "worktree_path": "/repo/.hive/worktrees/run_...",
    "base_branch": "main"
  },
  "compiled_context_manifest": "context/manifest.json",
  "capability_snapshot": "capability-snapshot.json",
  "scheduler_decision": "scheduler/decision.json",
  "retrieval_trace": "retrieval/trace.json"
}
```

## 6. Universal handoff flow

This flow is frozen and shared by all drivers.

1. task selection
2. worktree claim/create
3. compile context
4. build runpack
5. probe driver
6. select sandbox backend
7. materialize projections for the chosen harness
8. launch driver against runpack
9. normalize events
10. broker approvals
11. collect artifacts
12. evaluate
13. promote / escalate / reroute / requeue

The important product decision is that **handoff is always explicit and materialized**. Nothing important is only in memory.

## 7. Codex driver

## 7.1 Modes

Two modes are supported:

- `app_server` — primary interactive mode
- `exec` — batch / CI / non-interactive fallback

### 7.1.1 app_server mode requirements

Use `codex app-server` because it supports:
- JSON-RPC over stdio or websocket
- turn start, steer, interrupt
- structured event streaming (`item/*`, `turn/*`, diff/plan updates)
- approvals for commands and file changes
- skill listing and explicit skill items

### 7.1.2 exec mode requirements

Use `codex exec` when:
- the run is fully non-interactive
- a CI/batch run is needed
- app-server is unavailable
- a run is requeued as batch after an interactive exploration phase

## 7.2 Context projection for Codex

Required outputs in the runpack worktree:
- `AGENTS.md`
- optional `.codex/AGENTS.md` if Hive wants a harness-local shim
- skill bundles or paths referenced in `driver/codex.json`

### 7.2.1 Codex projection rules

- `AGENTS.md` is generated from Hive truth, never hand-edited in the runpack
- skills selected by Hive are attached explicitly using app-server `skill` items
- per-run steering notes are appended as turn input, not mixed into durable repo policy

## 7.3 Codex launch sequence

1. start app-server subprocess
2. send `initialize`
3. confirm probes for skills/review features if used
4. create or resume thread
5. send `turn/start` with:
   - user text
   - explicit skill items
   - per-run cwd/worktree
   - sandbox/approval settings derived from `PROGRAM.md`
6. stream notifications into normalized events
7. on approval request, surface to Hive console/CLI and respond back to app-server
8. on completion, collect:
   - diff
   - transcript
   - final status
   - review artifacts if review mode was invoked
   - token usage if exposed

## 7.4 Codex steering and reroute

### Steering
- use `turn/steer` for in-flight guidance
- use `turn/interrupt` for pause/stop equivalents
- attach structured steering events in Hive before/after the upstream driver call

### Reroute export
Codex must export:
- current transcript
- current plan
- latest diff
- context manifest
- unresolved approvals / pending state if any

## 8. Claude driver

## 8.1 Mode

One primary mode:
- `sdk`

Optional fallback:
- local CLI subprocess only if needed for debugging or last-resort compatibility

## 8.2 Why the SDK is mandatory

The Claude Agent SDK already exposes:
- same tools, agent loop, and context management as Claude Code
- programmable sessions
- interrupts
- permissions
- hooks
- subagents
- response streaming

That makes it the correct integration layer. A CLI wrapper would be a downgrade.

## 8.3 Context projection for Claude

Required outputs:
- `CLAUDE.md`
- `.claude/skills/` for selected skills
- optional `.claude/rules/` or project settings fragments if needed by the integration

### Projection rules

- Hive remains canonical for durable memory and policy
- Claude-local files are generated per run or refreshed from Hive truth
- no durable policy may exist only in `CLAUDE.md`

## 8.4 Claude launch sequence

1. choose/instantiate sandbox backend
2. prepare runpack and worktree
3. open `ClaudeSDKClient`
4. configure:
   - allowed tools
   - permission handler
   - hooks or tool permission bridge
   - worktree cwd
5. send `query()` with compiled instructions and steering context
6. stream `receive_response()` and normalize output into Hive events
7. route permission requests to Hive approvals broker
8. allow `interrupt()` from console/CLI
9. collect transcript, changed files, output summary, and evaluator artifacts

## 8.5 Claude permission model mapping

Hive must map `PROGRAM.md` policy to SDK permission logic.

Examples:
- path denylist -> deny result with `interrupt=True`
- command/network allowlist -> allow / deny / escalate to approval
- destructive writes -> always route through approvals broker unless explicitly pre-approved

## 8.6 Claude reroute export

Must export:
- session transcript
- last response summary
- outstanding tool state if recoverable
- selected skills
- context manifest
- changed files / patch if any

## 9. Pi driver

## 9.1 Mode

Primary mode:
- `rpc`

Later possible mode:
- direct SDK embedding

## 9.2 Launch sequence

1. start Pi subprocess in RPC mode or use an SDK wrapper with equivalent semantics
2. send initial runpack-derived instructions
3. parse JSONL records
4. normalize tool/task/status messages into Hive events
5. persist transcript and steering notes
6. terminate or checkpoint explicitly at run end

## 9.3 Scope

Pi is a first-class driver for v2.3, but it is not allowed to delay Codex or Claude depth. The acceptance bar is:
- launch
- event stream
- steer
- interrupt/terminate
- transcript collection
- capability truthfulness

## 10. Manual / staged driver

This driver must be brutally honest.

### Required effective capabilities

```json
{
  "launch_mode": "staged",
  "session_persistence": "none",
  "event_stream": "none",
  "approvals": [],
  "skills": "file_projection",
  "worktrees": "host_managed",
  "subagents": "none",
  "native_sandbox": "none",
  "outer_sandbox_required": true,
  "artifacts": ["runpack"],
  "reroute_export": "none"
}
```

No staged driver may report `streaming`, `resume`, `subagents`, or `scheduled` as effective unless the current environment proves it.

## 11. Normalized event model

All events are append-only JSONL. Required categories:

- `run.created`
- `run.prepared`
- `driver.probed`
- `sandbox.selected`
- `driver.launched`
- `driver.attached`
- `driver.status`
- `driver.output.delta`
- `plan.updated`
- `diff.updated`
- `approval.requested`
- `approval.resolved`
- `steer.requested`
- `steer.applied`
- `interrupt.requested`
- `interrupt.applied`
- `artifact.collected`
- `eval.started`
- `eval.completed`
- `promotion.accepted`
- `promotion.escalated`
- `promotion.rejected`
- `run.completed`

Every event requires:
- `event_id`
- `ts`
- `run_id`
- `project_id`
- `task_id`
- `campaign_id` nullable
- `driver`
- `sandbox_backend` nullable
- `type`
- `payload`

## 12. Sandbox backend interface

```python
class SandboxBackend(Protocol):
    name: str
    def doctor(self) -> SandboxProbe: ...
    def create(self, policy: SandboxPolicy, runpack: RunPack) -> SandboxHandle: ...
    def resume(self, handle: SandboxHandle) -> SandboxHandle: ...
    def exec(self, handle: SandboxHandle, request: ExecRequest) -> ExecResult: ...
    def stream(self, handle: SandboxHandle) -> Iterator[SandboxEvent]: ...
    def snapshot(self, handle: SandboxHandle) -> SnapshotRef | None: ...
    def terminate(self, handle: SandboxHandle) -> Ack: ...
    def collect_artifacts(self, handle: SandboxHandle) -> ArtifactBundle: ...
```

## 13. Sandbox policy schema

```json
{
  "backend": "podman",
  "isolation_class": "container",
  "network": {
    "mode": "deny",
    "allowlist": []
  },
  "mounts": {
    "read_only": [],
    "read_write": ["/repo/.hive/worktrees/run_..."]
  },
  "resources": {
    "cpu": 2,
    "memory_mb": 4096,
    "disk_mb": 8192,
    "wall_clock_sec": 3600
  },
  "env": {
    "inherit": false,
    "allowlist": ["CI", "PYTHONPATH"]
  },
  "snapshot": true,
  "resume": true
}
```

## 13.1 Default policy rules

- network default = deny
- filesystem default = only mounted worktree + run artifact directory + temp
- env inheritance default = off
- no home dir, SSH dir, cloud creds, package-manager creds, or docker socket mounts by default
- every policy exception must be attributable to `PROGRAM.md`, campaign policy, or explicit operator steering

## 14. Sandbox backend choices and required behaviors

## 14.1 Podman backend

Required:
- rootless mode support
- worktree mount
- read-only / read-write mount policy
- network deny / allowlist when possible
- CPU/memory limits
- artifact extraction
- Linux first; macOS and Windows via `podman machine`

## 14.2 Docker rootless backend

Required:
- rootless mode detection
- warning when user is relying on rootful daemon access
- mount/network/resource controls
- compatibility docs for environments where Podman is not preferred

## 14.3 Anthropic sandbox runtime backend

Use for:
- wrapping a subprocess or helper program
- fast local “safer than raw shell” mode
- not as the only security boundary for untrusted long-running code

## 14.4 E2B backend

Required:
- sandbox create/connect
- PTY attach
- pause/resume integration
- timeout mapping
- artifact sync
- policy mapping for environment variables and network expectations

## 14.5 Daytona backend

Required:
- sandbox create from snapshot
- archive/snapshot integration when useful
- Git operations or worktree sync
- network allowlist/deny mapping
- self-host/team docs

## 14.6 Cloudflare backend

Experimental only:
- hidden behind explicit opt-in
- docs must say beta
- must not block release if incomplete

## 15. Driver and sandbox doctor commands

Required CLI:

```bash
hive driver doctor --json
hive sandbox doctor --json
```

Each must show:
- installed/available backends
- declared capabilities
- probed capabilities
- warnings
- blockers
- example policy profile matches

## 16. Required code areas

This spec assumes the repository gains or updates modules roughly in this shape:

```text
src/hive/runtime/
  runpack.py
  capabilities.py
  events.py
  approvals.py
  normalization.py

src/hive/drivers/
  base_v2.py
  codex_appserver.py
  codex_exec.py
  claude_sdk.py
  pi_rpc.py
  manual_stage.py
  local_runner.py

src/hive/sandbox/
  base.py
  podman.py
  docker_rootless.py
  asrt.py
  e2b_backend.py
  daytona_backend.py
  cloudflare_backend.py
```

Names may differ, but responsibilities must not.

## 17. No-shortcuts clause

The coding agent must not satisfy this RFC by:
- merely renaming the current staged harness adapter
- treating capability truthfulness as docs work only
- adding a fake `sandbox_backend` field without actual backend integration
- piping raw driver logs into the console without normalized event mapping

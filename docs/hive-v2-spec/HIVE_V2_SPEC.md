# Hive 2.0 Technical Specification

Status: Proposed  
Date: 2026-03-14  
Audience: Codex implementation team  
Scope: `intertwine/hive-orchestrator` v2

## 1. Executive summary

Hive 2.0 keeps the human-friendly parts of Hive 1.x — `GLOBAL.md`, per-project `AGENCY.md`, Git review, and agent skills — but moves machine state into a structured, Git-friendly substrate under `.hive/`. The result is a hybrid system:

- **Human interface:** `GLOBAL.md`, `AGENCY.md`, `PROGRAM.md`, `AGENTS.md`
- **Machine state:** `.hive/tasks/*.md`, `.hive/runs/*`, `.hive/memory/*`, `.hive/events/*.jsonl`
- **Derived cache:** `.hive/cache/index.sqlite` and search indexes (gitignored)
- **Primary interface:** `hive` CLI with stable JSON output
- **Optional interface:** a thin Code Mode-style adapter (`search`, `execute`) and/or a thin MCP wrapper on top of the CLI/client

Hive 2.0 is intentionally **CLI-first and harness-agnostic**. It should work well with Codex CLI, Claude Code, OpenCode, Pi, Hermes, and future harnesses without forcing Hive to become a monolithic chat runtime.

## 2. Design goals

1. Preserve Markdown/Git readability while making work state queryable and reliable.
2. Introduce stable task IDs, typed dependency edges, and atomic-enough claim semantics.
3. Add observational memory so agents can resume work across sessions.
4. Add `PROGRAM.md` as an executable contract for autonomous work.
5. Add a bounded run engine with evaluator-gated promotion.
6. Avoid MCP/tool bloat by making the core surface small and stable.
7. Prefer direct CLI integration; keep MCP optional and thin.
8. Make every autonomous action observable and reproducible.

## 3. Non-goals

1. Hive 2.0 is **not** a replacement for terminal coding harnesses such as Codex, Claude Code, Pi, or Hermes.
2. Hive 2.0 is **not** a generic hosted agent cloud.
3. Hive 2.0 does **not** try to provide Cloudflare-grade sandbox security in MVP; the interface pattern is adopted first, hardened local isolation comes later.
4. Hive 2.0 does **not** depend on a heavy database as the canonical repo format.
5. Hive 2.0 does **not** use harness-native todo or hidden plan modes as persistent state.

## 4. Core decisions

### D1. CLI-first, JSON-first

The `hive` CLI is the primary stable interface. Every command that agents may use MUST support `--json`. Text output is for humans; JSON output is for harnesses and scripts.

### D2. Optional MCP, not MCP-first

MCP is an adapter, not the core product. If MCP exists, it SHOULD be a thin facade over the CLI/library and SHOULD follow a small-surface Code Mode pattern instead of exposing dozens of narrow tools.

### D3. Structured files are canonical; SQLite is derived

Canonical repo state lives in text files:

- `.hive/tasks/*.md`
- `.hive/runs/**`
- `.hive/memory/**/*.md`
- `.hive/events/*.jsonl`
- `GLOBAL.md`
- `projects/**/AGENCY.md`
- `projects/**/PROGRAM.md`

`index.sqlite` and search indexes are local caches and MUST be gitignored.

### D4. Stable immutable IDs

Every project, task, claim, run, and event gets a stable immutable ID. Display order and hierarchy are derived, not primary.

### D5. Evaluator-gated promotion

A task is not complete because an agent says so. A run is promoted only when required evaluators pass and escalation rules are satisfied.

### D6. Externalized state over hidden harness state

Persistent plans, tasks, and memory live in files Hive controls. We do not rely on harness-local plan modes, hidden subagents, or native todo lists as the source of truth.

### D7. On-demand skills

Skills MUST be small markdown docs loaded on demand, not always injected into the base prompt.

### D8. Execution backend abstraction

The run engine uses an executor interface. MVP ships with `local` and `github-actions` executors; `docker` and `ssh` are planned but not required for first release.

## 5. Repository layout

```text
repo/
  GLOBAL.md
  AGENTS.md                       # compatibility shim for Codex/Pi/Hermes/etc.
  projects/
    <project-slug>/
      AGENCY.md
      PROGRAM.md
  .hive/
    tasks/
      task_<id>.md
    runs/
      run_<id>/
        metadata.json
        plan.md
        plan.json
        patch.diff
        summary.md
        review.md
        command-log.jsonl
        eval/
          unit.json
          lint.json
        logs/
          stdout.txt
          stderr.txt
    memory/
      project/
        observations.md
        reflections.md
        profile.md
        active.md
      transcripts/
        claude/
        codex/
        opencode/
        pi/
        hermes/
    events/
      2026-03-14.jsonl
    cache/                       # gitignored
      index.sqlite
      search/
```

Optional user-global memory root:

```text
$XDG_DATA_HOME/hive/
  global-memory/
    observations.md
    reflections.md
    profile.md
    active.md
```

Repo-local project memory is always supported. User-global memory is optional and can be merged into startup context when present.

## 6. Canonical artifacts

### 6.1 `GLOBAL.md`

Purpose:
- human-readable top-level orientation
- summary of all projects
- generated rollup of project status
- stable entry point for humans and harnesses

Rules:
- human-authored overview sections MUST be preserved
- generated sections MUST be bounded by markers:
  - `<!-- hive:begin projects -->`
  - `<!-- hive:end projects -->`
- generated sections are rewritten by `hive sync projections`

### 6.2 `AGENCY.md`

Purpose:
- narrative project document
- rationale, architecture notes, handoff context
- generated task rollup and recent accepted runs

Rules:
- task checkbox lists are deprecated as canonical state
- generated sections use markers:
  - `<!-- hive:begin task-rollup -->`
  - `<!-- hive:end task-rollup -->`
  - `<!-- hive:begin recent-runs -->`
  - `<!-- hive:end recent-runs -->`
- any human-authored notes outside markers MUST be preserved

### 6.3 `PROGRAM.md`

Purpose:
- machine-operable contract for autonomous work on a project
- budgets, allowlists, evaluators, escalation rules, promotion criteria

`PROGRAM.md` is the equivalent of “research org code” for a project. Humans edit it; runs obey it.

### 6.4 `AGENTS.md`

Purpose:
- compatibility shim for coding harnesses that auto-load `AGENTS.md`
- points harnesses to the Hive CLI and startup context workflow

`AGENTS.md` SHOULD stay short and stable. It is not the place for large project logic.

### 6.5 `.hive/tasks/*.md`

Purpose:
- canonical structured task records
- one file per task to reduce merge conflicts
- machine-readable frontmatter + human-readable notes

### 6.6 `.hive/events/*.jsonl`

Purpose:
- append-only audit log
- observability, metrics, and history
- not the primary current-state store

### 6.7 `.hive/memory/**/*.md`

Purpose:
- project and optional global observational memory
- compact startup profile + active context
- recent observations and durable reflections

### 6.8 `.hive/runs/*`

Purpose:
- immutable run artifacts
- reproducibility, review, telemetry, evaluator history

## 7. IDs and naming

All IDs MUST be immutable and globally unique within a repo.

Recommended format:
- project: `proj_<ulid>`
- task: `task_<ulid>`
- claim: `claim_<ulid>`
- run: `run_<ulid>`
- event: `evt_<ulid>`

Display slugs MAY be derived for readability:
- project display: `obsmem`
- task display: `t-a1b2`
- run display: `r-c3d4`

Hierarchy is derived from `parent_id` and rollout order in projections; it is not encoded into the immutable ID.

## 8. Task model

### 8.1 Task states

Allowed `status` values:

- `proposed`
- `ready`
- `claimed`
- `in_progress`
- `blocked`
- `review`
- `done`
- `archived`

Recommended transitions:

```text
proposed -> ready
ready -> claimed
claimed -> in_progress
in_progress -> review
review -> done
* -> blocked
done -> archived
claimed -> ready         # release / expiry
review -> in_progress    # changes requested
```

### 8.2 Task kinds

Allowed `kind` values:

- `epic`
- `task`
- `bug`
- `spike`
- `chore`
- `review`
- `experiment`

### 8.3 Typed edges

MVP edge types:

- `blocks`
- `parent_of`
- `relates_to`
- `duplicates`
- `supersedes`

Rules:
- `blocks` is directional
- `parent_of` is directional
- `duplicates` and `relates_to` are treated as symmetric in projections
- `supersedes` is directional

### 8.4 Ready detection

A task is `ready` when:

1. `status` is `proposed` or `ready`
2. there is no active non-expired claim by another owner
3. all inbound `blocks` edges come from tasks in `done` or `archived`
4. the task is not marked duplicate/superseded by a newer active task

`hive task ready` returns the ranked ready set.

## 9. Claim model

Claims exist to reduce duplicated work, not to provide hard global locking in Git-only mode.

Task files include:
- `owner`
- `claimed_until`

Claim semantics:
- claim is a lease, not a permanent lock
- claims SHOULD default to 60 minutes for human-attended work and 15–30 minutes for autonomous runs
- claim renewal MUST be explicit
- expired claims become eligible for takeover

Modes:
- `git-only`: best-effort via task file updates
- `coordinator`: stronger lease semantics via optional local/remote coordinator service

The coordinator service is optional. Hive MUST still work without it.

## 10. Task file format

Example canonical task file:

```md
---
id: task_01JQRC7W1M8M6VPK5RNDQ4G7Y9
project_id: proj_01JQRC4VPH6X7GV3N9K8FQAMRF
title: Add Code Mode adapter for Hive
kind: task
status: ready
priority: 1
parent_id: null
owner: null
claimed_until: null
labels:
  - interface
  - codemode
relevant_files:
  - src/hive/codemode.py
  - src/hive/cli.py
acceptance:
  - `hive codemode search` returns API examples and schema docs
  - `hive codemode execute` runs JS in a bounded subprocess
  - direct CLI remains the primary path
edges:
  blocks: []
  relates_to:
    - task_01JQRC9AT8F9S2X4D9BG9P2E8
  duplicates: []
  supersedes: []
created_at: 2026-03-14T14:00:00Z
updated_at: 2026-03-14T14:00:00Z
source:
  imported_from:
    path: projects/hive-v2/AGENCY.md
    line: 37
---

## Summary

Implement the optional Code Mode-style adapter as a thin layer on top of the Hive client.

## Notes

- Direct CLI stays primary.
- No giant MCP tool catalog.

## History

- 2026-03-14 bootstrap imported from v1 planning notes
```

Task parser rules:
- unknown frontmatter keys MUST be preserved round-trip
- body sections MAY be edited by humans or agents
- frontmatter schema MUST be validated before save

## 11. `PROGRAM.md` format

`PROGRAM.md` has two parts:

1. **Frontmatter** for machine-parsable policy
2. **Body** for human guidance and rationale

Example:

```md
---
program_version: 1
mode: workflow
default_executor: local

budgets:
  max_wall_clock_minutes: 45
  max_steps: 50
  max_tokens: 75000
  max_cost_usd: 5.0

paths:
  allow:
    - src/**
    - tests/**
    - docs/**
  deny:
    - secrets/**
    - infra/prod/**
    - migrations/**

commands:
  allow:
    - uv run pytest -q
    - uv run ruff check .
    - uv run mypy src
  deny:
    - rm -rf /
    - terraform apply
    - kubectl apply

evaluators:
  - id: lint
    command: uv run ruff check .
    required: true
  - id: unit
    command: uv run pytest -q
    required: true
  - id: types
    command: uv run mypy src
    required: false

promotion:
  requires_all:
    - lint
    - unit
  review_required_when_paths_match:
    - migrations/**
    - auth/**
    - infra/**
  auto_close_task: false

escalation:
  when_paths_match:
    - migrations/**
    - infra/**
  when_commands_match:
    - "terraform apply"
    - "kubectl apply"
---

# Goal

Ship a thin Code Mode adapter and keep CLI-first ergonomics intact.

# Constraints

- No giant MCP tool catalog.
- Must work with Codex CLI via shell first.
- Must keep existing Hive v1 flows working during migration.

# Reviewer checklist

- JSON outputs are stable.
- Generated sections update cleanly.
- Claims expire correctly.
```

Rules:
- frontmatter MUST be sufficient for automated runs
- body MAY contain higher-level guidance, heuristics, or style notes
- if `PROGRAM.md` is missing, a project can still use manual task tracking, but autonomous runs SHOULD NOT start without a program contract

## 12. Run engine

### 12.1 Run lifecycle

States:
- `planned`
- `running`
- `evaluating`
- `accepted`
- `rejected`
- `escalated`
- `aborted`

Lifecycle:

```text
choose task
-> claim task
-> create run record
-> create branch/worktree
-> assemble context
-> write plan.md
-> execute bounded loop
-> run evaluators
-> write summary/review
-> accept / reject / escalate
-> sync task + projections
-> release claim or keep for follow-up
```

### 12.2 Worktree and branch conventions

Recommended branch name:

```text
hive/<project-slug>/<task-display>/<run-id>
```

Recommended worktree path:

```text
.hive/worktrees/<run-id>/
```

### 12.3 Run artifact contract

Each run directory MUST include:

- `metadata.json`
- `plan.md`
- `plan.json`
- `patch.diff`
- `summary.md`
- `review.md`
- `command-log.jsonl`
- `eval/*.json`
- `logs/stdout.txt`
- `logs/stderr.txt`

If a run touches code, `patch.diff` is required.

### 12.4 Promotion rules

A run MAY be auto-accepted only if:

1. all required evaluators pass
2. touched paths do not trigger mandatory review
3. the run stays within budget
4. `summary.md` exists
5. `review.md` exists
6. no escalation rule fired

Otherwise the run becomes `escalated` or `rejected`.

### 12.5 Keep/discard/promote semantics

- **accept / promote:** result is merged into task history, task may move to `review` or `done`
- **reject / discard:** run artifacts remain, patch is not promoted
- **escalate:** task stays active but requires human review or explicit follow-up

## 13. Memory plane

Hive 2.0 adopts an observational memory pattern.

### 13.1 Memory tiers

Project-local tiers:

1. `observations.md` — recent compressed notes
2. `reflections.md` — durable long-term project memory
3. `profile.md` — compact stable startup profile
4. `active.md` — compact active context

Optional user-global tiers mirror the same files in `$XDG_DATA_HOME/hive/global-memory/`.

### 13.2 Sources

Transcript adapters SHOULD support:

- Claude Code session start/end hooks
- Codex CLI transcript scanning / cron
- OpenCode transcript ingestion
- Pi transcript/session ingestion
- Hermes transcript/session ingestion

### 13.3 Memory jobs

#### Observer

Input:
- new transcript chunks
- recent run summaries
- recent task changes

Output:
- append compressed entries to `observations.md`

#### Reflector

Input:
- observations since last reflection timestamp

Output:
- regenerate or update `reflections.md`
- regenerate `profile.md`
- regenerate `active.md`

### 13.4 Search backends

MVP backend interface:

- `bm25` (default)
- `qmd` (optional)
- `qmd-hybrid` (optional)
- `none`

Search targets:
- project memory docs
- optional user-global memory docs
- task summaries
- accepted run summaries

### 13.5 Startup context assembly

`hive context startup --project <id>` SHOULD assemble context in this order:

1. `AGENTS.md` shim instructions
2. project summary from `AGENCY.md`
3. key sections from `PROGRAM.md`
4. project `profile.md`
5. project `active.md`
6. top memory search hits for the current task or query
7. recent accepted run summaries
8. optional user-global `profile.md` / `active.md`

Profiles:
- `light`: ~2k tokens
- `default`: ~4k tokens
- `deep`: ~8k tokens

## 14. Scheduler

### 14.1 MVP ranking

MVP scoring SHOULD be deterministic and simple:

```text
score =
  priority_weight
+ age_weight
+ downstream_unblock_weight
+ continuity_bonus
- risk_penalty
```

Default sort:
1. higher explicit priority first
2. older ready tasks first
3. tasks that unblock more downstream work first
4. continuity bonus for the currently active project

### 14.2 Advanced portfolio mode

A later mode MAY support:
- exploitation branch continuation
- exploration branches
- periodic reviewer pass
- memory-aware ranking

Portfolio mode is not required for MVP.

## 15. CLI specification

Core command groups:

```text
hive init
hive doctor

hive project list
hive project show <project-id>
hive project sync [<path>]

hive task list
hive task show <task-id>
hive task create
hive task update <task-id>
hive task claim <task-id>
hive task release <task-id>
hive task link <src-id> <edge-type> <dst-id>
hive task ready

hive run start <task-id>
hive run show <run-id>
hive run eval <run-id>
hive run accept <run-id>
hive run reject <run-id>
hive run escalate <run-id>

hive memory observe
hive memory reflect
hive memory search "<query>"
hive context startup --project <project-id>
hive context handoff --project <project-id>

hive sync projections
hive migrate v1-to-v2
```

All agent-facing commands MUST support `--json`.

### 15.1 Example JSON output: `hive task ready --json`

```json
{
  "version": "2.0",
  "generated_at": "2026-03-14T15:00:00Z",
  "tasks": [
    {
      "id": "task_01JQRC7W1M8M6VPK5RNDQ4G7Y9",
      "project_id": "proj_01JQRC4VPH6X7GV3N9K8FQAMRF",
      "title": "Add Code Mode adapter for Hive",
      "status": "ready",
      "priority": 1,
      "owner": null,
      "blocked_by": [],
      "score": 14.2
    }
  ]
}
```

## 16. Code Mode / optional MCP interface

### 16.1 Positioning

Hive 2.0 uses:
- **direct CLI first**
- **thin Code Mode adapter second**
- **thin MCP wrapper only if a harness requires MCP**

### 16.2 Tool surface

If implemented as Code Mode/MCP, expose exactly two tools:

#### `search`

Purpose:
- search the Hive API, command help, schemas, examples, current workspace graph summary, and memory/query surfaces

Input:
```json
{
  "query": "find how to claim a task and start a run",
  "scopes": ["api", "examples", "project"],
  "limit": 8
}
```

Output:
```json
{
  "results": [
    {
      "kind": "command",
      "title": "hive task claim",
      "summary": "Claim a task lease with optional TTL",
      "example": "hive task claim task_... --owner codex --ttl-minutes 30 --json"
    }
  ]
}
```

#### `execute`

Purpose:
- execute JS/TS or Python against a typed local Hive client

Input:
```json
{
  "language": "ts",
  "profile": "default",
  "code": "export default async (hive) => { const ready = await hive.task.ready({limit: 1}); return ready; }"
}
```

Output:
```json
{
  "ok": true,
  "value": { "...": "..." },
  "stdout": "",
  "stderr": ""
}
```

### 16.3 Client surface inside `execute`

Expose a typed `hive` object with modules:

- `project`
- `task`
- `run`
- `memory`
- `context`
- `scheduler`

Example methods:
- `hive.task.list()`
- `hive.task.show({ id })`
- `hive.task.claim({ id, owner, ttlMinutes })`
- `hive.task.update({ id, patch })`
- `hive.task.link({ srcId, edgeType, dstId })`
- `hive.run.start({ taskId })`
- `hive.run.eval({ runId })`
- `hive.memory.search({ query, scope })`
- `hive.context.startup({ projectId, profile })`

### 16.4 Sandboxing

MVP local `execute` SHOULD use:
- bounded subprocess
- no inherited secrets except explicit allowlist
- timeout
- working directory allowlist
- best-effort network denial

Future hardening MAY use:
- `bubblewrap`
- `nsjail`
- Docker/OCI
- remote isolated executor

Important: MVP adopts the **interface pattern** first. It does not claim Cloudflare-level isolation locally.

## 17. Skills model

Skills MUST be markdown documents that can be injected on demand.

Recommended initial skills:
- `hive-core.md`
- `hive-memory.md`
- `hive-runner.md`
- `hive-reviewer.md`
- `hive-codemode.md`

Rules:
- do not inject all skills by default
- load by explicit agent choice or harness workflow
- skills SHOULD reference CLI commands first, code mode second

## 18. Harness compatibility

### 18.1 Codex CLI

Preferred integration:
- shell out to `hive ... --json`
- load `AGENTS.md`
- optionally use transcript polling for memory observe

### 18.2 Claude Code

Preferred integration:
- `SessionStart` hook calls `hive context startup`
- `SessionEnd` hook calls `hive memory observe`

### 18.3 OpenCode

Preferred integration:
- use same CLI and skills
- optional MCP wrapper if desired

### 18.4 Pi

Pi integration SHOULD stay simple:
- use shell commands
- use `AGENTS.md`
- keep persistent plan/task state in Hive files, not harness-native todos or plan mode

### 18.5 Hermes

Hermes integration SHOULD leverage:
- `AGENTS.md` compatibility
- memory import/export hooks
- on-demand skills
- optional cron to run `hive memory reflect` and `hive scheduler tick`

## 19. Projection rules

`hive sync projections` updates:

- generated project list in `GLOBAL.md`
- generated task rollup in `AGENCY.md`
- recent run rollup in `AGENCY.md`
- optional root `AGENTS.md` compatibility text

Projection rules:
- preserve human-authored content outside markers
- rewrite only marked regions
- sort tasks by status and priority
- include stable IDs in generated rollups

## 20. Migration from Hive 1.x

MVP migration command:

```text
hive migrate v1-to-v2
```

Behavior:
1. scan existing `GLOBAL.md` and `projects/**/AGENCY.md`
2. create project IDs
3. parse legacy checkbox tasks into `.hive/tasks/*.md`
4. preserve imported source path/line
5. create default `PROGRAM.md` stubs where missing
6. add generated markers to `GLOBAL.md` and `AGENCY.md`
7. create `AGENTS.md` shim
8. create bootstrap event log
9. build local cache

Migration MUST be reversible at the Git level. Do not delete legacy sections unless `--rewrite` is explicitly passed.

## 21. Telemetry and observability

Hive 2.0 MUST emit structured events for:

- task create/update/claim/release
- run start/eval/accept/reject/escalate
- memory observe/reflect
- projection sync
- migration actions

Default sink:
- `.hive/events/*.jsonl`

Optional sinks:
- Weave
- OpenTelemetry
- custom webhooks

Key metrics:
- ready-to-claim latency
- claim conflict rate
- evaluator pass rate
- accepted vs rejected runs
- memory search hit rate
- startup context size
- time from claim to promoted result

## 22. Testing requirements

### 22.1 Unit tests

Required:
- task file round-trip parse/write
- ready detection
- edge handling
- claim expiry
- `PROGRAM.md` validation
- run state transitions
- memory context assembly

### 22.2 Integration tests

Required:
- migrate a sample Hive 1.x project
- start a run from a ready task
- execute evaluators
- update projections
- observe and reflect a sample transcript
- query memory search
- produce stable JSON outputs

### 22.3 Golden tests

Required:
- `GLOBAL.md` generated section output
- `AGENCY.md` generated task rollup
- `AGENTS.md` shim
- startup context bundles
- sample task file serialization

## 23. Recommended implementation order

1. storage + parser + task file schema
2. CLI scaffolding with JSON outputs
3. projection sync for `GLOBAL.md` / `AGENCY.md`
4. `PROGRAM.md` parser + evaluator engine
5. run engine + worktree management
6. memory observe/reflect/search
7. migration tool
8. optional code mode adapter
9. optional thin MCP wrapper
10. optional coordinator upgrade

## 24. Opinionated calls

1. **Do not make MCP the center of the product.**
2. **Do not make SQLite the canonical repo format.**
3. **Do not keep checkbox lines in `AGENCY.md` as the machine task database.**
4. **Do not depend on hidden harness-native planning/todo features.**
5. **Do reuse as much of `observational-memory` as possible instead of rewriting it.**
6. **Do treat Cloudflare-style Code Mode as an adapter pattern, not as permission to reintroduce a huge tool surface.**
7. **Do bias toward a tiny stable CLI + skill docs.**
8. **Do keep every autonomous run inspectable by humans.**

## 25. Deferred ideas (post-MVP)

- automatic skill extraction from repeated accepted runs
- portfolio scheduler with exploit/explore balancing
- docker/ssh executors
- stronger local sandboxing for `execute`
- multi-repo swarm scheduling
- richer graph analytics and dashboards

## 26. References

Primary inspirations and adjacent systems:

- Hive v1: https://github.com/intertwine/hive-orchestrator
- Observational Memory: https://github.com/intertwine/observational-memory
- Beads: https://github.com/steveyegge/beads
- autoresearch: https://github.com/karpathy/autoresearch
- Cloudflare Code Mode: https://blog.cloudflare.com/code-mode/
- Cloudflare Code Mode MCP: https://blog.cloudflare.com/code-mode-mcp/
- Cloudflare MCP server: https://github.com/cloudflare/mcp
- Cloudflare Agents Code Mode docs: https://developers.cloudflare.com/agents/api-reference/codemode/
- Pi coding agent essay: https://mariozechner.at/posts/2025-11-30-pi-coding-agent/
- Hermes Agent docs: https://hermes-agent.nousresearch.com/docs/
- Hermes Agent repo: https://github.com/NousResearch/hermes-agent

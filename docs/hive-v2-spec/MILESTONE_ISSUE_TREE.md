# Hive 2.0 Milestone Issue Tree

Status: Proposed  
Audience: Codex implementation team  
Legend:
- **Epic** = large track
- **Issue** = implementable unit
- Priority: P0 / P1 / P2
- Size: S / M / L

## Milestone 0 — bootstrap and architecture guardrails

### Epic M0.1 — repo scaffolding and ADRs
Goal: establish the structure so all later work lands consistently.

#### Issue M0.1.1 — add `.hive/` directory conventions
- Priority: P0
- Size: S
- Deliverables:
  - `.hive/README.md`
  - `.gitignore` entries for `.hive/cache/` and worktrees
  - directory creation helpers
- Acceptance:
  - `hive init` produces the expected layout

#### Issue M0.1.2 — add architecture decision records
- Priority: P1
- Size: S
- Deliverables:
  - ADR for CLI-first
  - ADR for structured file canonical state
  - ADR for optional Code Mode / MCP
- Acceptance:
  - ADRs match the v2 spec and are linked from docs

---

## Milestone 1 — structured graph substrate

### Epic M1.1 — canonical task file store
Goal: replace checkbox lists as machine state.

#### Issue M1.1.1 — task frontmatter schema + parser
- Priority: P0
- Size: M
- Deliverables:
  - parser/serializer for `.hive/tasks/*.md`
  - strict validation with round-trip preservation of unknown keys
- Acceptance:
  - golden tests pass on sample tasks
  - unknown frontmatter survives load/save

#### Issue M1.1.2 — stable ID generation
- Priority: P0
- Size: S
- Deliverables:
  - ULID-based IDs for project/task/run/event/claim
- Acceptance:
  - IDs are stable and lexically sortable
  - no collisions in tests

#### Issue M1.1.3 — edge model
- Priority: P0
- Size: M
- Deliverables:
  - typed edges: `blocks`, `parent_of`, `relates_to`, `duplicates`, `supersedes`
- Acceptance:
  - ready detection tests include blocker handling
  - symmetric vs directional edge rules are explicit

#### Issue M1.1.4 — ready detection engine
- Priority: P0
- Size: M
- Deliverables:
  - task graph traversal and ready ranking
- Acceptance:
  - `hive task ready --json` returns correct results on fixture graphs

### Epic M1.2 — derived cache
Goal: make structured files queryable without making SQLite canonical.

#### Issue M1.2.1 — `index.sqlite` builder
- Priority: P0
- Size: M
- Deliverables:
  - build/rebuild cache from canonical files
  - FTS indexing hooks
- Acceptance:
  - deleting cache and rebuilding produces the same query results

#### Issue M1.2.2 — search index targets
- Priority: P1
- Size: M
- Deliverables:
  - index task summaries
  - index accepted run summaries
  - index memory docs
  - index `PROGRAM.md` / `AGENCY.md` snippets
- Acceptance:
  - `hive search` returns hits from each source type

### Epic M1.3 — projection sync
Goal: keep docs readable while machine state moves elsewhere.

#### Issue M1.3.1 — `GLOBAL.md` project rollup generation
- Priority: P0
- Size: S
- Acceptance:
  - generated region updates without clobbering human text

#### Issue M1.3.2 — `AGENCY.md` task rollup generation
- Priority: P0
- Size: M
- Acceptance:
  - task rollup shows ID, status, priority, owner, blockers
  - updates are stable under repeated sync

#### Issue M1.3.3 — root `AGENTS.md` compatibility shim
- Priority: P1
- Size: S
- Acceptance:
  - generated or appended Hive section is bounded by markers
  - does not overwrite unrelated instructions

---

## Milestone 2 — CLI and JSON surface

### Epic M2.1 — core CLI
Goal: make CLI the primary agent interface.

#### Issue M2.1.1 — `hive init`, `hive doctor`
- Priority: P0
- Size: S

#### Issue M2.1.2 — `hive project *`
- Priority: P0
- Size: M

#### Issue M2.1.3 — `hive task *`
- Priority: P0
- Size: L
- Commands:
  - list
  - show
  - create
  - update
  - claim
  - release
  - link
  - ready

#### Issue M2.1.4 — stable JSON outputs
- Priority: P0
- Size: M
- Acceptance:
  - schema snapshots for each JSON-producing command
  - version field included

### Epic M2.2 — claim semantics
Goal: reduce duplicate work.

#### Issue M2.2.1 — local lease handling
- Priority: P0
- Size: M
- Acceptance:
  - claims expire correctly
  - release works
  - task status syncs with claim state

#### Issue M2.2.2 — optional coordinator upgrade path
- Priority: P2
- Size: M
- Acceptance:
  - local coordinator can be plugged in without changing canonical files

---

## Milestone 3 — `PROGRAM.md` and run engine

### Epic M3.1 — `PROGRAM.md` parser and validator
Goal: create a machine-operable project contract.

#### Issue M3.1.1 — frontmatter schema
- Priority: P0
- Size: M
- Fields:
  - budgets
  - paths
  - commands
  - evaluators
  - promotion
  - escalation

#### Issue M3.1.2 — default stub generator
- Priority: P1
- Size: S

### Epic M3.2 — worktree-backed runs
Goal: support bounded autonomous execution.

#### Issue M3.2.1 — run record creation
- Priority: P0
- Size: M

#### Issue M3.2.2 — worktree/branch management
- Priority: P0
- Size: M

#### Issue M3.2.3 — command log and patch capture
- Priority: P0
- Size: M

#### Issue M3.2.4 — run artifact writer
- Priority: P0
- Size: M
- Acceptance:
  - `metadata.json`, `plan.md`, `summary.md`, `review.md`, `patch.diff` exist

### Epic M3.3 — evaluator engine
Goal: gate promotion on measurable outcomes.

#### Issue M3.3.1 — evaluator runner
- Priority: P0
- Size: M

#### Issue M3.3.2 — evaluator result schema
- Priority: P0
- Size: S

#### Issue M3.3.3 — promotion decision engine
- Priority: P0
- Size: M
- Acceptance:
  - required evaluators enforced
  - escalation path rules enforced

---

## Milestone 4 — observational memory plane

### Epic M4.1 — transcript ingestion
Goal: collect raw material for memory.

#### Issue M4.1.1 — Claude Code adapter
- Priority: P0
- Size: M
- Acceptance:
  - startup context hook works
  - session-end observe works

#### Issue M4.1.2 — Codex adapter
- Priority: P0
- Size: M
- Acceptance:
  - AGENTS integration works
  - cron/polling observe path works

#### Issue M4.1.3 — OpenCode adapter
- Priority: P1
- Size: M

#### Issue M4.1.4 — Pi adapter
- Priority: P1
- Size: S
- Acceptance:
  - shell + AGENTS path documented and tested

#### Issue M4.1.5 — Hermes adapter
- Priority: P1
- Size: S
- Acceptance:
  - AGENTS + cron/skill loading path documented and tested

### Epic M4.2 — observer/reflector jobs
Goal: compress transcripts into durable memory.

#### Issue M4.2.1 — observer job
- Priority: P0
- Size: M

#### Issue M4.2.2 — reflector job
- Priority: P0
- Size: M

#### Issue M4.2.3 — profile/active regeneration
- Priority: P0
- Size: S

### Epic M4.3 — search and context assembly
Goal: make memory usable at session start and during work.

#### Issue M4.3.1 — default BM25 backend
- Priority: P0
- Size: M

#### Issue M4.3.2 — optional QMD backend adapter
- Priority: P1
- Size: M

#### Issue M4.3.3 — `hive context startup`
- Priority: P0
- Size: M

#### Issue M4.3.4 — `hive memory search`
- Priority: P0
- Size: S

---

## Milestone 5 — Code Mode adapter and optional MCP

### Epic M5.1 — Code Mode adapter
Goal: adopt the small-surface search/execute pattern.

#### Issue M5.1.1 — API search surface
- Priority: P1
- Size: M
- Acceptance:
  - searches CLI docs, schema docs, examples, current workspace graph summary

#### Issue M5.1.2 — typed local client for execute
- Priority: P1
- Size: M
- Acceptance:
  - `project`, `task`, `run`, `memory`, `context`, `scheduler` modules exposed

#### Issue M5.1.3 — bounded execute sandbox
- Priority: P1
- Size: M
- Acceptance:
  - timeouts
  - environment scrubbing
  - working-dir allowlist
  - best-effort network denial

### Epic M5.2 — thin MCP wrapper
Goal: support MCP-required harnesses without tool bloat.

#### Issue M5.2.1 — two-tool MCP server
- Priority: P2
- Size: M
- Tools:
  - `search`
  - `execute`

#### Issue M5.2.2 — skills for Code Mode usage
- Priority: P1
- Size: S

---

## Milestone 6 — migration and compatibility

### Epic M6.1 — v1 importer
Goal: move existing repos onto the new substrate.

#### Issue M6.1.1 — parse legacy checklists
- Priority: P0
- Size: M

#### Issue M6.1.2 — infer hierarchy and basic blockers
- Priority: P0
- Size: M

#### Issue M6.1.3 — write bootstrap task files and events
- Priority: P0
- Size: M

#### Issue M6.1.4 — write `PROGRAM.md` stubs
- Priority: P1
- Size: S

### Epic M6.2 — shadow mode
Goal: allow gradual adoption.

#### Issue M6.2.1 — preserve legacy sections
- Priority: P0
- Size: S

#### Issue M6.2.2 — `--rewrite` cleanup mode
- Priority: P1
- Size: S

---

## Milestone 7 — telemetry, docs, and hardening

### Epic M7.1 — events and metrics
Goal: make behavior observable.

#### Issue M7.1.1 — structured JSONL event writer
- Priority: P0
- Size: S

#### Issue M7.1.2 — key metrics calculator
- Priority: P1
- Size: M

#### Issue M7.1.3 — optional Weave/OpenTelemetry exporters
- Priority: P2
- Size: M

### Epic M7.2 — docs and examples
Goal: make the new model learnable.

#### Issue M7.2.1 — end-to-end demo project
- Priority: P0
- Size: S

#### Issue M7.2.2 — examples for AGENCY / PROGRAM / task files
- Priority: P0
- Size: S

#### Issue M7.2.3 — harness recipes (Codex, Claude, OpenCode, Pi, Hermes)
- Priority: P1
- Size: M

### Epic M7.3 — post-MVP experiments
Goal: evaluate compounding behaviors.

#### Issue M7.3.1 — skill extraction from accepted runs
- Priority: P2
- Size: M

#### Issue M7.3.2 — exploit/explore portfolio scheduler
- Priority: P2
- Size: M

#### Issue M7.3.3 — docker / ssh executors
- Priority: P2
- Size: L

---

## Suggested first implementation slice

If Codex only does one vertical slice first, do this:

1. parse/write task files
2. `hive task list/show/create/update/ready --json`
3. projection sync for `AGENCY.md`
4. `PROGRAM.md` parser
5. `hive run start/eval/accept`
6. memory observer + startup context for one harness (Claude Code or Codex)
7. migration command for one sample project

That slice is already enough to prove the architecture.

## Done definition for Hive 2.0 MVP

Hive 2.0 MVP is done when:

1. structured task files are canonical
2. CLI JSON surface is stable
3. `PROGRAM.md` drives evaluator-gated runs
4. memory observe/reflect/search works for at least Claude Code and Codex
5. migration from a v1 repo works
6. `AGENCY.md` and `GLOBAL.md` remain readable
7. optional Code Mode search/execute exists or is cleanly staged behind a feature flag

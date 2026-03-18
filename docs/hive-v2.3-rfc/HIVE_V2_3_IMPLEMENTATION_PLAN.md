# Agent Hive v2.3 Implementation Plan

Status: Proposed  
Date: 2026-03-17

## 1. Overall approach

This is a **completion release**, not a rewrite.

The coding agent should preserve the existing v2.2.1 substrate and implement the missing product depth in a controlled sequence. The goal is to maximize shipped value while minimizing churn in stable user-facing concepts.

## 2. Order of work

The implementation order is frozen.

## Milestone 0 — Contract freeze and scaffolding

### Deliverables
- `DriverV2` interface
- `SandboxBackend` interface
- `CapabilitySnapshot` model
- `RunPack` model
- normalized event enum/types
- `driver doctor` and `sandbox doctor` skeletons
- feature flags or config surface if needed for safe rollout

### Code areas
- `src/hive/runtime/`
- `src/hive/drivers/`
- `src/hive/sandbox/`
- CLI command registration
- model/schema fixtures in tests

### Exit criteria
- all schemas have fixtures
- no v2.3 code relies on the old flat capability model
- old driver helpers can coexist behind a compatibility layer during migration

## Milestone 1 — Capability truthfulness

### Deliverables
- runtime capability probe pipeline
- `declared/probed/effective/evidence` snapshots persisted per run
- console capability inspector
- doctors show warnings and blockers
- current staged harness adapters downgraded to truthful effective capabilities

### Required fixes
- remove optimistic capability inflation from staged harnesses
- make the console and CLI use `effective`, not `declared`, for operator affordances

### Exit criteria
- a staged driver cannot surface streaming/resume controls in the UI unless probe + effective say yes
- doctor output is accurate enough to diagnose missing app-server/SDK dependencies

## Milestone 2 — Deep Codex driver

### Deliverables
- `codex_appserver` driver
- `codex_exec` driver
- approval bridge for command/file/network requests
- skill attachment support
- turn steer / interrupt support
- transcript, diff, and review artifact collection
- Codex capability probes

### Code areas
- `src/hive/drivers/codex_appserver.py`
- `src/hive/drivers/codex_exec.py`
- approval broker / event normalization
- Codex-specific projection builder
- run detail console page

### Exit criteria
- same task launches and completes via Codex app-server
- approvals appear in Hive inbox and route back upstream
- rerun/batch fallback via `codex exec` works
- transcripts and diffs land in standard runpack locations

## Milestone 3 — Deep Claude driver

### Deliverables
- `claude_sdk` driver
- permission bridge using SDK handlers
- interrupt support
- session reuse where appropriate
- `CLAUDE.md` and `.claude/skills/` projection
- transcript and artifact normalization

### Code areas
- `src/hive/drivers/claude_sdk.py`
- context compiler / projection layer
- approval broker adapters
- console driver-specific details

### Exit criteria
- same task launches and completes via Claude SDK
- interrupts work from CLI and console
- permission prompts round-trip through Hive
- session continuity is visible in run detail

## Milestone 4 — Pi driver and honest manual stage

### Deliverables
- `pi_rpc` driver
- normalized JSONL event ingestion
- honest manual/staged driver rewrite
- capability fixtures for both

### Exit criteria
- Pi launches through RPC
- manual/staged driver no longer overclaims capabilities
- run board can show all four driver families with consistent lifecycle states

## Milestone 5 — Sandbox backends

### Deliverables
- `podman` backend
- `docker_rootless` backend
- `asrt` process wrapper backend
- `e2b_backend`
- `daytona_backend`
- optional `cloudflare_backend` marked experimental
- sandbox policy model
- sandbox doctor and console backend display
- mount/network/env/resource enforcement adapters

### Required policy profiles

#### `local-safe`
- podman default
- network deny
- worktree rw only
- no env inheritance

#### `local-fast`
- ASRT or local container depending availability
- reduced cold-start expectations
- still denies broad ambient access

#### `hosted-managed`
- E2B
- persistent sessions enabled
- explicit timeout mapping

#### `team-self-hosted`
- Daytona
- snapshot-based environments
- org-level network restrictions when available

### Exit criteria
- at least one safe local backend works across macOS/Linux/Windows/WSL through documented paths
- at least one managed hosted backend works
- at least one self-hosted backend works
- every run records sandbox backend, policy, and any violations

## Milestone 6 — Hybrid retrieval

### Deliverables
- SQLite FTS5 lexical index
- LanceDB dense index
- FastEmbed embedding pipeline
- FastEmbed reranking on top-k candidates
- retrieval explanations
- retrieval traces
- installed-package docs/recipes indexing validation
- optional Qdrant backend abstraction

### Code areas
- `src/hive/retrieval/`
- `src/hive/search/` or existing search layer
- packaging (`pyproject.toml`)
- console retrieval inspector
- benchmark fixtures

### Exit criteria
- `hive search` is meaningfully better on installed package than today
- retrieval inspector exists
- canonical docs outrank projections
- traces are stored for every context compilation

## Milestone 7 — Campaign scheduler completion

### Deliverables
- campaign type templates
- lane model
- weighted candidate scoring
- decision logging
- brief generator upgrade
- campaign inspector in console
- operator steering for lane and driver preference

### Code areas
- `src/hive/control/campaigns.py` or successor
- decision logging models
- brief generation
- console campaign views

### Exit criteria
- delivery and research campaigns behave differently
- scheduler decisions are inspectable
- duplicate overlap penalties prevent obviously redundant launches
- campaign briefs explain recommendations

## Milestone 8 — Console completion and docs polish

### Deliverables
- capability inspector
- approvals inbox polish
- run detail with retrieval and sandbox panes
- campaign board
- truthful compare-harness docs
- sandbox docs
- operator docs
- release demo flow
- package extras and installation docs updated

### Exit criteria
- a new user can understand what is happening without inspecting raw markdown
- docs match actual driver and sandbox depth
- screenshots/demo reflect the final product story

## 3. Repository/code map for the coding agent

This is a suggested map. Exact names may differ, but responsibilities should remain recognizable.

```text
src/hive/runtime/
  runpack.py
  capabilities.py
  events.py
  approvals.py
  selection.py

src/hive/drivers/
  base_v2.py
  codex_appserver.py
  codex_exec.py
  claude_sdk.py
  pi_rpc.py
  manual_stage.py
  local_runner.py
  registry.py
  doctor.py

src/hive/sandbox/
  base.py
  policy.py
  podman.py
  docker_rootless.py
  asrt.py
  e2b_backend.py
  daytona_backend.py
  cloudflare_backend.py
  doctor.py

src/hive/retrieval/
  chunkers.py
  index_sqlite.py
  index_lance.py
  embed.py
  rerank.py
  fusion.py
  traces.py
  bench.py

src/hive/control/
  campaigns_v2.py
  scoring.py
  briefs.py

src/hive/console/
  api/
  components/
  pages/
    inbox
    run-detail
    campaigns
    capabilities
    retrieval
    sandboxes

docs/
  RUNTIME_DRIVERS.md
  SANDBOXES.md
  HYBRID_RETRIEVAL.md
  CAMPAIGNS.md
  OPERATOR_STEERING.md
  COMPARE_HARNESSES.md
```

## 4. Packaging changes

The package should add optional extras like:

- `drivers-codex`
- `drivers-claude`
- `drivers-pi`
- `sandbox-e2b`
- `sandbox-daytona`
- `retrieval`
- `console`
- `full`

`full` should remain optional so the base CLI stays light.

## 5. CI and fixture strategy

## 5.1 Driver conformance fixtures

Create a shared fixture contract:
- probe
- prepare runpack
- launch
- status
- stream events
- approvals
- interrupt
- collect artifacts

Use mocks where upstream services are unavailable, but require at least one real integration smoke path per major driver in nightly or opt-in CI.

## 5.2 Sandbox conformance fixtures

Verify:
- mount policy
- env policy
- network deny
- network allowlist
- artifact collection
- timeout enforcement
- snapshot/resume where supported

## 5.3 Retrieval benchmarks

Add a small benchmark dataset with:
- policy questions
- task lookup questions
- history questions
- skill discovery questions
- multi-project ambiguity cases

Track:
- top-1 accuracy
- top-3 hit rate
- duplicate-hit rate
- canonical-over-projection success rate

## 5.4 Campaign simulation tests

Use fixture workspaces to test:
- delivery vs research behavior
- overlap penalties
- review lane prioritization
- cost-constrained launch choices

## 6. Migration and rollout

## 6.1 User-facing rollout

- preserve current CLI nouns where possible
- add new inspect/doctor commands rather than renaming stable commands unnecessarily
- introduce deep drivers as preferred paths without breaking existing manual workflows

## 6.2 Internal rollout

Suggested feature flags during implementation:
- `hive.runtime_v2`
- `hive.hybrid_retrieval_v2`
- `hive.campaigns_v2`
- `hive.sandbox_v2`

These may be removed before release once stable.

## 6.3 Backward compatibility

- old runs remain readable
- missing capability snapshot in old runs should render as `legacy`
- campaign decisions missing lane data should still display with graceful fallback
- manual/staged flows should remain supported, just more honest

## 7. Release recommendation

Do not tag v2.3 until:
- Codex and Claude deep drivers are real
- one local, one managed, and one self-hosted sandbox path are real
- retrieval inspector and capability inspector are present
- campaign decision logging is present
- docs and screenshots match the actual product

## 8. What the coding agent must optimize for

1. **Truthfulness over breadth**
2. **Durable artifacts over hidden state**
3. **Operator trust over flashy demos**
4. **Backtestability over hand-wavy “smartness”**
5. **Cross-platform realism over perfect theoretical elegance**

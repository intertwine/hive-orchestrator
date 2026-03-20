# Agent Hive v2.3 RFC — Completing the World-Class Observe-and-Steer Vision

Status: Historical design reference  
Date: 2026-03-17  
Audience: product, engineering, docs, release, design  
Applies to: `intertwine/hive-orchestrator` / package `mellona-hive` / product `Agent Hive`

Current scoped release truth lives in `docs/V2_3_STATUS.md`. This RFC remains packaged and searchable as the broader
design bundle, including ideas later narrowed or deferred for the actual v2.3 release.

## 1. Executive summary

Agent Hive 2.2.1 proved that the v2 substrate is real. The repo now clearly presents Hive as a repo-native control plane above Codex, Claude Code, and local/manual loops, with canonical task state under `.hive/`, human-readable `AGENCY.md`, policy in `PROGRAM.md`, and a CLI-first manager loop.(Source 1)

The remaining gap is **not** architectural foundation. The remaining gap is **runtime depth and product polish**:

- external harnesses are still too staged instead of deeply driven
- capability reporting is not yet fully truthful
- campaigns are still simpler than the intended portfolio-control model
- retrieval is better than v1 but not yet explainable hybrid search
- `execute` is explicitly not a hardened sandbox today(Source 1)
- the console is strong enough to be useful, but not yet the obvious best-in-class command center

v2.3 is the release that closes that gap.

This RFC makes the hard calls needed to finish Hive 2.2 as a marketable, durable product:

1. **Deep runtime drivers**
   - Codex primary integration: `codex app-server`
   - Codex batch fallback: `codex exec`
   - Claude primary integration: `claude-agent-sdk` / `ClaudeSDKClient`
   - Pi primary integration: JSONL RPC
   - everything else remains honestly staged until deep adapters exist

2. **Truthful capability snapshots**
   - no more flat booleans as the whole truth
   - every run records `declared`, `probed`, and `effective` capabilities with evidence

3. **Policy-driven campaign orchestration**
   - campaigns become lane-based portfolios (`exploit`, `explore`, `review`, `maintenance`)
   - Hive logs why it launched a run, not just what it launched

4. **Hybrid semantic retrieval**
   - local default: SQLite FTS5 + LanceDB dense vectors + FastEmbed embeddings/reranking
   - remote/team option: Qdrant hybrid backend
   - every retrieval step becomes inspectable and backtestable

5. **Real sandboxing**
   - local default: rootless Podman
   - local alternative: Docker rootless
   - fast process wrapper: Anthropic sandbox runtime
   - managed hosted default: E2B
   - self-hosted/team default: Daytona
   - Cloudflare Sandbox stays experimental
   - no first-party Firecracker runtime in v2.3

The product line stays the same:

> **Keep your favorite worker harness. Hive is the observe-and-steer control plane above it.**

## 2. Current-state diagnosis

Hive 2.2.1 already has the right center of gravity:

- canonical task state lives under `.hive/tasks/*.md`
- `PROGRAM.md` governs autonomous work
- `hive next`, `hive work`, and `hive finish` form the manager loop
- the console exists as a genuine observe-and-steer surface
- runs, memory, events, and campaigns are first-class concepts
- the model-facing interface remains intentionally thin (`search` + `execute` or direct CLI/JSON) (Source 1)

That is the good news.

The bad news is that the last 20–25% matters disproportionately:

### 2.1 Runtime harness depth is still incomplete

The current shared `HarnessDriver` is still a staging adapter. Its own notes say Hive prepares a run pack and that the external harness is “not auto-launched from Hive yet,” but the current capability block still advertises resume, streaming, subagents, and scheduled behavior in a flat way.(Source 2)

That mismatch hurts trust, operator UX, and future learning quality.

### 2.2 Campaigns are still task pickers, not portfolios

The current campaign layer is useful, but the intended product is a multi-lane policy system that balances exploitation, exploration, review burden, and recurring maintenance. v2.3 has to make campaign policy explicit and logged.

### 2.3 Retrieval still needs to become explainable infrastructure

Hive already has search and memory, but it still feels closer to a pragmatic doc/task search layer than to a durable hybrid retrieval subsystem. v2.3 needs to make search:
- more accurate
- more inspectable
- more portable in installed environments
- more ready for v2.3 backtesting

### 2.4 Sandboxing is still underspecified

The README is honest that current `execute` is a bounded local Python helper, not a full sandbox.(Source 1) That honesty is good. The missing step is to replace that ambiguity with a deliberate multi-backend sandbox system that works locally, hosted, and self-hosted.

## 3. Decisions resolved in this RFC

These are no longer open questions.

## 3.1 Worker harnesses Hive will deeply support in v2.3

**First-class deep drivers**
- Codex
- Claude
- Pi

**First-class honest fallback**
- manual / staged
- local deterministic runner

**Not first-class deep drivers in v2.3**
- Hermes
- OpenClaw
- bespoke MCP-only external harnesses

Those can be supported later through the same driver contract, but they should not delay completion of Codex + Claude + Pi depth.

### Why Codex

Codex now has a strong integration surface:
- `codex app-server` supports bidirectional JSON-RPC over stdio or websocket(Source 3)
- it streams turn and item events, diffs, plans, token usage, and supports turn steering and interruption(Source 3)
- it exposes approval requests back to the client for commands and file changes(Source 3)
- it supports explicit skill injection(Source 3)
- `codex exec` is stable for non-interactive automation and supports scripting/CI(Source 4)(Source 5)

That is exactly what Hive needs for an interactive observe-and-steer driver plus a batch fallback.

### Why Claude

Anthropic’s Agent SDK is the right level of integration:
- Anthropic explicitly describes it as Claude Code “as a library,” with the same tools, loop, and context management(Source 10)
- `ClaudeSDKClient` supports persistent sessions, streaming responses, follow-up turns in the same session, interrupts, and explicit permission handling(Source 11)
- the SDK exposes hooks, sessions, permissions, subagents, and MCP in a programmable interface(Source 10)
- Claude Code’s native sandboxing is useful, but Hive should treat it as an inner boundary, not the only boundary(Source 12)(Source 13)

### Why Pi

Pi gives Hive a vendor-diverse third driver that matches Hive’s design philosophy:
- programmatic SDK for embedding custom workflows and UIs(Source 15)
- JSONL RPC mode for headless orchestration over stdin/stdout(Source 16)
- minimalist inspectable harness model with explicit branch/session thinking(Source 17)

### Why not Hermes or OpenClaw first

They are strategically relevant, but they do not yet beat the implementation leverage of Codex + Claude + Pi:
- Codex and Claude already dominate the likely user base for engineering workflows
- Pi adds proof that Hive is not a two-vendor shell
- Hermes/OpenClaw adapters can land after the driver contract is stabilized

## 3.2 The runtime integration split

Hive will treat these as separate layers:

1. **Driver** — talks to the harness
2. **Sandbox backend** — constrains execution
3. **Context compiler** — projects Hive truth into harness-native files and settings
4. **Event normalizer** — turns harness activity into Hive run events
5. **Evaluator/promoter** — decides what may graduate
6. **Console/CLI** — shows and steers the result

No single driver object is allowed to blur those layers.

## 3.3 Sandboxing choices

### Chosen local default: rootless Podman

Why:
- Podman supports clients on Linux, macOS, and Windows(Source 22)
- macOS and Windows paths are realistic through `podman machine`(Source 23)
- rootless Podman uses user namespaces and supports rootless mappings in the run model(Source 24)

### Chosen local alternative: Docker rootless

Why:
- Docker rootless runs both daemon and containers as a non-root user inside a user namespace(Source 25)
- it is a practical alternative for users already standardized on Docker
- Docker’s own security docs make clear why rootless is preferable to broad daemon access(Source 25)(Source 26)

### Chosen enterprise desktop hardening option: Docker Desktop ECI

Why:
- ECI uses Sysbox, user namespaces, namespace isolation enforcement, protected bind mounts, and advanced syscall protections(Source 27)
- it is the best “already on Docker Desktop Business” hardening path
- it is **not** the default because it requires Docker Business and has platform/version caveats(Source 27)

### Chosen fast local wrapper: Anthropic sandbox runtime

Why:
- it is already cross-platform enough for macOS, Linux, and WSL2(Source 12)
- it is useful when Hive needs to wrap a subprocess or MCP-compatible helper without standing up a full container
- it complements, but does not replace, outer container/microVM isolation

### Chosen managed hosted default: E2B

Why:
- pause/resume preserves both filesystem and memory state(Source 28)
- PTY sessions support real-time bidirectional interaction(Source 29)
- Pro plans can keep sessions alive up to 24 hours(Source 30)
- E2B is already built around the “virtual computer for agents” model Hive needs

### Chosen self-hosted / team-managed default: Daytona

Why:
- Daytona sandboxes provide a dedicated kernel, filesystem, and network stack(Source 31)
- OCI-based snapshots give reproducible environments(Source 31)(Source 33)
- organization and sandbox-level network control exists(Source 32)
- Git and code execution APIs are already first-class(Source 34)

### Experimental only: Cloudflare Sandbox

Why:
- promising API surface for secure isolated execution inside Workers(Source 19)(Source 20)
- useful for experimental remote execution and for people already standardized on Workers
- still in open beta, with explicit limitation language(Source 21)
- not mature enough to be the default hosted path

### Explicitly deferred: a first-party Firecracker runtime

Why:
- Firecracker is excellent technology for secure multi-tenant microVMs(Source 35)
- but it is KVM/Linux infrastructure with real operational complexity
- building and shipping that as a required v2.3 dependency would slow the release and narrow adoption
- it is a strong future hosted-platform substrate, not the right v2.3 product default

## 3.4 Retrieval choices

### Chosen local default

- operational metadata and lexical fallback: **SQLite FTS5**
- dense semantic store: **LanceDB**
- embeddings and rerankers: **FastEmbed**
- graph augmentation: Hive’s own task/run/memory links

Why:
- LanceDB OSS is embedded and can target a local path or object storage URI(Source 36)
- it behaves more like SQLite than like a required network service
- FastEmbed gives a practical local model path for dense embeddings and reranking(Source 39)
- SQLite keeps installation friction low and lets lexical search remain available everywhere

### Chosen optional remote/team backend

- **Qdrant**

Why:
- Qdrant has first-class hybrid dense+sparse query patterns and built-in RRF fusion(Source 37)(Source 38)
- it is a good team/shared backend once Hive has multiple operators or shared search infrastructure
- it should remain optional in v2.3, not the default

## 3.5 Campaign orchestration choices

Campaigns will be explicit policy objects with:
- a **type** (`delivery`, `research`, `maintenance`, `review`)
- lane quotas across `exploit`, `explore`, `review`, `maintenance`
- harness preferences
- sandbox preferences
- budget policy
- escalation policy
- brief cadence
- selection score logging

This is the minimum viable form of true portfolio control.

## 3.6 Capability reporting choices

Hive will no longer treat a single flat capability record as truth.

Every run records:

- `declared`: what the adapter can theoretically do
- `probed`: what this install/environment can do right now
- `effective`: what this run is actually allowed to do after driver, sandbox, account, `PROGRAM.md`, and campaign policy are combined
- `evidence`: strings or structured records that explain why the capability is or is not available

This is mandatory for:
- console trust
- driver doctor
- sandbox doctor
- future scheduler learning
- future v2.3 backtesting

## 4. Goals

1. **Deep runtime integrations** for Codex and Claude, plus Pi as the third serious driver.
2. **Truthful capabilities** with no more optimistic staging behavior masquerading as deep support.
3. **Best-in-class observe-and-steer UX** for multi-project operator work.
4. **Pluggable but real sandboxes** across local, hosted, and self-hosted deployment models.
5. **Hybrid retrieval with provenance and explanations**.
6. **Policy-driven campaigns** instead of simplistic next-task launching.
7. **v2.3-ready telemetry** for backtesting and continual improvement.

## 5. Non-goals

1. Do not build a first-party hosted Firecracker fleet in v2.3.
2. Do not add a broad MCP tool catalog.
3. Do not promise deep adapters for every agent harness on earth.
4. Do not make the console a second source of truth.
5. Do not silently mutate memory or policy without audit trails.
6. Do not make Qdrant or any remote vector DB mandatory for local adoption.

## 6. Target architecture

```text
Hive task/project/campaign truth
        |
        v
  context compiler
        |
        v
     runpack
        |
        +--> driver (Codex / Claude / Pi / manual)
        |
        +--> sandbox backend (Podman / Docker / ASRT / E2B / Daytona / Cloudflare-exp)
        |
        v
 normalized event stream
        |
        +--> console / CLI / inbox / approvals
        +--> artifacts / transcripts / evaluator results
        +--> retrieval traces / scheduler decisions
        |
        v
 evaluator / promoter / memory reflectors
        |
        v
 accepted work, escalations, campaign briefs, future backtesting inputs
```

## 7. Release red lines

v2.3 **must not** ship if any of these are still true:

1. Codex and Claude are still only staged by default.
2. A driver can advertise streaming/resume/subagents when the current installation cannot actually use them.
3. A user cannot tell what sandbox protected a run.
4. A campaign launch cannot explain why one candidate won over another.
5. Retrieval results do not explain why they matched.
6. Retrieval traces are not persisted.
7. The observe console still depends on the user understanding raw Markdown state to know what needs attention.

## 8. What success looks like

**North-star scenario**

One operator supervises:
- three projects
- ten concurrent runs
- across Codex, Claude, Pi, and a deterministic local helper
- from one console and one inbox
- with policy-controlled approvals
- with explicit capability snapshots
- with explainable retrieval
- with campaign briefs that explain not only what happened, but why Hive launched what it launched

If that works cleanly, v2.3 is done.

## 9. v2.3 readiness requirements baked into v2.3

Every run must persist:

- selected driver
- capability snapshot
- selected sandbox backend
- sandbox policy
- compiled context manifest
- skills and projections used
- retrieval queries, candidates, scores, and final injected chunks
- scheduler candidate set and chosen score
- steering actions and approvals
- transcript path
- evaluator outputs
- final promotion/escalation reason

Those artifacts are not optional. They are the training and backtesting substrate for the v2.3 continual-improvement lab.

## 10. File outputs required by this RFC

This RFC assumes v2.3 implementation produces:

```text
.hive/runs/<run-id>/
  manifest.json
  capability-snapshot.json
  sandbox-policy.json
  events.ndjson
  approvals.ndjson
  transcript.ndjson
  retrieval/
    trace.json
    hits.json
  scheduler/
    candidate-set.json
    decision.json
  artifacts/
    patch.diff
    changed-files.json
    logs/
  eval/
    results.json
  final.json
```

and:

```text
.hive/campaigns/<campaign-id>/
  campaign.md
  policy.json
  board.json
  decisions.ndjson
  briefs/
  metrics.json
```

## 11. What Codex should not debate during implementation

These are frozen:

- Codex app-server is the primary interactive Codex adapter
- `codex exec` is the non-interactive Codex fallback
- Claude Agent SDK is the primary Claude adapter
- Pi RPC is the third first-class external harness driver
- Podman rootless is the local default sandbox
- E2B is the managed hosted default
- Daytona is the self-hosted/team default
- LanceDB + SQLite + FastEmbed is the local default retrieval stack
- Qdrant is optional remote retrieval
- campaign scheduling is lane/policy-based, not “best next task wins”

## 12. Companion documents

- `HIVE_V2_3_RUNTIME_AND_SANDBOX_SPEC.md`
- `HIVE_V2_3_RETRIEVAL_AND_CAMPAIGNS_SPEC.md`
- `HIVE_V2_3_IMPLEMENTATION_PLAN.md`
- `HIVE_V2_3_ACCEPTANCE_TESTS.md`
- `SOURCES.md`

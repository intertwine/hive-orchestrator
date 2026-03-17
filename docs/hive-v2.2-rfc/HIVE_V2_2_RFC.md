# Hive 2.2 RFC — Universal Observe-and-Steer Control Plane

Status: Proposed  
Date: 2026-03-15  
Audience: product, design, implementation, docs  
Scope: `intertwine/hive-orchestrator` v2.2  
Depends on: current v2.1 main branch

## 1. Executive summary

Hive 2.2 is a **productization release**, not a substrate rewrite.

Hive 2.1 already established the right foundations: a CLI-first architecture, canonical task state under `.hive/`, `PROGRAM.md` as the autonomy contract, a manager loop (`next`, `work`, `finish`, `portfolio`), a thin Code Mode-style `search` + `execute` surface, and enough memory/run machinery to support real autonomous work. v2.2 should keep that substrate and turn it into a **world-class cross-harness command center**.

The product position is simple:

> **Keep your favorite agent. Hive is the control plane above it.**

That means Hive should not try to out-IDE Codex, out-chat Claude, or out-minimal Pi. It should own the layer that those products still leave fragmented:

- **multi-project portfolio visibility**
- **cross-harness run supervision**
- **human steering and approvals**
- **repo-native policy and memory**
- **context compilation**
- **scheduled and campaign-style autonomy**
- **auditability and reproducibility**

The core outcome for v2.2 is this:

1. A human can supervise many concurrent runs across multiple projects and harnesses from one place.
2. A strong LLM can control Hive through a tiny, stable interface instead of a bloated tool catalog.
3. Every run is inspectable: what context it got, why it was chosen, what policy applied, what changed, and why it was accepted or escalated.
4. Hive remains agent-, harness-, and model-agnostic.

## 2. Context and market thesis

The category is shifting from “single coding assistant” to **multi-agent supervision**.

Recent product moves all point in the same direction:

- The Codex app explicitly positions itself as a **command center for agents**, with parallel threads, built-in worktrees, skills, and automations.[^codex_app]
- Claude Code now emphasizes persistent `CLAUDE.md`, skills, subagents, teams, and deterministic hooks.[^claude_features]
- Cowork adds long-running and scheduled tasks, but its scheduling still depends on Claude Desktop being open and the machine being awake.[^cowork_sched][^cowork_safe]
- Cloudflare’s Code Mode shows why a **thin `search()` + `execute()` API** is better than exposing thousands of narrow MCP tools.[^cloudflare_code_mode]
- Pi argues for a tiny, inspectable harness with minimal hidden context and minimal built-ins.[^pi_post]
- Hermes emphasizes persistent memory, skills, resumable sessions, and flexible deployment.[^hermes_docs][^hermes_memory]
- OpenClaw shows demand for onboarding, dashboards, routing, and multi-agent control surfaces.[^openclaw_docs][^openclaw_multi]
- Karpathy’s autoresearch demonstrates the power of a human-authored `program.md` plus bounded experiment loops and measurable outcomes.[^autoresearch]

Hive should not fight those products head-on. It should unify them.

## 3. Product thesis

### 3.1 Product category

Hive 2.2 is a:

repo-native, model-agnostic, harness-agnostic control plane for long-running autonomous work

### 3.2 What Hive owns

Hive owns:

- project and portfolio state
- task graph and campaigns
- run lifecycle and artifacts
- evaluator and promotion policy
- steering actions and audit trail
- cross-harness normalization
- context compilation and memory inspection
- scheduling and recurring work
- search over repo docs, skills, recipes, tasks, runs, and memory
- operator UX for observe and steer

### 3.3 What Hive does not own

Worker harnesses own:

- interactive coding loop
- local editor integration
- harness-native execution/runtime
- harness-native conveniences (subagents, branching, command approval UX, etc.)
- low-level tool invocation

### 3.4 v2.2 positioning line

**Use Codex or Claude Code to do the work. Use Hive to direct, supervise, and remember the work.**

## 4. Goals

1. **Harness agnosticism:** one operator experience above Codex, Claude Code, local execution, and manual/clipboard workflows; Pi, Hermes, and OpenClaw adapters should be possible with the same driver contract.
2. **Model agnosticism:** no first-class product assumptions that depend on one model vendor.
3. **Observe-first UX:** the default human experience is a live portfolio console, not markdown browsing.
4. **Steer-first UX:** pausing, rerouting, approving, budget adjustment, and side-questing are first-class actions with audit trails.
5. **Tiny agent surface:** keep the machine-facing interface small and stable; prefer typed CLI/JSON and optional thin MCP over tool catalogs.
6. **Trustworthy inspectability:** show exactly what context, memory, skills, and policy affected a run.
7. **Cross-project autonomy:** add campaigns, scheduling, recurring briefs, and exploit/explore portfolio control.
8. **Repo-native truth:** the dashboard is not the database; projections are not canonical.
9. **Marketable onboarding:** new users can adopt an existing repo, pick a harness, and delegate first work in under 10 minutes.

## 5. Non-goals

1. Hive 2.2 does **not** replace Codex, Claude Code, Pi, Hermes, OpenClaw, or any IDE.
2. Hive 2.2 does **not** build a full chat-first consumer assistant.
3. Hive 2.2 does **not** expose a sprawling MCP tool surface.
4. Hive 2.2 does **not** promise hostile multi-tenant isolation in MVP.
5. Hive 2.2 does **not** add hidden or magical context mutation.
6. Hive 2.2 does **not** make the dashboard a second source of truth.
7. Hive 2.2 does **not** try to solve cloud execution, mobile UX, and voice UX all at once.

## 6. Design principles

### P1. Own the control plane, not the worker

Hive wins by coordinating worker harnesses, not by becoming another worker harness.

### P2. Thin surface, rich substrate

The agent-facing surface stays tiny (`search`, `execute`, and a stable JSON CLI). Complexity lives in:

- context compilation
- skills
- searchable docs/recipes
- canonical state
- event streams
- run artifacts

### P3. Inspectability beats cleverness

Users must be able to answer:

- Why was this chosen?
- What context did the agent get?
- What policy applied?
- Why is this blocked?
- Why was this accepted?

### P4. Structured steering over chat steering

Steering should be typed actions with audit events, not ad hoc “please do X now” notes buried in transcripts.

### P5. Progressive autonomy

Autonomy expands with policy maturity. Projects should become safer through `PROGRAM.md`, evaluator templates, and guided setup.

### P6. Vendor neutrality at the edges

Driver adapters can be vendor-specific; Hive core must not be.

### P7. Minimal required context

Codex’s skill model and Pi’s critique both push the same lesson: keep base context lean and load detail on demand.[^pi_post][^codex_skills]

### P8. One source of truth

Canonical repo state stays in Hive-controlled files and append-only events.

## 7. Current-state baseline

Hive 2.2 starts from the current main-branch architecture, not from scratch:

- `hive` is the primary interface
- `.hive/tasks/*.md` is canonical task state
- `projects/*/AGENCY.md` remains human-readable
- `projects/*/PROGRAM.md` defines evaluator and command policy
- `GLOBAL.md` and `AGENTS.md` are projections
- the current manager loop already includes `next`, `work`, `finish`, and portfolio-oriented control[^hive_readme]

This RFC assumes those substrate choices remain intact.

## 8. Personas and top jobs

### 8.1 Solo founder / technical lead

Needs to direct multiple agents across product, code, docs, and launch work without babysitting every task.

### 8.2 Staff engineer / engineering manager

Needs to monitor concurrent work across repos, approve risky changes, and keep state understandable for humans.

### 8.3 Agency / consultant / fractional CTO

Needs to operate across many client projects, often with different harnesses and policies.

### 8.4 Research / experimentation lead

Needs bounded experiment loops, scheduling, keep/discard behavior, and portfolio steering over many candidate runs.

## 9. Product definition

Hive 2.2 is the combination of six product surfaces:

1. **Universal Drivers** — normalized adapters for worker harnesses
2. **Observe Console** — the operator command center
3. **Steer Console** — typed intervention and approvals
4. **Context & Memory Inspector** — inspect what shaped a run
5. **Campaigns & Scheduling** — long-running, recurring, multi-run goals
6. **Thin Agent Interface** — stable CLI JSON and optional thin MCP

## 10. Proposed v2.2 scope

### 10.1 Universal driver layer

Add a normalized driver contract that abstracts harness-specific launch/resume/status behavior.

Initial supported drivers:

- `local`
- `manual` (clipboard / human-run / paste-back)
- `codex`
- `claude-code`

Beta / experimental drivers:

- `pi`
- `hermes`
- `openclaw`

#### 10.1.1 Driver contract

Every driver MUST implement:

- `probe() -> DriverInfo`
- `launch(RunLaunchRequest) -> RunHandle`
- `resume(RunHandle) -> RunHandle`
- `status(RunHandle) -> RunStatus`
- `interrupt(RunHandle, mode) -> Ack`
- `steer(RunHandle, SteeringRequest) -> Ack`
- `collect_artifacts(RunHandle) -> ArtifactBundle`
- `stream_events(RunHandle) -> EventStream`

Optional:

- `checkpoint()`
- `reroute_export()`
- `reroute_import()`
- `exec_preview()`

#### 10.1.2 Capability model

Each driver advertises booleans or enums for:

- worktree support
- resume support
- streaming output
- subagent support
- scheduled execution
- remote execution
- diff preview
- sandbox strength
- command approval mode
- context-file support (`AGENTS.md`, `CLAUDE.md`, `SOUL.md`, etc.)
- skill support
- interrupt semantics
- artifact availability

Hive MUST use capability detection rather than hard-coded vendor assumptions.

### 10.2 Unified run model

Today, runs are already real objects. v2.2 makes them the product’s central UX object.

#### 10.2.1 Canonical run states

Every run MUST map into the same lifecycle:

- `queued`
- `compiling_context`
- `launching`
- `running`
- `awaiting_input`
- `awaiting_review`
- `blocked`
- `completed_candidate`
- `accepted`
- `rejected`
- `escalated`
- `cancelled`
- `failed`

#### 10.2.2 Standard artifacts

Every run SHOULD expose a normalized artifact set:

```text
.hive/runs/run_<id>/
  metadata.json
  launch.json
  context/
    manifest.json
    compiled/
  transcript/
    normalized.jsonl
    raw/
  plan/
    plan.md
    plan.json
  workspace/
    patch.diff
    changed_files.json
  eval/
    *.json
  review/
    summary.md
    review.md
  driver/
    driver-metadata.json
    handles.json
  logs/
    stdout.txt
    stderr.txt
  events.jsonl
```

Driver-specific artifacts MAY be added under `driver/`, but the normalized artifact set is what the UI and CLI rely on.

### 10.3 Context compiler

The context compiler is the main v2.2 differentiator.

It takes:

- project state
- campaign context
- task state
- `PROGRAM.md`
- approved memory slices
- steering notes
- skill metadata
- driver capabilities
- repo docs/recipes search hits

It outputs:

- a minimal run brief
- driver-specific context files or overlays
- a context manifest explaining exactly what was included and why

#### 10.3.1 Compiler goals

1. Keep default context compact.
2. Prefer pointers and search results over giant instruction dumps.
3. Make all included context inspectable.
4. Generate harness-specific files from Hive state instead of hand-maintaining them.
5. Use progressive disclosure for skills and recipes.

#### 10.3.2 Outputs

Examples:

- `compiled/AGENTS.md`
- `compiled/CLAUDE.md`
- `compiled/SOUL.md`
- `compiled/run-brief.md`
- `compiled/skills-manifest.json`
- `manifest.json`

#### 10.3.3 Context manifest

For every compiled bundle, Hive MUST record:

- source file
- source type (`program`, `task`, `memory`, `skill-meta`, `search-hit`, `steering-note`)
- byte count / token estimate
- inclusion reason
- whether it was required, recommended, or optional
- whether it was truncated or compacted

### 10.4 Observe Console

The current dashboard becomes a live operator console.

#### 10.4.1 Primary design rule

The operator should live in **exceptions and decisions**, not in folders.

#### 10.4.2 Information architecture

Top-level surfaces:

1. **Home**
   - what is running now
   - what is blocked
   - what needs attention
   - what changed since last visit
   - suggested next delegation

2. **Runs**
   - active runs board
   - filters by project, harness, owner, health, campaign
   - health indicators and “why unhealthy?” explanations

3. **Inbox**
   - approvals
   - escalations
   - blocked-item requests
   - failed evaluator alerts
   - policy violations
   - memory merge suggestions

4. **Campaigns**
   - campaign status
   - exploit vs explore progress
   - budgets, cadence, and outcomes

5. **Projects**
   - project summary
   - tasks, runs, memory, brief, evaluator health

6. **Search**
   - unified search across docs, tasks, runs, memory, skills, recipes, and campaigns

7. **Run Detail**
   - timeline
   - logs
   - artifacts
   - diff
   - eval results
   - compiled context
   - steering history

#### 10.4.3 Observe Console requirements

- no manual sync button
- live refresh from event stream or polling adapter
- every board item shows why it is in that state
- “why this next?” and “why blocked?” explanations are mandatory
- project browsing is secondary, not primary

### 10.5 Steer Console

Steering becomes an explicit, typed layer.

#### 10.5.1 Steering actions

Hive MUST support at least:

- `pause`
- `resume`
- `cancel`
- `reroute`
- `raise_budget`
- `lower_budget`
- `attach_note`
- `request_review`
- `approve`
- `reject`
- `rollback`
- `requeue`
- `spawn_sidequest`
- `demote_to_task`
- `promote_to_campaign`

#### 10.5.2 Steering model

Every steering action MUST:

- create a `steering.*` event
- record actor, reason, timestamp, and affected run/task/campaign IDs
- be visible in run and campaign timelines
- be available through both CLI and UI

#### 10.5.3 Reroute

Rerouting is a core v2.2 differentiator.

A run SHOULD be reroutable:

- from one model to another within a harness
- from one harness to another when export/import capability exists
- from autonomous mode to manual review mode

Reroute MUST preserve:

- original task/run linkage
- steering history
- budgets spent so far
- artifact lineage

### 10.6 Context & Memory Inspector

The user must be able to inspect exactly what shaped a run.

#### 10.6.1 Inspector panes

For every run, show:

- compiled instructions
- `PROGRAM.md` rules in force
- loaded skills and why they were suggested or activated
- memory snippets injected
- search hits used in compilation
- truncation/compaction summary
- context size and token estimate
- what changed in memory after completion
- diff from previous run context on the same task/campaign

#### 10.6.2 Post-run memory review

Memory changes SHOULD go through a merge/review layer when confidence is low.

Each proposed change MUST show:

- old text
- new text
- provenance
- confidence / rationale
- accept / reject / edit actions

### 10.7 Campaigns & Scheduling

Tasks are too small a unit for many real-world workflows. v2.2 adds campaigns.

#### 10.7.1 Campaign definition

A campaign is a bounded multi-run initiative with:

- goal
- scope (one or more projects)
- budget
- cadence or deadline
- success signals
- steering defaults
- exploit/explore policy
- brief cadence

Examples:

- Reduce flaky tests in three repos
- Prepare launch materials for a release
- Run overnight design experiments
- Produce weekly engineering brief

#### 10.7.2 Campaign files

Canonical files:

```text
.hive/campaigns/
  campaign_<id>.md
.hive/briefs/
  daily/
  weekly/
```

Campaign records SHOULD be one-file-per-campaign like tasks.

#### 10.7.3 Scheduling

Hive MUST support:

- one-off scheduled launches
- recurring schedules
- daily / weekly brief generation
- overnight exploit/explore runs
- pause windows and quiet hours

Scheduling MUST work on:

- local machine
- CI
- VPS / server
- remote runner

v2.2 should not depend on “desktop app open and machine awake” semantics.

### 10.8 Search, skills, and recipes

#### 10.8.1 Search

Keep the surface thin:

- `search(query, scope, filters)`
- `execute(request)`

But make the backing corpus rich.

Search MUST cover:

- repo docs
- packaged docs/examples
- tasks
- runs
- memory
- skills
- recipes
- campaigns
- project projections

Search ranking SHOULD:

- prefer canonical state over projections
- collapse duplicates
- explain why a result matched
- handle lexical + semantic ranking
- return structured snippets

#### 10.8.2 Skills and recipes

Skills stay on-demand. v2.2 adds:

- packaged example skills
- packaged operator recipes
- task/harness-specific recommendation logic
- recipe search in normal installs, not only source checkouts

#### 10.8.3 Packaging requirement

The install artifact MUST include:

- docs needed for `search`
- examples
- recipe corpus
- skill metadata stubs
- harness integration guides

The current “search is better in source checkouts than installs” gap MUST be closed.

### 10.9 Onboarding and adoption

v2.2 needs a product-grade first-run experience.

#### 10.9.1 `hive onboard`

Guided flow:

1. detect repo and existing harness files
2. detect installed drivers
3. pick harness preference
4. scaffold `PROGRAM.md`
5. run program doctor
6. create first task
7. launch first run
8. open Observe Console

#### 10.9.2 `hive adopt`

Guided repo adoption:

1. analyze current repo structure
2. infer project boundaries
3. detect existing `AGENTS.md`, `CLAUDE.md`, scripts, CI, tests
4. propose `PROGRAM.md`
5. import or generate initial tasks
6. compile driver contexts
7. preview risk / policy gaps

#### 10.9.3 Program Doctor

Add `hive program doctor` and `hive program add-evaluator`.

Doctor MUST:

- detect missing evaluators
- detect unsafe path policies
- recommend templates based on stack
- explain why autonomous promotion is blocked
- offer one-command fixes where safe

### 10.10 Security and trust model

v2.2 must be explicit about trust boundaries.

#### 10.10.1 Trust levels

Every driver MUST declare a trust profile:

- filesystem boundary
- network boundary
- shell execution boundary
- remote execution boundary
- identity / account scope
- artifact provenance strength

#### 10.10.2 UI disclosure

The UI MUST show:

- trust level badge
- whether execution is local, remote, or manual
- whether command approvals are enforced by harness or Hive
- whether reroute may drop sandbox guarantees

#### 10.10.3 No fake security claims

Adopting the Code Mode pattern does **not** imply Cloudflare-grade isolation. The interface pattern and the security model are separate.

### 10.11 Telemetry and success metrics

v2.2 SHOULD track:

- time to first delegated task
- approval latency
- escalation rate
- evaluator pass rate
- reroute frequency
- campaign success rate
- search hit usefulness
- memory merge acceptance rate
- mean concurrent supervised runs per operator
- “why next?” click-through and override rate
- time to recover from unhealthy run

## 11. CLI contract changes

### 11.1 New top-level groups

```text
hive drivers ...
hive runs ...
hive steer ...
hive campaigns ...
hive briefs ...
hive console ...
hive doctor ...
```

Alias-friendly versions MAY exist:

- `hive run ...`
- `hive campaign ...`
- `hive brief ...`

### 11.2 Required commands

#### Drivers

- `hive drivers list --json`
- `hive drivers probe <driver> --json`

#### Runs

- `hive run launch <task-id> [--driver codex] [--campaign ...] --json`
- `hive run status <run-id> --json`
- `hive run artifacts <run-id> --json`
- `hive run reroute <run-id> --driver claude-code --json`

#### Steer

- `hive steer pause <run-id> --reason ... --json`
- `hive steer resume <run-id> --json`
- `hive steer note <run-id> --message ... --json`
- `hive steer approve <run-id> --json`
- `hive steer reject <run-id> --reason ... --json`
- `hive steer sidequest <run-id> --title ... --json`

#### Campaigns

- `hive campaign create ... --json`
- `hive campaign status <campaign-id> --json`
- `hive campaign tick <campaign-id> --json`

#### Briefs

- `hive brief daily --json`
- `hive brief weekly --json`

#### Console

- `hive console serve`
- `hive console open`

#### Doctor

- `hive doctor program [project] --json`
- `hive doctor repo --json`

## 12. File-system changes

New repo-local structure:

```text
.hive/
  campaigns/
    campaign_<id>.md
  briefs/
    daily/
    weekly/
  compiled-context/
    run_<id>/
      manifest.json
      AGENTS.md
      CLAUDE.md
      SOUL.md
      run-brief.md
  drivers/
    handles/
      run_<id>.json
    cache/
  recipes/
    index.json
```

Guidelines:

- canonical state remains text-first
- caches are gitignored
- compiled context MAY be gitignored by default but should be preservable for debugging
- event log remains append-only

## 13. UX requirements

### 13.1 Default home screen

The default operator landing page MUST answer five questions in < 5 seconds:

1. What is running?
2. What is blocked?
3. What needs me?
4. What changed since I last checked?
5. What should I do next?

### 13.2 Morning briefing

Hive SHOULD generate a briefing that summarizes:

- completed work
- risky or stalled work
- new escalations
- campaign progress
- recommended steering actions
- notable memory/profile changes

### 13.3 Run detail page

Run detail MUST include:

- timeline
- health summary
- artifacts
- diff
- evaluator results
- compiled context
- steering history
- driver metadata
- log stream
- “what changed in memory” section

### 13.4 Keyboard-first ergonomics

Because the core audience is technical, the UI SHOULD support:

- keyboard navigation
- quick approve/reject
- fast project/run switching
- copyable CLI equivalents for UI actions

## 14. Acceptance criteria for v2.2

A v2.2 release is complete only if all of the following are true.

### 14.1 Control-plane correctness

- The same task can be launched via `local`, `codex`, and `claude-code` drivers without changing canonical task or project metadata.
- Every run from those drivers appears in one normalized run board.
- Every accepted run has a visible promotion rationale and evaluator evidence.
- Every steering action produces an audit event visible in both CLI JSON and UI timeline.

### 14.2 Observe-and-steer UX

- An operator can supervise at least **10 concurrent runs across 3 projects** without dropping to raw markdown or ad hoc shell scripts.
- The Inbox surface catches all approvals, escalations, and policy failures without manual refresh.
- There is no manual projection-sync button in the primary UI path.

### 14.3 Context and memory trust

- Every run shows the exact compiled context bundle and why each item was included.
- Every post-run memory mutation is attributable to a run and reviewable.
- Installed users get useful docs/recipes search without cloning the repo.

### 14.4 Onboarding

- A new user can install Hive, adopt an existing repo, pick a harness, and launch a first governed run in under 10 minutes.
- `hive program doctor` can take a project from “unsafe/no evaluator” to “safe baseline” with guided commands.

### 14.5 Product narrative

- The docs and landing copy consistently describe Hive as a cross-harness control plane.
- The dashboard, CLI, and harness shims all teach the same observe-and-steer mental model.

## 15. Milestone plan

### Milestone 1 — Contract freeze

Deliver:

- driver spec
- run event schema
- steering action schema
- UI IA
- operator flows
- CLI naming freeze

Acceptance:

- all implementation work can target stable nouns and lifecycle states

### Milestone 2 — First universal drivers

Deliver:

- `local`, `manual`, `codex`, `claude-code` drivers
- capability probing
- normalized artifacts and transcripts
- context compiler v1

Acceptance:

- cross-driver launch/status/interrupt works
- run board can mix drivers

### Milestone 3 — Observe Console

Deliver:

- new home page
- runs board
- inbox
- run detail
- project summaries
- live refresh/event streaming

Acceptance:

- no manual sync in primary path
- exception-driven operation is viable

### Milestone 4 — Steer Console + Program Doctor

Deliver:

- steering UI and CLI
- reroute support
- budget controls
- approvals workflow
- doctor and evaluator templates

Acceptance:

- safe autonomous setup no longer requires raw YAML/Markdown editing

### Milestone 5 — Context, memory, search, skills

Deliver:

- context manifest viewer
- memory delta review
- packaged docs/recipes corpus
- improved ranking and duplicate collapse
- skill and recipe recommendations

Acceptance:

- runs are explainable
- install search is materially useful

### Milestone 6 — Campaigns, scheduling, launch polish

Deliver:

- campaign model
- recurring schedules
- daily/weekly brief generation
- exploit/explore policies
- onboarding/adoption flows
- product docs and demos

Acceptance:

- Hive feels like a product, not only a framework

## 16. Risks and open questions

### 16.1 Driver drift

Harnesses evolve quickly. Driver maintenance cost may become real. Mitigation: keep the driver contract small and capability-based.

### 16.2 Over-contexting

Context compiler could become too aggressive. Mitigation: token budgets, manifests, and visibility.

### 16.3 Security ambiguity

Users may overestimate safety from thin interfaces. Mitigation: explicit trust badges and docs.

### 16.4 Reroute semantics

Not every harness will preserve state equally well. Mitigation: define reroute grades:

- metadata-only
- transcript-aware
- checkpoint-aware

### 16.5 UI complexity

A control plane can become cluttered. Mitigation: inbox-first and drill-down patterns, not “everything everywhere”.

### 16.6 Campaign sprawl

Campaigns could become vague mega-projects. Mitigation: budgets, review cadence, archive rules.

## 17. Launch narrative

### 17.1 Tagline

Hive: the command center for autonomous work

### 17.2 One-line pitch

**Keep your favorite agent. Hive gives you the portfolio board, steering controls, policy, memory, and audit trail above it.**

### 17.3 Demo story

1. Adopt an existing repo.
2. Detect Codex and Claude Code.
3. Create two governed runs on one task with different harnesses.
4. Watch both appear in the run board.
5. Pause one, reroute one, accept one.
6. Show exact context and evaluator evidence.
7. End with a morning brief and a campaign summary.

## 18. Implementation notes

### 18.1 Recommended order

Build driver normalization and event schemas before the new UI. A pretty dashboard on top of unstable lifecycles will rot fast.

### 18.2 Backwards compatibility

- keep current CLI aliases where possible
- map older dashboard routes to the new Observe Console
- support legacy AGENTS/CLAUDE compatibility shims during transition

### 18.3 What to cut if schedule slips

Do **not** cut:

- driver normalization
- observe console home/inbox/runs
- steering actions
- context manifest
- program doctor
- packaged docs/recipes search

Cut or defer first:

- beta drivers
- advanced exploit/explore policies
- remote executor polish
- advanced memory auto-merge heuristics

## 19. References

[^codex_app]: OpenAI, “Introducing the Codex app,” February 2, 2026. It describes Codex as a “command center for agents” with parallel threads, worktrees, skills, and automations. <https://openai.com/index/introducing-the-codex-app/>

[^claude_features]: Claude Code docs, “Extend Claude Code / Features overview.” It documents `CLAUDE.md`, skills, MCP, subagents, agent teams, and hooks. <https://code.claude.com/docs/en/features-overview>

[^cowork_sched]: Claude Help Center, “Schedule recurring tasks in Cowork.” It documents recurring/on-demand scheduled tasks. <https://support.claude.com/en/articles/13854387-schedule-recurring-tasks-in-cowork>

[^cowork_safe]: Claude Help Center, “Use Cowork safely.” It notes that scheduled tasks only run while the computer is awake and Claude Desktop is open. <https://support.claude.com/en/articles/13364135-use-cowork-safely>

[^cloudflare_code_mode]: Cloudflare Blog, “Code Mode: give agents an entire API in 1,000 tokens,” February 20, 2026. It describes a thin `search()` + `execute()` MCP surface over the Cloudflare API. <https://blog.cloudflare.com/code-mode-mcp/>

[^pi_post]: Mario Zechner, “What I learned building an opinionated and minimal coding agent,” November 30, 2025. It argues for minimal APIs, minimal hidden context, and inspectable harness behavior. <https://mariozechner.at/posts/2025-11-30-pi-coding-agent/>

[^hermes_memory]: Hermes Agent docs, “Persistent Memory.” It documents bounded, curated memory across sessions. <https://hermes-agent.nousresearch.com/docs/user-guide/features/memory/>

[^hermes_docs]: Hermes Agent docs home. It highlights memory, skills, MCP integration, messaging gateway, and SOUL.md. <https://hermes-agent.nousresearch.com/docs/>

[^openclaw_docs]: OpenClaw docs home. It highlights the gateway as the source of truth, multi-agent routing, and a web control UI. <https://docs.openclaw.ai/>

[^openclaw_multi]: OpenClaw docs, “Multi-Agent Routing.” It documents per-agent isolated workspaces with `SOUL.md` and `AGENTS.md`. <https://docs.openclaw.ai/concepts/multi-agent>

[^autoresearch]: karpathy/autoresearch README. It frames `program.md` as the thing the human “programs” to define the autonomous research org. <https://github.com/karpathy/autoresearch>

[^codex_skills]: OpenAI Codex docs, “Agent Skills.” It documents progressive disclosure, where only skill metadata is loaded initially and full instructions are loaded on demand. <https://developers.openai.com/codex/skills/>

[^hive_readme]: Current `intertwine/hive-orchestrator` README on `main`, describing Hive as a CLI-first orchestration platform with `.hive/` canonical state and `PROGRAM.md` policy. <https://raw.githubusercontent.com/intertwine/hive-orchestrator/main/README.md>

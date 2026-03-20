# Agent Hive v2.3 Acceptance Tests and Release Gates

Status: Active scope-locked release-gate reference  
Date: 2026-03-17

This document is the active acceptance companion to `docs/V2_3_STATUS.md`. When older RFC language and the scoped
release ledger disagree, follow the scope-locked truth in `docs/V2_3_STATUS.md`.

## 1. North-star release scenario

One operator supervises:
- 3 projects
- 10 concurrent runs
- across Codex, Claude, and one deterministic local helper
- from one console and one CLI
- with one unified inbox for approvals and escalations

Scope-locked v2.3 note:
- Pi remains available as an honest staged driver, but full Pi RPC depth is deferred from this
  release line.

The release passes only if the operator can:
- see all runs on one board
- inspect effective capabilities for each run
- inspect sandbox backend and policy for each run
- approve or decline at least two upstream driver approval requests
- interrupt one run
- reroute one run or relaunch it on another harness with lineage preserved
- inspect why a campaign launched a specific run
- inspect retrieval explanations for at least one run
- inspect evaluator evidence for every accepted run

## 2. Mandatory release gates

## Gate A — Runtime depth

Scope-locked v2.3 note:
- Codex and Claude are the mandatory deep-driver gates for this release.
- Pi remains non-blocking for the scoped v2.3 release as long as the staged driver stays truthful.

### Codex
- [ ] `hive driver doctor` reports Codex `app_server` availability accurately
- [ ] Hive can launch an interactive Codex run through app-server
- [ ] Codex approval prompts land in Hive inbox
- [ ] Hive can respond and continue the run
- [ ] Hive can interrupt a Codex turn
- [ ] `codex exec` fallback works for non-interactive runs

### Claude
- [ ] `hive driver doctor` reports Claude SDK availability accurately
- [ ] Hive can launch an interactive Claude run through `ClaudeSDKClient`
- [ ] permission prompts or denials are handled through Hive policy/approval flow
- [ ] Hive can interrupt a Claude run
- [ ] session continuity is visible in run detail

### Manual / staged
- [ ] staged driver does not claim streaming/resume/subagents as effective
- [ ] console hides controls that the staged driver cannot support

### Pi (deferred from the v2.3 release bar)
- [ ] `hive driver doctor` reports Pi RPC availability accurately
- [ ] Hive can launch Pi in RPC mode
- [ ] Hive can ingest normalized events from Pi
- [ ] Hive can terminate a Pi run cleanly

## Gate B — Capability truthfulness

- [ ] every new run writes `capability-snapshot.json`
- [ ] snapshot has `declared`, `probed`, `effective`, and `evidence`
- [ ] console displays `effective` capabilities, not `declared`
- [ ] driver doctor explains blockers with actionable text
- [ ] staged driver notes and effective capabilities do not contradict each other

## Gate C — Sandbox depth

### Local
- [ ] Podman backend works in at least one CI-supported Linux environment
- [ ] docs cover macOS/Windows via `podman machine`
- [ ] Docker rootless backend works when configured
- [ ] ASRT wrapper mode works for wrapped subprocess cases

### Hosted / self-hosted
Scope-locked v2.3 note:
- E2B is release-accepted as an ephemeral upload-only hosted path.
- E2B pause/resume and downloaded artifact sync are deferred from this release line.
- Daytona remains release-accepted as an ephemeral upload-only self-hosted path once the real-environment proof is run.

- [ ] E2B backend can create an ephemeral sandbox, upload the worktree/artifacts directories, run a bounded command, and return stdout/stderr/exit status
- [ ] E2B truthfully documents that session pause/resume and downloaded artifact sync are not yet wired
- [ ] Daytona backend can create an ephemeral sandbox from a snapshot or base image and run code
- [ ] Daytona truthfully documents upload-only sync and the current mount/network limits
- [ ] sandbox doctor reports backend availability accurately

### Policy
- [ ] default network is deny
- [ ] network allowlist exceptions are logged
- [ ] default env inheritance is off
- [ ] worktree-only mount policy is enforced by default
- [ ] every run records sandbox backend and policy

## Gate D — Retrieval

- [ ] installed package includes docs/examples/recipes search corpus
- [ ] `hive search` on installed package is materially useful without source checkout
- [ ] canonical task files outrank projections on exact task queries
- [ ] `PROGRAM.md` outranks general docs on policy queries
- [ ] accepted run summaries outrank raw transcript chunks on history queries
- [ ] duplicate hits collapse
- [ ] retrieval explanations are shown
- [ ] retrieval traces are written for every context compilation

## Gate E — Campaign orchestration

- [ ] campaigns have a type and policy
- [ ] candidate scoring logs component scores
- [ ] delivery and research campaigns choose differently on the same fixture set
- [ ] duplicate/overlap penalty prevents obvious redundant launches
- [ ] campaign brief explains what changed and why Hive recommends the next step
- [ ] operator can inspect selected candidate and rejected alternatives

## Gate F — Console and operator UX

- [ ] home view answers:
  - [ ] what is running now?
  - [ ] what is blocked?
  - [ ] what needs me?
  - [ ] what changed?
  - [ ] what should I do next?
- [ ] inbox supports approvals and escalations
- [ ] run detail shows:
  - [ ] timeline
  - [ ] driver details
  - [ ] capability snapshot
  - [ ] sandbox policy
  - [ ] retrieval inspector
  - [ ] artifacts and diff
  - [ ] evaluator output
  - [ ] steering history
- [ ] campaign view shows lanes and candidate reasoning

## 3. Truthfulness failure conditions

The release automatically fails if any of the following are observed:

- [ ] a staged driver renders pause/resume/streaming controls it cannot support
- [ ] a run claims sandbox protection that is not actually configured
- [ ] the console cannot tell the operator which backend protected the run
- [ ] the operator cannot tell whether a capability is declared, probed, or effective
- [ ] a campaign launch lacks a machine-readable decision log
- [ ] retrieval results lack provenance or explanations
- [ ] installed search is obviously worse than source-checkout search because docs were not packaged

## 4. Performance guardrails

These are pragmatic local-product targets, not hard real-time guarantees.

- [ ] run board loads in under 2 seconds on a typical local dev machine with 1,000 events
- [ ] capability inspector opens in under 500 ms after cached load
- [ ] retrieval first results appear in under 1 second on warm cache
- [ ] context compilation finishes in under 3 seconds for normal repos
- [ ] campaign brief generation finishes in under 30 seconds for 3 medium projects
- [ ] approval actions reflect in UI in under 1 second after response

## 5. Security guardrails

- [ ] sandbox policy violations are logged as events
- [ ] no default profile mounts home, SSH, or cloud credentials
- [ ] no default profile inherits the entire environment
- [ ] local-fast profile is explicitly labeled weaker than local-safe
- [ ] experimental backends are visibly labeled experimental in docs and doctor output

## 6. Fixture-based acceptance scenarios

## Scenario 1 — Codex interactive approval
- launch a Codex run that tries a command requiring approval
- ensure Hive inbox receives the request
- approve once
- ensure run completes and transcript/diff are stored

## Scenario 2 — Claude interrupt and resume-like follow-up
- launch a long Claude run
- interrupt it from console
- add steering note
- continue in same session or relaunch with preserved lineage
- confirm run detail shows both steps clearly

## Scenario 3 — Pi headless scripted run (deferred from the scoped v2.3 release bar)
- launch a Pi run in RPC mode
- capture transcript and event stream
- inspect capability snapshot
- terminate cleanly

## Scenario 4 — Sandbox deny-by-default
- attempt outbound network on local-safe
- verify denial and event log
- allow a domain via policy exception
- verify allowlisted access only

## Scenario 5 — Delivery vs research campaign
- run both campaign types on identical fixture workspace
- verify delivery chooses exploit-heavy launch set
- verify research chooses at least one explore lane candidate
- inspect decision logs

## Scenario 6 — Retrieval provenance
- ask a policy question
- confirm top result is from `PROGRAM.md`
- inspect explanation and retrieval trace
- confirm selected chunks appear in context manifest

## 7. Release checklist

### Product
- [ ] README and website copy emphasize “observe-and-steer control plane”
- [ ] compare-harness docs are truthful and current
- [ ] sandbox docs explain profiles clearly
- [ ] a demo video or fixture walkthrough exists for multi-project, multi-harness oversight

### Engineering
- [ ] driver conformance tests pass
- [ ] sandbox conformance tests pass
- [ ] retrieval benchmark thresholds are met
- [ ] campaign simulation tests pass
- [ ] console smoke tests pass

### Docs
- [ ] install docs cover optional extras
- [ ] driver doctor docs exist
- [ ] sandbox doctor docs exist
- [ ] operator docs explain capability inspector, retrieval inspector, and campaign inspector

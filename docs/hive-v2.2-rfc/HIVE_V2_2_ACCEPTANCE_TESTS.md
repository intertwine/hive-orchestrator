# Hive 2.2 Acceptance Tests and Launch Checklist

Status: Live release checklist  
Date: 2026-03-17

This is the working release checklist for Hive 2.2. Checked items have direct proof in tests, docs,
or launch collateral already in the repo. Unchecked items are real remaining work, not placeholders.

## 1. North-star acceptance test

**Scenario:** One operator supervises three projects with ten concurrent runs across Codex, Claude
Code, and local/manual execution, using one console, one inbox, and one audit trail.

Current status: covered by `tests/test_v22_acceptance.py`.

Pass if:

- [x] all ten runs are visible in a unified run board
- [x] at least two require approval and land in the inbox
- [x] one run is rerouted to another driver without losing lineage
- [x] one campaign produces a daily brief
- [x] every accepted run shows evaluator evidence and compiled context manifest

## 2. Milestone-by-milestone test plan

## M1 — Contract freeze

- [x] Driver names, states, event types, and steering verbs are frozen
- [x] CLI JSON schemas validated in fixtures
- [x] UI IA documented
- [x] Operator flows documented

## M2 — Universal drivers

- [x] `hive drivers list --json` shows `local`, `manual`, `codex`, `claude-code`
- [x] Same task launches successfully on `codex` and `claude-code`
- [x] Normalized artifacts exist for all supported drivers
- [x] Driver conformance tests pass in CI

## M3 — Observe Console

- [x] Home answers the five core operator questions
- [x] Runs board supports project, driver, and health filtering
- [x] Inbox updates without manual sync
- [x] Run detail shows timeline, logs, diff, eval, context, steering history
- [x] Operator can monitor 10 runs across 3 projects in one browser session

## M4 — Steer Console + Program Doctor

- [ ] Pause/resume/cancel actions work from UI and CLI
- [x] Reroute works at least between `local`, `codex`, and `claude-code` at metadata/transcript level
- [x] Program Doctor suggests evaluator templates based on project stack
- [x] Autonomous promotion is blocked until required evaluator gates exist
- [ ] Every steering action emits an event and appears in timeline

## M5 — Context, memory, search, skills

- [x] Every run has a context manifest
- [x] Inspector shows included memory, skills, and search hits
- [x] Memory delta review supports accept/reject
- [x] Search works in installed package without source checkout
- [x] Duplicate search hits collapse and canonical docs outrank projections

## M6 — Campaigns, scheduling, launch polish

- [x] Campaign can launch recurring runs
- [x] Daily brief is generated and searchable
- [x] `hive onboard` takes a new user from install to first run in under 10 minutes
- [x] `hive adopt` can initialize a repo with at least one safe default program
- [x] Demo script runs end-to-end on recorded fixtures

## 3. UX heuristics

These are failure conditions, not work items. A checked line here means the failure mode is not true.

The release fails if any of the following are true:

- [x] The primary dashboard still relies on a manual sync button
- [x] The user must inspect raw markdown to know what needs attention
- [x] Accepted runs cannot explain why they were accepted
- [x] Users cannot tell what context was loaded
- [x] Search is materially better in source checkout than in installed CLI
- [x] Steering exists only as freeform notes, not typed actions

## 4. Performance / quality guardrails

- [x] Home page usable with 1,000+ events in store
- [x] Run detail opens in under 2 seconds on common local setups
- [x] Event stream recoverable after browser refresh
- [x] Context compilation completes in under 3 seconds for normal repos
- [x] Search returns first results in under 1 second on warm cache
- [x] Brief generation completes in under 30 seconds for a 3-project portfolio

## 5. Launch checklist

### Product

- [x] Website/README tagline uses “control plane” / “command center” language
- [x] Comparison page explains relation to Codex, Claude Code, and local harnesses
- [x] Demo video shows multi-project observe-and-steer flow
- [x] Screenshots show inbox, runs board, and context inspector

### Docs

- [x] Quickstart teaches `onboard` / `adopt`
- [x] Harness pages exist for Codex and Claude Code
- [x] Driver development guide exists
- [x] Program Doctor docs exist
- [x] Campaigns and briefs docs exist

### Engineering

- [x] CI runs driver conformance fixtures
- [x] UI routes covered by smoke tests
- [x] Event schema fixtures versioned
- [x] Migration notes from v2.1 documented
- [x] Package includes docs/recipes corpus

## 6. Remaining release work

What is still open is small and concrete:

- browser-level proof for the full pause/resume/cancel steering loop
- browser-level proof that every steering action shows up in the visible timeline, not just reroute
- the final PR / review / merge path for the release-proof branch itself

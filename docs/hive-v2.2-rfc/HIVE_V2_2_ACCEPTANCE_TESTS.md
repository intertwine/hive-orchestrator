# Hive 2.2 Acceptance Tests and Launch Checklist

Status: Proposed  
Date: 2026-03-15

## 1. North-star acceptance test

**Scenario:** One operator supervises three projects with ten concurrent runs across Codex, Claude Code, and local/manual execution, using one console, one inbox, and one audit trail.

Pass if:

- all ten runs are visible in a unified run board
- at least two require approval and land in the inbox
- one run is rerouted to another driver without losing lineage
- one campaign produces a daily brief
- every accepted run shows evaluator evidence and compiled context manifest

## 2. Milestone-by-milestone test plan

## M1 — Contract freeze

- [ ] Driver names, states, event types, and steering verbs are frozen
- [ ] CLI JSON schemas validated in fixtures
- [ ] UI IA documented
- [ ] Operator flows documented

## M2 — Universal drivers

- [ ] `hive drivers list --json` shows `local`, `manual`, `codex`, `claude-code`
- [ ] Same task launches successfully on `codex` and `claude-code`
- [ ] Normalized artifacts exist for all supported drivers
- [ ] Driver conformance tests pass in CI

## M3 — Observe Console

- [ ] Home answers the five core operator questions
- [ ] Runs board supports project, driver, and health filtering
- [ ] Inbox updates without manual sync
- [ ] Run detail shows timeline, logs, diff, eval, context, steering history
- [ ] Operator can monitor 10 runs across 3 projects in one browser session

## M4 — Steer Console + Program Doctor

- [ ] Pause/resume/cancel actions work from UI and CLI
- [ ] Reroute works at least between `local`, `codex`, and `claude-code` at metadata/transcript level
- [ ] Program Doctor suggests evaluator templates based on project stack
- [ ] Autonomous promotion is blocked until required evaluator gates exist
- [ ] Every steering action emits an event and appears in timeline

## M5 — Context, memory, search, skills

- [ ] Every run has a context manifest
- [ ] Inspector shows included memory, skills, and search hits
- [ ] Memory delta review supports accept/reject
- [ ] Search works in installed package without source checkout
- [ ] Duplicate search hits collapse and canonical docs outrank projections

## M6 — Campaigns, scheduling, launch polish

- [ ] Campaign can launch recurring runs
- [ ] Daily brief is generated and searchable
- [ ] `hive onboard` takes a new user from install to first run in under 10 minutes
- [ ] `hive adopt` can initialize a repo with at least one safe default program
- [ ] Demo script runs end-to-end on recorded fixtures

## 3. UX heuristics

The release fails if any of the following are true:

- [ ] The primary dashboard still relies on a manual sync button
- [ ] The user must inspect raw markdown to know what needs attention
- [ ] Accepted runs cannot explain why they were accepted
- [ ] Users cannot tell what context was loaded
- [ ] Search is materially better in source checkout than in installed CLI
- [ ] Steering exists only as freeform notes, not typed actions

## 4. Performance / quality guardrails

- [ ] Home page usable with 1,000+ events in store
- [ ] Run detail opens in under 2 seconds on common local setups
- [ ] Event stream recoverable after browser refresh
- [ ] Context compilation completes in under 3 seconds for normal repos
- [ ] Search returns first results in under 1 second on warm cache
- [ ] Brief generation completes in under 30 seconds for a 3-project portfolio

## 5. Launch checklist

### Product

- [ ] Website/README tagline uses “control plane” / “command center” language
- [ ] Comparison page explains relation to Codex, Claude Code, and local harnesses
- [ ] Demo video shows multi-project observe-and-steer flow
- [ ] Screenshots show inbox, runs board, and context inspector

### Docs

- [ ] Quickstart teaches `onboard` / `adopt`
- [ ] Harness pages exist for Codex and Claude Code
- [ ] Driver development guide exists
- [ ] Program Doctor docs exist
- [ ] Campaigns and briefs docs exist

### Engineering

- [ ] CI runs driver conformance fixtures
- [ ] UI routes covered by smoke tests
- [ ] Event schema fixtures versioned
- [ ] Migration notes from v2.1 documented
- [ ] Package includes docs/recipes corpus

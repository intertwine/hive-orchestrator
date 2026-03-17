# Hive 2.2 Implementation Status

Last updated: 2026-03-17

This note tracks what is already real on `main`, what the current branch is proving, and what still
has to happen before we can call Hive 2.2 ready.

## Current read

Hive 2.2 is no longer an architecture project. The control-plane model, driver layer, React observe
console, Program Doctor, campaigns, onboarding, adoption, memory review, launch walkthrough, and
demo collateral are all real now.

The center of gravity has shifted again. The main job is release proof:

- freeze the manager-loop and driver contracts in durable fixtures
- close the last browser-level console proofs
- keep the acceptance checklist honest enough that a 2.2 release call is based on evidence, not mood

## Validation snapshot

Current working branch:

- `codex/hive-v2-2-release-proof`

Latest local validation on this branch:

- `UV_PYTHON=3.11 uv run --extra dev pytest tests/test_cli_schema_fixtures.py tests/test_hive_drivers.py -q`
- `cd frontend/console && pnpm test`
- `cd frontend/console && pnpm build`

Latest result:

- manager-loop CLI JSON contracts are now fixture-backed
- the same run can move from `local` to `codex` to `claude-code` without losing lineage
- the React console run-detail view survives a browser refresh and refetches cleanly

## What is already on main

PRs `#99` through `#103` established the release-grade surface:

- the v2.2 control-plane foundations
- the React observe console cutover
- acceptance-harness coverage for the north-star operator scenario
- browser-smoke coverage for the console routes
- launch collateral, screenshots, and the reusable demo workspace

That means the current branch is not doing more feature expansion. It is closing the last proof gaps
around contracts, cross-driver lineage, and refresh resilience.

## What this branch adds

- fixture-backed schema coverage for the manager loop:
  - `hive drivers list`
  - `hive next`
  - `hive work`
  - `hive finish`
  - `hive portfolio status`
  - `hive campaign create`
  - `hive brief daily`
  - `hive program doctor`
- a stronger cross-driver reroute proof that the same governed run can move across `local`,
  `codex`, and `claude-code`
- explicit browser-refresh proof for the run-detail timeline and inspector view

## Milestone status

### M1 — Contract freeze

Status: done

Strong signals:

- driver names, event vocabulary, and steering verbs are versioned
- event schema fixtures exist
- UI information architecture is documented
- operator flows are documented
- manager-loop CLI payloads are fixture-backed on this branch

### M2 — Universal drivers

Status: done

Strong signals:

- `local`, `manual`, `codex`, and `claude-code` all go through the same driver layer
- normalized artifacts exist across supported drivers
- reroute lineage is implemented and tested
- CI already runs driver-conformance coverage
- this branch strengthens the proof by moving one run across `local -> codex -> claude-code`

### M3 — Observe Console

Status: done

Strong signals:

- the React/Vite console is the real product surface
- the console API exposes home, inbox, runs, projects, campaigns, search, and run detail
- run detail includes timeline, steering history, eval evidence, context manifest, and artifact
  previews
- the north-star acceptance harness proves one operator can watch ten runs across three projects
- this branch adds explicit browser-refresh recovery for run detail

### M4 — Steer Console + Program Doctor

Status: mostly done

Strong signals:

- pause, resume, cancel, approve, reject, and reroute are typed steering actions
- reroute lineage and steering timelines are covered in backend and console tests
- Program Doctor is implemented, documented, and tested
- autonomous promotion is blocked until required evaluator gates exist

Remaining work:

- add one explicit browser-level proof for the full pause/resume/cancel loop if we decide that final
  UI evidence is worth a separate tiny follow-up

### M5 — Context, memory, search, skills

Status: done

Strong signals:

- every governed run emits a context manifest
- the inspector shows memory, skills, search hits, and outputs
- memory review supports propose, accept, and reject
- installed-package search keeps the docs and recipe corpus
- duplicate search hits collapse and canonical task hits outrank projections

### M6 — Campaigns, scheduling, launch polish

Status: done

Strong signals:

- `hive onboard` and `hive adopt` are both real and documented
- campaigns can launch recurring governed work
- daily briefs are generated, indexed, and searchable
- the demo workspace builder and walkthrough collateral are checked in
- launch-facing README and docs now consistently describe Hive as the control plane above the worker

## Acceptance summary

### Clear passes

- the north-star three-project / ten-run scenario
- inbox refresh without manual sync
- evaluator evidence and context manifests on accepted runs
- installed search parity with the packaged docs corpus
- duplicate-hit collapse and task-first ranking
- launch screenshots, demo clip, and walkthrough fixture

### Honest remaining gap

The one acceptance item I would still call “nice to close” rather than “already airtight” is
browser-level proof for every steering button, not just the run-detail observe-and-reroute path. The
underlying steering model is there and well-covered in backend tests. This is about polishing the last
bit of UI proof, not fixing a product hole.

## Recommended next step

Land this release-proof branch, then make one deliberate decision:

1. either ship 2.2 from there if we are comfortable with the current UI steering evidence
2. or do one last tiny console-proof PR for pause/resume/cancel and then cut the release

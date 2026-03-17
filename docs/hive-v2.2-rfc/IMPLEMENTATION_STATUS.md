# Hive 2.2 Implementation Status

Last updated: 2026-03-17

This note tracks where the implementation stands while the work is being split into reviewable PRs.

## Current read

Hive 2.2 is still on the same track: the architecture is in place, and the product now feels like one
coherent system instead of a stack of experiments. The control-plane substrate, driver layer, steering
model, Program Doctor, campaigns, onboarding, memory review, and React observe console are all real on
`main`.

The center of gravity has shifted to release proof:

- shipping the acceptance harness and the remaining release-grade proofs
- finishing the last console / search / launch polish gaps that only show up in end-to-end scenarios
- producing launch collateral such as screenshots and demo assets

## Validation snapshot

Current working branch:

- `codex/hive-v2-2-acceptance-proof`

Latest local validation on this branch:

- `UV_PYTHON=3.11 uv run --extra dev pytest -q`
- `PYLINTHOME=$(mktemp -d) UV_PYTHON=3.11 make lint`

Latest result:

- `419 passed, 1 warning`
- pylint `9.43/10`

## Recent progress

- PR #99 and PR #100 are merged, so the v2.2 foundations and React console cutover are now on `main`.
- The first release-proof pass is in progress on `codex/hive-v2-2-acceptance-proof`.
- The new acceptance tests now cover:
  - the north-star three-project / ten-run operator scenario
  - inbox updates without manual sync
  - duplicate-hit collapse for task search
  - timing guardrails for home, run detail, context build, search, brief generation, and the
    onboard-to-first-run path
- That pass also found and fixed two real search bugs:
  - `workspace` scope was not expanding to workspace docs
  - greenfield repos without a `docs/` directory were skipping `.hive/briefs` and `.hive/campaigns`
    in cache indexing

## Milestone status

### M1 — Contract freeze

Status: mostly done

Strong signals:

- driver names, event vocabulary, and steering verbs are versioned
- event schema fixtures exist
- UI information architecture is documented
- operator flows are documented

Remaining work:

- tighten the CLI schema-proof story so more command payloads are checked as fixtures instead of only by behavior tests

### M2 — Universal drivers

Status: mostly done

Strong signals:

- `local`, `manual`, `codex`, and `claude-code` are exposed through the driver layer
- normalized run artifacts exist across drivers
- reroute lineage is implemented and tested
- CI already has a dedicated driver-conformance job

Remaining work:

- add one stronger acceptance-style proof for cross-driver launch and reroute behavior, not just fixture-level tests

### M3 — Observe Console

Status: mostly done

Strong signals:

- React/Vite console exists and builds into packaged assets
- console API exposes home, inbox, runs, projects, campaigns, search, and run detail
- run detail includes context, steering history, evaluator evidence, and artifact previews

Remaining work:

- add a little more browser-level proof around the observe console, not just API/state coverage

### M4 — Steer Console + Program Doctor

Status: mostly done

Strong signals:

- pause, resume, cancel, approve, reject, and reroute are typed actions
- steering events land in timelines
- Program Doctor is implemented and tested
- autonomous promotion is blocked until required evaluator gates exist

Remaining work:

- deepen UI-level proof for steering actions in the console, not just CLI and API tests

### M5 — Context, memory, search, skills

Status: mostly done

Strong signals:

- runs compile a context manifest and run brief
- memory review supports propose, accept, and reject
- installed-package search fallback works without a source checkout
- search ranking already prefers canonical task hits over projections

Remaining work:

- keep improving inspector polish and search explanations

### M6 — Campaigns, scheduling, launch polish

Status: partial to mostly done

Strong signals:

- `hive onboard` and `hive adopt` are implemented
- campaigns and briefs are implemented
- daily brief generation is tested
- the public product story is moving toward the React console and manager loop

Remaining work:

- record an end-to-end demo script on fixtures
- finish launch collateral

## Acceptance checklist summary

### Clear passes

- event schema fixtures are versioned
- driver conformance runs in CI
- Quickstart teaches `onboard`
- adoption docs teach `adopt`
- Program Doctor docs exist
- campaigns and briefs docs exist
- package includes the docs and recipe corpus needed by the installed search path
- accepted runs can explain why they were accepted
- users can inspect what context was loaded
- steering is typed, not just freeform notes

### Likely passes, but still need a little more release-proof coverage

- home answers the five operator questions
- run detail shows the right evidence
- campaigns can launch recurring work
- installed search is no longer materially weaker than source-checkout search
- operator can monitor the console comfortably at release scale

### Still open

- launch screenshots and demo assets
- a recorded demo script / fixture walkthrough
- any browser-level console smoke coverage we still decide we want before release

## Recommended PR stack

### PR 1 — Core control-plane backend

Put the backend foundations up first:

- drivers
- normalized run and event contracts
- Program Doctor
- graph intelligence
- campaigns, onboarding, and memory review backend
- CI and schema fixtures

### PR 2 — Observe Console UI

Then layer on the React product surface:

- frontend console
- packaged console assets
- run detail inspector polish
- console route smoke tests

### PR 3 — Console-first product cutover

Then land the public story:

- README and install docs
- maintainer docs
- Makefile and packaging language
- Streamlit deprecation / compatibility shim cleanup

## What remains after the first PR batch

Now that the first batch is merged, the highest-value follow-up is the release-proof pass:

1. finish the acceptance-proof PR and get it reviewed
2. add any last browser-level console smoke coverage we decide is worth the complexity
3. produce launch screenshots and a demo flow
4. polish the public launch package

# Hive v2.2.4 Onboarding Polish

Archived note: kept as reference material after the v2.3 onboarding and release-doc cleanup. Prefer the active
public docs in `README.md`, `docs/START_HERE.md`, `docs/QUICKSTART.md`, and `docs/V2_3_STATUS.md` for current
guidance.

Status: draft
Date: 2026-03-18
Source: Claude Code re-evaluation after v2.2.3

## Purpose

Record the onboarding work that still feels worth doing after the v2.2.3 patch
fully cleaned up the original onboarding issues from the v2.2.2 re-audit.

This is no longer a "fix the broken path" document. The happy path is working.
This is a small future polish queue for making the first-run experience more
comfortable and more convincing.

## v2.2.3 re-evaluation summary

The onboarding flow is now solid:

`git init` -> `hive onboard demo` -> `hive next` -> `hive work` -> `hive finish`

Claude's re-evaluation confirmed that every v2.2.2 follow-up item was addressed
in v2.2.3:

- `hive --help` now promotes `onboard` without surfacing `quickstart`
- `hive program doctor` pass output now explains what is configured
- onboard output now explains that `local-smoke` proves the loop is wired up,
  but does not validate real project behavior
- starter `PROGRAM.md` constraints now read like user guidance instead of
  internal maintainer notes
- docs now call out the `mellona-hive[console]` requirement anywhere they lead
  users to `hive console serve`

Overall assessment:

- a new user can reach a working governed loop without hand-editing config files
- the remaining gaps are polish, not blockers

## Proposed v2.2.4 polish scope

### 1. Improve task ID ergonomics

Problem:
Task ULIDs are still awkward to type and remember in direct CLI workflows.

Possible patch targets:

- add `hive work --next`
- add short task aliases in list output
- improve shell completion support for task IDs

Acceptance:

- a user can move from `hive next` or task listings into `hive work` without
  copying a long ULID by hand

### 2. Ship more starter evaluator templates

Problem:
`local-smoke` is useful as a bootstrap check, but it is still the only starter
template. That makes the evaluator story feel thinner than it needs to.

Possible patch targets:

- add starter templates for common workflows such as `pytest`, `ruff`, or
  `make test`
- make template selection clearer during onboarding or program setup
- keep `local-smoke` as the "prove the loop works" option, not the only option

Acceptance:

- a new user can pick a starter evaluator that resembles real project checks
  without writing custom config first

### 3. Show a clearer path to a successful demo finish

Problem:
The default demo still rejects `hive finish` unless the run produced workspace
changes. That behavior is correct, but the first-run path does not yet make it
obvious how to see a successful promotion.

Possible patch targets:

- add explicit onboarding guidance to make a small change before `hive finish`
- suggest safe demo edits in `docs/` or `src/` that produce a successful finish
- explain that a rejection here usually means "nothing changed", not "the loop
  is broken"

Acceptance:

- a first-time user can intentionally experience both a noop rejection and a
  successful finish without confusion

## Explicitly out of scope

These still belong to the broader v2.3 line rather than a patch polish pass:

- deeper runtime adapter work
- new sandbox backends
- hybrid retrieval redesign
- larger campaign and portfolio policy changes
- broader console product expansion

## Suggested acceptance checklist

Before shipping a v2.2.4 onboarding polish patch, verify:

1. a user can claim work without manually copying a long task ULID
2. starter evaluator options include at least one realistic project-check
   template in addition to `local-smoke`
3. the onboarding story explains how to reach a successful `hive finish`, not
   only how noop rejection works

## Recommendation

Do not treat these as urgent. v2.2.3 already delivered the onboarding repair
pass successfully.

Treat this document as a small optional v2.2.4 queue if we want one more
usability-focused patch before the broader v2.3 work.

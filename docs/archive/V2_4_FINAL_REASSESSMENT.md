# Hive v2.4 Final Reassessment

Archived note: kept as the post-implementation reassessment after the v2.4 sprint landed. Prefer
`docs/V2_4_STATUS.md` for live release truth, and `docs/AUTONOMY_GAP_ANALYSIS.md` plus
`docs/AUTONOMY_V2_5_PLAN.md` for current autonomy follow-up.

Date: 2026-03-30
Scope: Post-`#179` re-audit of the shipped v2.4 line on `main`

## Verdict

v2.4 is functionally complete against the RFC acceptance bar in
`docs/hive-v2.4-rfc/HIVE_V2_4_ACCEPTANCE_TESTS.md`.

The remaining items that were still under debate after the M5 merges are not
implementation blockers. They are surface-shape or ergonomics follow-ups that
fit better as v2.5 work.

The one real issue this reassessment did find was truth drift in the maintainer
surfaces: the repo still said M5 was next even though the M5 PRs had already
merged. That is a substrate/docs synchronization problem, not a missing v2.4
feature.

## What Passed The Reassessment

- Gate 1: adapter-family split is real in code and docs.
- Gate 2: Pi, OpenClaw, and Hermes all have native-first onboarding paths in the
  shipped docs.
- Gate 3: attach without relaunch is implemented for Pi, OpenClaw, and Hermes,
  and console visibility is covered by the landed console proof.
- Gate 4: advisory versus governed truth is visible in detail views, doctor
  payloads, and persisted artifacts.
- Gate 5: normalized `trajectory.jsonl` artifacts exist across the shipped
  managed and attached flows.
- Gate 6: companion intent coverage is functionally complete.

## Genuine Remaining Work

These are still real, but they do not block v2.4 implementation completion:

- Release execution is still pending. The repo version is still `2.3.2`, so the
  actual `v2.4` cut remains a version/tag/publish/release-notes workflow.
- Maintainer truth surfaces needed cleanup so the task graph, projections, and
  compact ledger match the already-merged state.

## Not Blockers

These came up in the post-M5 discussion, but they do not fail the RFC gates:

- `hive_open` intent for OpenClaw and Hermes. Those harnesses are intentionally
  attach-first or attach-only in v2.4, and the public docs describe them that
  way.
- `hive link serve` CLI wiring. `LinkServer` exists, but a top-level parser entry
  is an optional operator surface, not a release gate.
- top-level `hive attach` / `hive detach` aliases. `hive integrate attach` and
  `hive integrate detach` are the supported v2.4 surfaces and satisfy the
  documented workflows.
- dedicated `/delegates` or standalone `/trajectory` endpoints. Delegate sessions
  and trajectory data are already visible through the merged `/runs` detail path,
  which is what the acceptance scenarios actually require.

## Recommendation Before External Assessment

Treat v2.4 implementation as complete, but hand external reviewers a repo state
that is truthful about that completion:

1. keep the maintainer ledger and project projections synchronized
2. distinguish implementation completion from release publication
3. treat the remaining surface-level ideas as explicit v2.5 candidates rather
   than hidden “maybe still open” release debt

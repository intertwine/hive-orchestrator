---
priority: 2
project_id: hive-v24
status: active
---

# Hive v2.4 Ecosystem Integrations

## Mission
Deliver the v2.4 ecosystem-integration line for Agent Hive: native Pi, OpenClaw,
and Hermes companion surfaces built on an adapter-family split, Hive Link, and
truthful advisory-vs-governed UX.

## Notes
- Primary planning bundle: `docs/hive-v2.4-rfc/`
- Scoped release ledger: `docs/V2_4_STATUS.md`
- Milestone order: wire docs/status -> adapter-model and Hive Link -> Pi -> OpenClaw -> Hermes -> launch polish
- Claude may be working in parallel from the same RFC; coordinate on canonical task claims and avoid overlapping slices

## Working Rules
- Keep canonical task state in `.hive/tasks/*.md`.
- Read `PROGRAM.md` before autonomous edits or evaluator runs.
- Refresh projections after state changes with `hive sync projections --json`.
- Claim the active slice before editing shared files so other agents can see the lease.

<!-- hive:begin task-rollup -->
## Task Rollup

| ID | Status | Priority | Owner | Title |
|---|---|---:|---|---|
| task_01KNHQ7V13BRKRVZ1KET19P061 | done | 0 | codex | Bump the package, release docs, and maintainer surfaces to v2.4.0 |
| task_01KNHQ747AB64PEEWXP9KD82Q4 | proposed | 0 |  | Execute the v2.4.0 release cut and public verification |
| task_01KNHQ8JR4QBA2NZQKDS0VN5KF | done | 0 | codex | Run full v2.4 release validation and fix any blocking regressions |
| task_01KNHQ9SAYDKWT4DWPFCPR990Q | claimed | 0 | codex | Tag, publish, and cut the public v2.4.0 release artifacts |
| task_01KNHQA4GRWBA7KKB4TMCNS94E | ready | 0 |  | Verify public install/search behavior and mark the v2.4 line as shipped |
| task_01KNHQADY83DG8C0GHSW3XWC41 | archived | 0 |  | Verify public install/search behavior and mark the v2.4 line as shipped |
| task_01KMY3WJJ0XANHDQHB6NY2HJ5S | done | 1 |  | Archive stale docs and maintenance artifacts for v2.4 assessment |
| task_01KMRWWXGA9XZZK6XBQPWE9HME | done | 1 |  | Implement Hermes companion and attach integration |
| task_01KMRWWPXX70HTCPZFKBG3E1TZ | done | 1 |  | Implement OpenClaw companion and Gateway attach integration |
| task_01KMRWWETVXHGSE293M2C3X9TC | done | 1 |  | Implement Pi companion, attach, and managed integration |
| task_01KMRWW8E64Q9GPDPWPRZZQ2Z5 | done | 1 |  | Land adapter-family split, Hive Link, and advisory truth surfaces |
| task_01KMRWW1YQ5MWC0NCVCYB4WNWC | done | 1 |  | Wire the v2.4 RFC/status bundle into repo docs, search, and packaging |
| task_01KMRWX2AP42JZ32GMBKQAQ8JE | done | 2 |  | Polish compare docs, demos, and release gates for v2.4 |
<!-- hive:end task-rollup -->

<!-- hive:begin recent-runs -->
## Recent Runs

| Run | Status | Task |
|---|---|---|
| No runs | - | - |
<!-- hive:end recent-runs -->

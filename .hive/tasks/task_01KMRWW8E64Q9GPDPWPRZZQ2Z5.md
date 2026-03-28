---
acceptance:
- WorkerSessionAdapter and DelegateGatewayAdapter base contracts exist with truthful
  capability modeling
- A dummy adapter can attach and stream normalized events
- Console and doctor surfaces distinguish advisory from governed truth
claimed_until: null
created_at: '2026-03-28T00:18:05.894735Z'
edges:
  blocks:
  - task_01KMRWWETVXHGSE293M2C3X9TC
  - task_01KMRWWPXX70HTCPZFKBG3E1TZ
  - task_01KMRWWXGA9XZZK6XBQPWE9HME
id: task_01KMRWW8E64Q9GPDPWPRZZQ2Z5
kind: task
labels: []
owner: null
parent_id: null
priority: 1
project_id: hive-v24
relevant_files:
- src/hive/integrations/base.py
- src/hive/integrations/models.py
- src/hive/link
- src/hive/trajectory
- docs/V2_4_STATUS.md
- docs/hive-v2.4-rfc/HIVE_V2_4_ADAPTER_MODEL_AND_LINK_SPEC.md
source: {}
status: ready
title: Land adapter-family split, Hive Link, and advisory truth surfaces
updated_at: '2026-03-28T00:30:20.702262Z'
---

## Summary
Milestone 1 foundation work from the v2.4 plan. M0 repo wiring is now in place.

## Notes
M0 is complete enough to build on: stable docs live at docs/hive-v2.4-rfc/ and docs/V2_4_STATUS.md, packaging includes are wired in pyproject.toml, packaged API search covers the v2.4 bundle via src/hive/search.py, and release-smoke/test coverage now proves a packaged v2.4 search hit. Do not begin OpenClaw or Hermes implementation until this foundation is stable.

## History
2026-03-28: M0 repo-wiring slice landed locally with packaging/search/tests support for the v2.4 bundle.

---
acceptance:
- "hive run start <task-id> --driver pi launches a real governed Pi-backed run with persisted trajectory.jsonl and steering.ndjson."
- "hive integrate attach pi <native-session-ref> --task-id <task-id> creates a real advisory Pi-backed run that keeps the native session handle and governance truth visible."
- "pi-hive open and pi-hive attach invoke the live Hive surfaces instead of placeholder errors."
- "Steering notes round-trip for both managed and attached Pi sessions."
claimed_until: null
created_at: '2026-03-28T00:18:12.443550Z'
edges:
  blocks:
  - task_01KMRWX2AP42JZ32GMBKQAQ8JE
id: task_01KMRWWETVXHGSE293M2C3X9TC
kind: task
labels:
- v2.4
- pi
owner: codex
parent_id: null
priority: 1
project_id: hive-v24
relevant_files:
- src/hive/drivers/pi.py
- src/hive/integrations/pi.py
- src/hive/integrations/pi_managed.py
- src/hive/cli/integrate.py
- packages/pi-hive/bin/pi-hive.js
- packages/pi-hive/bin/pi-hive-runner.js
- tests/test_v24_pi_runtime.py
source: {}
status: done
title: Implement Pi companion, attach, and managed integration
updated_at: '2026-03-28T06:35:00Z'
---

## Summary
Milestone 2 from the v2.4 implementation plan is now landed as a real end-to-end slice.

## Notes
Pi now ships as a real run driver plus worker-session integration:
- managed runs launch through the run lifecycle and a live `pi-hive-runner`
- advisory attach creates a real Pi-backed run instead of adapter-local scaffolding
- native `pi-hive open` / `pi-hive attach` wrappers are live
- steering and normalized trajectory artifacts persist for both modes

## History
- 2026-03-28T00:18:12.443550Z bootstrap created.
- 2026-03-28T06:35:00Z codex landed managed + attach completion, companion wrappers, and end-to-end Pi runtime tests.

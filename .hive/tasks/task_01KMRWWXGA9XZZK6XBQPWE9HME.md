---
acceptance: []
claimed_until: '2026-03-29T12:00:00Z'
created_at: '2026-03-28T00:18:27.466422Z'
edges:
  blocks:
  - task_01KMRWX2AP42JZ32GMBKQAQ8JE
id: task_01KMRWWXGA9XZZK6XBQPWE9HME
kind: task
labels: []
owner: claude
parent_id: null
priority: 1
project_id: hive-v24
relevant_files: []
source: {}
status: in_progress
title: Implement Hermes companion and attach integration
updated_at: '2026-03-28T00:19:12.194936Z'
---

## Summary
Milestone 4 from the v2.4 implementation plan.

acceptance:
- HermesGatewayAdapter implements DelegateGatewayAdapter with truthful doctor
- Hermes skill/toolset bundle with companion action wrappers
- Attach live session with normalized trajectory persistence
- Trajectory import fallback for offline sessions
- Memory privacy enforced — no bulk MEMORY.md/USER.md import
relevant_files:
- src/hive/integrations/hermes.py
- packages/hermes-skill/
- tests/test_v24_hermes.py

## Notes
M1 foundation stable. Building on DelegateGatewayAdapter pattern from OpenClaw.

## History
- 2026-03-28T00:18:27.466422Z bootstrap created.
- 2026-03-28: M4 implementation started — claimed by claude in worktree.

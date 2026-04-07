---
acceptance:
- The top operator actions are exposed through visible controls and a global command
  palette.
- Frontend action surfaces map to shared backend execution semantics rather than page-local
  bespoke handlers.
- Every action can expose explanation/provenance for why it is available.
claimed_until: '2026-04-07T07:32:07.531707Z'
created_at: '2026-04-06T15:45:00.975599Z'
edges: {}
id: task_01KNHQFZ1FE415P7TX42WRYKJD
kind: task
labels:
- ui
- actions
owner: codex
parent_id: task_01KNHQCCFAB4KWR88RGJX2JJTF
priority: 1
project_id: hive-v25
relevant_files:
- frontend/console/src
- src/hive/console/api.py
- src/hive/console/state.py
source: {}
status: done
title: Implement the shared action registry, action execution APIs, and command palette
updated_at: '2026-04-07T07:26:17.526152Z'
---

## Summary
Unify buttons, menus, keyboard shortcuts, palette actions, and deep links around one action vocabulary.

## Notes
- Imported or created by Hive 2.0.

## History
- 2026-04-06T15:45:00.975599Z bootstrap created.
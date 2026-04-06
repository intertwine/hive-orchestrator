---
acceptance:
- The top operator actions are exposed through visible controls and a global command
  palette.
- Frontend action surfaces map to shared backend execution semantics rather than page-local
  bespoke handlers.
- Every action can expose explanation/provenance for why it is available.
claimed_until: null
created_at: '2026-04-06T15:45:16.021164Z'
edges: {}
id: task_01KNHQGDQN66GEZ5M3HDAS0WC0
kind: task
labels:
- ui
- actions
owner: null
parent_id: task_01KNHQCCFAB4KWR88RGJX2JJTF
priority: 1
project_id: hive-v25
relevant_files:
- frontend/console/src
- src/hive/console/api.py
- src/hive/console/state.py
source: {}
status: archived
title: Implement the shared action registry, action execution APIs, and command palette
updated_at: '2026-04-06T15:53:45.772546Z'
---

## Summary
Unify buttons, menus, keyboard shortcuts, palette actions, and deep links around one action vocabulary.

## Notes
- Imported or created by Hive 2.0.

## History
- 2026-04-06T15:45:16.021164Z bootstrap created.
---
acceptance:
- The top operator actions are exposed through visible controls and a global command
  palette.
- Frontend action surfaces map to shared backend execution semantics rather than page-local
  bespoke handlers.
- Every action can expose explanation/provenance for why it is available.
claimed_until: null
created_at: '2026-04-06T15:46:44.483709Z'
edges: {}
id: task_01KNHQK443Q889CY875N9QB70Z
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
updated_at: '2026-04-06T15:54:09.504869Z'
---

## Summary
Unify buttons, menus, keyboard shortcuts, palette actions, and deep links around one action vocabulary.

## Notes
- Imported or created by Hive 2.0.

## History
- 2026-04-06T15:46:44.483709Z bootstrap created.
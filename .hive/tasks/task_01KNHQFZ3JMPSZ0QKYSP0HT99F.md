---
acceptance:
- Saved views survive restarts.
- Operator-local preferences are stored separately from canonical workspace state.
- Settings surfaces can read and update the persisted preferences model.
claimed_until: '2026-04-06T19:18:55.033063Z'
created_at: '2026-04-06T15:45:01.042859Z'
edges: {}
id: task_01KNHQFZ3JMPSZ0QKYSP0HT99F
kind: task
labels:
- preferences
owner: codex
parent_id: task_01KNHQCCFAB4KWR88RGJX2JJTF
priority: 1
project_id: hive-v25
relevant_files:
- frontend/console/src
- src/hive/console/api.py
source: {}
status: claimed
title: Add preferences, saved views, and operator-local state persistence
updated_at: '2026-04-06T18:18:55.033071Z'
---

## Summary
Persist density, theme, default page, filters, hidden columns, pinned panels, and saved views across restarts.

## Notes
- Imported or created by Hive 2.0.

## History
- 2026-04-06T15:45:01.042859Z bootstrap created.
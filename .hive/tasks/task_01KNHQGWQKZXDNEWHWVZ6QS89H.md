---
acceptance:
- Saved views survive restarts.
- Operator-local preferences are stored separately from canonical workspace state.
- Settings surfaces can read and update the persisted preferences model.
claimed_until: null
created_at: '2026-04-06T15:45:31.379942Z'
edges: {}
id: task_01KNHQGWQKZXDNEWHWVZ6QS89H
kind: task
labels:
- preferences
owner: null
parent_id: task_01KNHQCCFAB4KWR88RGJX2JJTF
priority: 1
project_id: hive-v25
relevant_files:
- frontend/console/src
- src/hive/console/api.py
source: {}
status: archived
title: Add preferences, saved views, and operator-local state persistence
updated_at: '2026-04-06T15:54:56.641927Z'
---

## Summary
Persist density, theme, default page, filters, hidden columns, pinned panels, and saved views across restarts.

## Notes
- Imported or created by Hive 2.0.

## History
- 2026-04-06T15:45:31.379942Z bootstrap created.
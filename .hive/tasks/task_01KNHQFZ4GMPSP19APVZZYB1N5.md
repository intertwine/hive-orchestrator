---
acceptance:
- Primary console flows no longer depend on manual full refresh for normal updates.
- Notification and activity surfaces can be driven from shared event primitives.
- The UI shows freshness honestly when data may be stale.
claimed_until: '2026-04-07T02:09:21.949697Z'
created_at: '2026-04-06T15:45:01.072618Z'
edges: {}
id: task_01KNHQFZ4GMPSP19APVZZYB1N5
kind: task
labels:
- realtime
owner: codex
parent_id: task_01KNHQCCFAB4KWR88RGJX2JJTF
priority: 1
project_id: hive-v25
relevant_files:
- src/hive/console/api.py
- frontend/console/src/hooks
- frontend/console/src/routes
source: {}
status: claimed
title: Add real-time event, notification, and freshness primitives for the browser
  console
updated_at: '2026-04-07T00:39:21.949745Z'
---

## Summary
Replace habitual refresh behavior with a visible-freshness event/update model suitable for browser and desktop shells.

## Notes
- Imported or created by Hive 2.0.

## History
- 2026-04-06T15:45:01.072618Z bootstrap created.
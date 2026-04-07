---
acceptance:
- Desktop deep links open the correct run/task/campaign context.
- Tray and native notifications can bring the operator to the relevant item and quit
  gracefully.
- The shell starts and stops the local daemon safely.
claimed_until: null
created_at: '2026-04-06T15:50:03.519191Z'
edges: {}
id: task_01KNHQS6FZW0PECASBK1NW0HWA
kind: task
labels:
- desktop
owner: null
parent_id: task_01KNHQE7RS8JDFC221XF3N5QGV
priority: 2
project_id: hive-v25
relevant_files:
- frontend/console
- src/hive/console
- docs/hive-post-v2.4-rfcs/docs/hive-v2.5-rfc/HIVE_V2_5_DESKTOP_SHELL_DECISION.md
source: {}
status: done
title: Add daemon lifecycle, tray, native notifications, and desktop deep-link handling
updated_at: '2026-04-07T10:08:40.328004Z'
---

## Summary
Implemented and merged in PR #204; local evaluators and post-merge main CI passed. The run's automatic finish path misclassified the slice as over budget because wall-clock elapsed time included review and CI wait time after implementation completed.

## Notes
- Imported or created by Hive 2.0.

## History
- 2026-04-06T15:50:03.519191Z bootstrap created.

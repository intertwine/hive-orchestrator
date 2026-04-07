---
acceptance:
- Search spans tasks, runs, docs, memory, recipes, campaigns, and delegates with previews
  and reasons for match.
- Projections are deduped or clearly explained rather than flooding the result list.
- Users can open results in the relevant page/context rather than reading raw IDs.
claimed_until: '2026-04-07T06:45:29.376865Z'
created_at: '2026-04-06T15:47:43.724753Z'
edges: {}
id: task_01KNHQMXZC3D86Z2JNPR29SQ81
kind: task
labels:
- search
owner: codex
parent_id: task_01KNHQD1FSKPPQGN4PXVCM6HCD
priority: 1
project_id: hive-v25
relevant_files:
- frontend/console/src/routes/SearchPage.tsx
- src/hive/console/api.py
- src/hive/search.py
source: {}
status: review
title: Upgrade search to explainable unified provenance with previews and open-in-context
  flows
updated_at: '2026-04-07T06:40:05.588523Z'
---

## Summary
Search should show why a result matched and let operators open the right context quickly.

## Notes
- Imported or created by Hive 2.0.

## History
- 2026-04-06T15:47:43.724753Z bootstrap created.
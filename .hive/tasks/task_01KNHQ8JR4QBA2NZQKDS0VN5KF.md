---
acceptance:
- Relevant local validation passes, including make check and release-check or a documented
  narrower equivalent if blockers require iteration.
- Any failures introduced or exposed by the v2.4.0 bump are fixed in the same slice
  or recorded as blockers.
- The release path still packages the docs/search surfaces promised by the v2.4 line.
claimed_until: '2026-04-06T17:58:40.458654Z'
created_at: '2026-04-06T15:40:59.012108Z'
edges: {}
id: task_01KNHQ8JR4QBA2NZQKDS0VN5KF
kind: task
labels:
- release
- validation
owner: codex
parent_id: task_01KNHQ747AB64PEEWXP9KD82Q4
priority: 0
project_id: hive-v24
relevant_files:
- Makefile
- scripts/smoke_release_install.sh
- tests
- frontend/console
source: {}
status: done
title: Run full v2.4 release validation and fix any blocking regressions
updated_at: '2026-04-06T16:04:08.901198Z'
---

## Summary
Ran make check (784 passed, 4 skipped) and make release-check successfully against the staged 2.4.0 artifact set.

## Notes
- Imported or created by Hive 2.0.

## History
- 2026-04-06T15:40:59.012108Z bootstrap created.
---
acceptance:
- Archive or remove superseded docs/support artifacts without breaking active entry
  points; update maintainer truth surfaces and tests to reflect the cleaned state;
  verify any removed script or artifact is unused by current code/tests/docs/CI before
  deletion.
claimed_until: '2026-03-30T02:56:59.731780Z'
created_at: '2026-03-30T00:56:48.448551Z'
edges: {}
id: task_01KMY3WJJ0XANHDQHB6NY2HJ5S
kind: task
labels: []
owner: codex
parent_id: null
priority: 1
project_id: hive-v24
relevant_files:
- README.md
- docs
- scripts
- tests/test_maintainer_surfaces.py
source: {}
status: in_progress
title: Archive stale docs and maintenance artifacts for v2.4 assessment
updated_at: '2026-03-30T01:14:35.538266Z'
---

## Summary
Clean up outdated documentation, support artifacts, and genuinely unused scripts before external v2.4 assessment and v2.5 planning.

## Notes
Archived stale v2.2/v2.4 interim docs into docs/archive, removed one orphaned launch image, refreshed maintainer/release/support entrypoints to point at the active v2.4 ledger, fixed packaged-doc includes after the archive move, and added explicit fresh-worktree guidance to run uv sync --extra dev before pytest or make check.

## History
2026-03-29T21:18:00-04:00 validated cleanup slice with make check (776 passed, 12 skipped) and make release-check after the archive packaging fix.
---
acceptance:
- Archive or remove superseded docs/support artifacts without breaking active entry
  points; update maintainer truth surfaces and tests to reflect the cleaned state;
  verify any removed script or artifact is unused by current code/tests/docs/CI before
  deletion.
claimed_until: null
created_at: '2026-03-30T00:56:48.448551Z'
edges: {}
id: task_01KMY3WJJ0XANHDQHB6NY2HJ5S
kind: task
labels: []
owner: null
parent_id: null
priority: 1
project_id: hive-v24
relevant_files:
- README.md
- docs
- scripts
- tests/test_maintainer_surfaces.py
source: {}
status: done
title: Archive stale docs and maintenance artifacts for v2.4 assessment
updated_at: '2026-03-30T01:29:45.613876Z'
---

## Summary
Clean up outdated documentation, support artifacts, and genuinely unused scripts before external v2.4 assessment and v2.5 planning.

## Notes
Archived stale docs/support artifacts for the pre-5.4-Pro assessment pass, refreshed maintainer entrypoints, fixed the archive packaging include, and documented fresh-worktree dev-extra setup. Landed in PR #181 / commit 671d4fb07e07b419d765cb11bf2c90190f07c76e.

## History
2026-03-29T21:20:06-04:00 merged via PR #181 at 671d4fb07e07b419d765cb11bf2c90190f07c76e after green local validation, green PR CI, and green post-merge main CI.

---
acceptance:
- A fresh installed-tool path can find the shipped docs/search surfaces and open the
  console story successfully.
- docs/V2_4_STATUS.md is updated from release-execution-pending to shipped truth with
  release history or shipped-line notes as needed.
- Any immediate post-release blocker is recorded canonically rather than left implicit.
claimed_until: null
created_at: '2026-04-06T15:41:49.976944Z'
edges: {}
id: task_01KNHQA4GRWBA7KKB4TMCNS94E
kind: task
labels:
- release
owner: null
parent_id: task_01KNHQ747AB64PEEWXP9KD82Q4
priority: 0
project_id: hive-v24
relevant_files:
- docs/V2_4_STATUS.md
- docs/START_HERE.md
- docs/OPERATOR_FLOWS.md
- README.md
source: {}
status: done
title: Verify public install/search behavior and mark the v2.4 line as shipped
updated_at: '2026-04-06T16:22:30.156008Z'
---

## Summary
Verified the public 2.4.0 install/search/console story from a fresh installed-tool environment.

## Notes
Fresh install via uv tool install --python 3.11 mellona-hive[console] proved packaged-doc search hits, quickstart demo, console home, and task ready against the published artifact.

## History
- 2026-04-06T15:41:49.976944Z bootstrap created.
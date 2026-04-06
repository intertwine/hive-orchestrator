---
acceptance:
- pyproject.toml and src/hive/common.py report v2.4.0.
- docs/V2_4_STATUS.md and related maintainer tests describe the v2.4.0 cut truthfully.
- Any release-surface references that still imply implementation-pending rather than
  release-candidate state are updated.
claimed_until: '2026-04-06T16:48:09.200718Z'
created_at: '2026-04-06T15:40:34.723956Z'
edges: {}
id: task_01KNHQ7V13BRKRVZ1KET19P061
kind: task
labels:
- release
- v2.4
owner: codex
parent_id: task_01KNHQ747AB64PEEWXP9KD82Q4
priority: 0
project_id: hive-v24
relevant_files:
- pyproject.toml
- src/hive/common.py
- docs/V2_4_STATUS.md
- docs/RELEASING.md
- tests/test_maintainer_surfaces.py
- uv.lock
source: {}
status: done
title: Bump the package, release docs, and maintainer surfaces to v2.4.0
updated_at: '2026-04-06T15:58:08.536334Z'
---

## Summary
Bumped pyproject/common to 2.4.0, updated release-ledger truth and maintainer docs, refreshed uv.lock, and passed tests/test_maintainer_surfaces.py.

## Notes
- Imported or created by Hive 2.0.

## History
- 2026-04-06T15:40:34.723956Z bootstrap created.
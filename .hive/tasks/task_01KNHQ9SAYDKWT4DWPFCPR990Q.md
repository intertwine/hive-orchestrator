---
acceptance:
- A v2.4.0 git tag is created from the intended release commit.
- The v2.4.0 package is published to PyPI with the expected artifacts.
- A GitHub release exists with notes pointing to the v2.4 RFC bundle and shipped install
  story.
claimed_until: '2026-04-06T19:07:05.795459Z'
created_at: '2026-04-06T15:41:38.526509Z'
edges: {}
id: task_01KNHQ9SAYDKWT4DWPFCPR990Q
kind: task
labels:
- release
owner: codex
parent_id: task_01KNHQ747AB64PEEWXP9KD82Q4
priority: 0
project_id: hive-v24
relevant_files:
- docs/RELEASING.md
- docs/V2_4_STATUS.md
source: {}
status: done
title: Tag, publish, and cut the public v2.4.0 release artifacts
updated_at: '2026-04-06T16:21:47.143524Z'
---

## Summary
Created and pushed release commit/tag, published v2.4.0 to PyPI, and created the GitHub release.

## Notes
Evidence: tag v2.4.0 on main, GitHub release https://github.com/intertwine/hive-orchestrator/releases/tag/v2.4.0, Actions run 24039447602 green, PyPI serves wheel and sdist for mellona-hive 2.4.0.

## History
- 2026-04-06T15:41:38.526509Z bootstrap created.
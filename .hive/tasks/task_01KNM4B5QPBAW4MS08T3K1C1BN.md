---
acceptance:
- A maintainer-facing walkthrough document enumerates the shipped v2.5 surfaces, acceptance
  evidence, and remaining release-only decisions.
- The release plan captures the exact version bump, tag, publish, Homebrew, and public
  verification steps that would execute after walkthrough signoff.
- docs/V2_5_STATUS.md and the hive-v25 project state truthfully reflect that walkthrough
  preparation is the last pre-release task.
claimed_until: '2026-04-07T14:38:26.195383Z'
created_at: '2026-04-07T14:08:04.342515Z'
edges: {}
id: task_01KNM4B5QPBAW4MS08T3K1C1BN
kind: task
labels:
- release-readiness
owner: codex
parent_id: null
priority: 1
project_id: hive-v25
relevant_files:
- docs/V2_5_RELEASE_WALKTHROUGH.md
- docs/V2_5_STATUS.md
- docs/RELEASING.md
- docs/MAINTAINING.md
- pyproject.toml
- src/hive/search.py
- tests/test_maintainer_surfaces.py
source: {}
status: done
title: Prepare the v2.5 walkthrough and release cut plan
updated_at: '2026-04-07T14:16:48.021574Z'
---

## Summary
Assemble the maintainer walkthrough bundle and the exact v2.5 version-bump/tag/publish plan that will be used before the final public cut.

## Notes
User wants a full walkthrough before the final v2.5 release; this task prepares that bundle without tagging or publishing.

## History
2026-04-07T18:18:00Z completed walkthrough bundle and v2.5.0 release-cut plan with packaged-doc/search coverage.

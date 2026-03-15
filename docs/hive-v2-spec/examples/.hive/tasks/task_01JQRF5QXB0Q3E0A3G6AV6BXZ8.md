---
id: task_01JQRF5QXB0Q3E0A3G6AV6BXZ8
project_id: proj_01JQREK9B1DKYYQ7J0Q2Y7E0XG
title: Add project-local observer / reflector memory
kind: task
status: ready
priority: 1
parent_id: null
owner: null
claimed_until: null
labels:
  - memory
  - observer
relevant_files:
  - src/hive/memory/
  - examples/.hive/memory/project/
acceptance:
  - observer writes `observations.md`
  - reflector regenerates `reflections.md`, `profile.md`, and `active.md`
  - `hive context startup` includes memory outputs
edges:
  blocks:
    - task_01JQRF3N0T4SR1Z8ZP6TRV1Q4N
  relates_to: []
  duplicates: []
  supersedes: []
created_at: 2026-03-14T14:20:00Z
updated_at: 2026-03-14T14:20:00Z
source:
  imported_from:
    path: projects/hive-v2/AGENCY.md
    line: 26
---

## Summary

Port the observer / reflector pattern into Hive’s project-local memory plane.

## Notes

Start with BM25 only. Add optional QMD later.

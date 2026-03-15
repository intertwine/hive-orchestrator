---
id: task_01JQRF3N0T4SR1Z8ZP6TRV1Q4N
project_id: proj_01JQREK9B1DKYYQ7J0Q2Y7E0XG
title: Build CLI-first task surface
kind: task
status: in_progress
priority: 0
parent_id: null
owner: codex
claimed_until: 2026-03-14T16:00:00Z
labels:
  - cli
  - json
relevant_files:
  - src/hive/cli/
  - tests/test_cli_tasks.py
acceptance:
  - `hive task list --json` works
  - `hive task ready --json` works
  - `hive task claim/release` works
edges:
  blocks: []
  relates_to:
    - task_01JQRF5QXB0Q3E0A3G6AV6BXZ8
  duplicates: []
  supersedes: []
created_at: 2026-03-14T14:15:00Z
updated_at: 2026-03-14T15:20:00Z
source:
  imported_from:
    path: projects/hive-v2/AGENCY.md
    line: 25
---

## Summary

Implement the stable CLI JSON surface for task operations.

## Notes

This is the active slice because nearly every later feature depends on it.

## History

- 2026-03-14 claimed by codex for the first vertical slice

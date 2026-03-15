---
id: task_01JQRF7BSAK6M7D5XCA3D2GH4K
project_id: proj_01JQREK9B1DKYYQ7J0Q2Y7E0XG
title: Add thin Code Mode adapter
kind: task
status: ready
priority: 1
parent_id: null
owner: null
claimed_until: null
labels:
  - codemode
  - interface
relevant_files:
  - src/hive/codemode/
  - AGENT_INTERFACE.md
acceptance:
  - `search` searches CLI docs, schema docs, and examples
  - `execute` runs against a typed local Hive client
  - feature flag keeps it optional
edges:
  blocks: []
  relates_to:
    - task_01JQRF3N0T4SR1Z8ZP6TRV1Q4N
  duplicates: []
  supersedes: []
created_at: 2026-03-14T14:25:00Z
updated_at: 2026-03-14T14:25:00Z
source:
  imported_from:
    path: projects/hive-v2/AGENCY.md
    line: 27
---

## Summary

Adopt the small-surface search + execute pattern as an optional adapter, not as the primary product surface.

## Notes

Ship behind a feature flag after the CLI slice lands.

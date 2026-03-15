---
project_id: example-cross-repo
status: active
priority: medium
tags:
- example
- cross-repo
- external
- v2
target_repo:
  url: https://github.com/example/target-repository
  branch: main
relevant_files:
- src/index.ts
- package.json
---

# Cross-Repo Workflows

## Objective

Show how Hive can coordinate work that lands in another repository while keeping canonical task state in one workspace.

## Recommended Pattern

- keep task state, memory, and runs in Hive
- keep the actual code change in the target repo
- clone or mount the target repo into the workspace before searching or building context

## Projection Notes

`target_repo` is a narrative helper for humans or adapters. Canonical machine state still lives in `.hive/`.

<!-- hive:begin task-rollup -->
Create local Hive tasks that reference the target repo files you care about, then use `hive search` and `hive context startup` against that workspace.
<!-- hive:end task-rollup -->

<!-- hive:begin recent-runs -->
No runs recorded in this example snapshot.
<!-- hive:end recent-runs -->

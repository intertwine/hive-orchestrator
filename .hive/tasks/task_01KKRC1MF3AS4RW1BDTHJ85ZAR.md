---
acceptance:
- A single ready task is claimed with an owner and lease time.
- Startup context is generated for that exact task.
- The change target is narrowed to README.md, docs/, or projects/demo/.
claimed_until: null
created_at: '2026-03-15T09:08:14.435743Z'
edges:
  blocks:
  - task_01KKRC1MJHZT4E47AN9FTJC0JP
id: task_01KKRC1MF3AS4RW1BDTHJ85ZAR
kind: task
labels: []
owner: null
parent_id: null
priority: 1
project_id: demo
relevant_files:
- README.md
- docs/QUICKSTART.md
- projects/demo/AGENCY.md
- projects/demo/PROGRAM.md
source: {}
status: ready
title: Claim the first demo task and capture startup context
updated_at: '2026-03-15T09:08:18.158982Z'
---

## Summary
Pick up the demo the same way an everyday Hive user would: claim the work, generate context, and narrow the first change to a safe slice.

## Notes
- Start with `hive task ready --project-id demo`.
- Claim the task before you generate startup context.
- Keep the actual change inside `README.md`, `docs/`, or `projects/demo/`.

## History
- 2026-03-15T09:08:14.435743Z bootstrap created.

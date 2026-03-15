---
last_updated: '2026-03-15T00:00:00Z'
priority: medium
project_id: demo
relevant_files:
- projects/demo/AGENCY.md
status: active
tags:
- example
- tutorial
- v2
---

# Demo Project

## Objective

This project is the smallest useful Hive 2.0 walkthrough in the repository. It exists to show the happy path:

1. create canonical tasks
2. build startup context
3. do the work
4. sync projections

## Recommended Flow

```bash
hive task ready --project-id demo --json
hive context startup --project demo --json
make session PROJECT=demo
```

Use the canonical task list below as the source of truth for schedulable work.

## Notes

- Keep operational truth in `.hive/tasks/*.md`
- Keep this document readable for humans
- Use `PROGRAM.md` if you add evaluator-gated work to the demo

<!-- hive:begin task-rollup -->
## Task Rollup

| ID | Status | Priority | Owner | Title |
|---|---|---:|---|---|
| task_01KKQGXZTZ5M0YWW1TM4EA16BX | ready | 2 |  | Add relevant examples or case studies |
| task_01KKQGXZV42GJC64G4JS43XHKB | ready | 2 |  | All phases completed |
| task_01KKQGXZTTYD6BJJH8KV7V4Q5W | ready | 2 |  | Allocate research findings to appropriate sections |
| task_01KKQGXZV6R15NE6MQC5KGCWFY | ready | 2 |  | At least 5 sources cited |
| task_01KKQGXZV01X6JHH023Y333TW2 | ready | 2 |  | Check for clarity and coherence |
| task_01KKQGXZV7ZQRYRR24V1YRA9M2 | ready | 2 |  | Content is original and insightful |
| task_01KKQGXZTSAKTARYB35S51HRT1 | ready | 2 |  | Create blog post structure (intro, 3-4 main sections, conclusion) |
| task_01KKQGXZTVMSQH14SYDM5BS80J | ready | 2 |  | Define key takeaways for each section |
| task_01KKQGXZV5W0CG2QE2P2CK0ZR8 | ready | 2 |  | Final blog post is 1200-1500 words |
| task_01KKQGXZV3Q3Z4GQ3M9A5CZZFW | ready | 2 |  | Final proofread |
| task_01KKQGXZTN0F580PVYBYQC8T0H | ready | 2 |  | Find 5 credible sources about AI agent orchestration |
| task_01KKQGXZTQHPPF6M9DAAZSPPGE | ready | 2 |  | Identify unique angles or insights |
| task_01KKQGXZV22VDFAJ2T5PE68XT1 | ready | 2 |  | Polish language and tone |
| task_01KKQGXZV7CKZ3HS70PEQK99GN | ready | 2 |  | Ready for publication |
| task_01KKQGXZTPGSHZ5EKFWKR98KES | ready | 2 |  | Summarize key trends and predictions |
| task_01KKQGXZV19XJAZFS8DTBF9B35 | ready | 2 |  | Verify all sources are properly referenced |
| task_01KKQGXZTY16XTV99WNVQCBJB4 | ready | 2 |  | Write conclusion with actionable insights |
| task_01KKQGXZTW5FXPZ0NETBF14PCX | ready | 2 |  | Write introduction (hook + thesis) |
| task_01KKQGXZTXBPBMKB44RET43FP9 | ready | 2 |  | Write main sections with supporting evidence |
<!-- hive:end task-rollup -->

<!-- hive:begin recent-runs -->
## Recent Runs

| Run | Status | Task |
|---|---|---|
| No runs | - | - |
<!-- hive:end recent-runs -->

---
project_id: multi-model-ensemble-example
status: active
priority: medium
tags:
- example
- ensemble
- v2
---

# Multi-Model Ensemble

## Objective

Show how several candidate solutions can be explored in parallel before a final synthesis task chooses the best direction.

## Recommended Task Shape

- one candidate task per approach
- one synthesis task that compares the candidates

## Suggested Commands

```bash
hive task create --project-id multi-model-ensemble-example --title "Candidate A" --json
hive task create --project-id multi-model-ensemble-example --title "Candidate B" --json
hive task create --project-id multi-model-ensemble-example --title "Synthesize the winning approach" --json
```

## Projection Notes

Accepted run summaries are a good place to record why one candidate beat another.

<!-- hive:begin task-rollup -->
Treat each candidate as canonical task or run state, then unblock the synthesis task when comparisons are ready.
<!-- hive:end task-rollup -->

<!-- hive:begin recent-runs -->
No runs recorded in this example snapshot.
<!-- hive:end recent-runs -->

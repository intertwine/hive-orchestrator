# Multi-Model Ensemble

Use this pattern when you want several candidate solutions before choosing one direction.

## Recommended Shape

Create one task or run per candidate, then a synthesis task that compares them.

Example:

```bash
hive task create --project-id ensemble-demo --title "Candidate A: optimize query" --json
hive task create --project-id ensemble-demo --title "Candidate B: optimize query" --json
hive task create --project-id ensemble-demo --title "Candidate C: optimize query" --json
hive task create --project-id ensemble-demo --title "Select and land the best approach" --json
```

Link the synthesis task to the candidates:

```bash
hive task link <selection-task-id> blocked_by <candidate-a-task-id> --json
```

## Good Practice

- keep each candidate scoped and comparable
- use governed runs if you want evaluator output per candidate
- write the final choice into a synthesis task or accepted run summary

## Useful Commands

```bash
hive search "candidate query optimization" --scope workspace
hive run start <task-id> --json
hive run eval <run-id> --json
```

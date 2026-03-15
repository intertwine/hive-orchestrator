# Agent Hive Examples

These examples are v2-native reference patterns.

Start with the root [README](../README.md) for installation and first-run setup. Use this folder when you want to study how a specific orchestration pattern maps onto the current CLI and substrate.

## Common Starting Point

```bash
hive init --json
hive project create demo --title "Demo project" --json
hive task create --project-id demo --title "Define the first slice" --json
hive context startup --project demo --json
```

## What Each Example Shows

- `1-simple-sequential/`: a clean handoff where one task unlocks the next
- `2-parallel-tasks/`: several independent tasks claimed at the same time
- `3-code-review-pipeline/`: run, evaluate, reject, refine, accept
- `4-multi-model-ensemble/`: parallel candidate solutions with a synthesis step
- `5-data-pipeline/`: stage-by-stage task chains with explicit blockers
- `6-creative-collaboration/`: project memory and iterative drafting
- `7-complex-application/`: combining projects, tasks, runs, search, and policy
- `8-agent-dispatchers/`: building adapters on top of `hive task ready` and `hive context startup`
- `9-cross-repo-workflows/`: keeping Hive canonical while work spans more than one repo

## Reading These Examples

Each directory includes:

- a `README.md` with the pattern and command flow
- an `AGENCY.md` projection snapshot that shows how the human-facing document should read in Hive 2.0

The important rule is the same in every example:

- canonical work lives in `.hive/tasks/*.md`
- `PROGRAM.md` carries policy
- `AGENCY.md` stays readable and narrative

If you want more implementation detail, also look at `docs/hive-v2-spec/examples/` and the live projects under `projects/`.

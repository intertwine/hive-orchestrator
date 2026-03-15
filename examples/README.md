# Agent Hive Examples

These examples are reference patterns, not the main onboarding path.

If you are new to Hive, start with the root [README](../README.md) and the CLI flow:

```bash
hive init --json
hive project create demo --title "Demo project" --json
hive task create --project-id demo --title "Define the first slice" --json
hive context startup --project demo --json
```

## How to use this folder

- Use these directories to study orchestration patterns.
- Expect some examples to reflect older, pre-v2 habits more than the current product surface.
- Treat `.hive/tasks/*.md`, `PROGRAM.md`, and the `hive` CLI as the current source of truth when adapting any example.

## Where to look first

- `1-simple-sequential/` for basic handoffs
- `2-parallel-tasks/` for independent parallel work
- `3-code-review-pipeline/` for reviewer loops
- `7-complex-application/` for a larger end-to-end example
- `8-agent-dispatchers/` if you want to build your own issue or webhook adapter

## Better v2-native references

For cleaner Hive 2.0 examples, also look at:

- `docs/hive-v2-spec/examples/`
- `projects/`

Those directories track the current substrate and projection model more closely than the older example set here.

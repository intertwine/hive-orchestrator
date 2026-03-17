# Operator Flows

Hive 2.2 assumes the operator mostly supervises and occasionally intervenes.

## Normal manager loop

```bash
hive console serve
hive next
hive work <task-id> --owner <your-name>
hive finish <run-id>
```

Use this when the system is healthy and the project already has a real `PROGRAM.md`.

## Guided first-run loop

For a new workspace:

```bash
hive onboard demo --title "Demo project"
hive console serve
```

For an existing repo:

```bash
hive adopt app --title "App"
hive console serve
```

## Steering loop

Use steering only when Hive hits a real fork in the road:

- pause or resume a run
- cancel risky or stale work
- approve or reject review-ready work
- reroute to a better driver
- attach a typed note that will stay in the audit trail

CLI examples:

```bash
hive steer pause <run-id> --reason "Waiting on a dependency" --json
hive steer reroute <run-id> --driver claude-code --reason "Need broader repo search" --json
```

## Program hardening loop

When a project is not yet safe for autonomous promotion:

```bash
hive program doctor <project-id>
hive program add-evaluator <project-id> <template-id>
```

Use this before blaming the run engine. Most blocked promotions are a policy problem, not a run problem.

## Campaign loop

Use campaigns when the work is larger than a single task:

```bash
hive campaign create --title "Launch week" --goal "Ship the site" --project-id website
hive campaign tick <campaign-id>
hive brief daily
```

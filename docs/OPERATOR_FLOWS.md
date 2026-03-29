# Operator Flows

Hive v2.4 assumes the operator mostly supervises, but it also gives explicit inspect-and-steer
surfaces when a Pi, OpenClaw, or Hermes run needs intervention.

Install `mellona-hive[console]` first anywhere you use `hive console serve` below.

## Normal manager loop

```bash
hive console serve
hive next
hive work <task-id> --owner <your-name>
hive finish <run-id>
```

Use this when the system is healthy and the project already has a real `PROGRAM.md`.

For native harness work, check the integration first:

```bash
hive integrate doctor pi --json
hive integrate doctor openclaw --json
hive integrate doctor hermes --json
```

## Guided first-run loop

For a new workspace:

```bash
hive onboard demo --title "Demo project"
hive next --project-id demo
hive work --owner <your-name>
hive finish <run-id>
```

For an existing repo:

```bash
hive adopt app --title "App"
hive next --project-id app
hive work --project-id app --owner <your-name>
hive finish <run-id>
```

Install `mellona-hive[console]` first and add `hive console serve` beside that loop when you want the live
observe-and-steer view from the beginning.

Pi is the managed companion path:

```bash
hive integrate pi --json
hive next --project-id demo
hive work --owner <your-name>
hive finish <run-id>
```

OpenClaw and Hermes are attach-first advisory paths:

```bash
hive integrate attach openclaw <session-key> --json
hive integrate attach hermes <session-key> --json
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
hive steer reroute <run-id> --driver claude --reason "Need broader repo search" --json
```

## Program hardening loop

When a project is not yet safe for autonomous promotion:

```bash
hive program doctor <project-id>
hive program add-evaluator <project-id> <template-id>
```

Use this before blaming the run engine. Most blocked promotions are a policy problem, not a run problem.
If Program Doctor suggested `local-smoke`, remember that it is only a bootstrap placeholder until you replace it with
a real evaluator for the repo.

## Sandbox readiness loop

When a run is blocked on sandbox setup or remote execution policy, inspect the backend truth directly:

```bash
hive sandbox doctor --json
hive sandbox doctor podman --json
hive sandbox doctor e2b --json
hive sandbox doctor daytona --json
```

Use [docs/recipes/sandbox-doctor.md](./recipes/sandbox-doctor.md) for the profile map, optional extras, and current backend limitations.

The current shipped operator story is: capability truth, sandbox truth, retrieval explanations,
approval handling, and campaign reasoning from one console and one CLI, with Pi managed runs and
OpenClaw/Hermes attach flows all visible in the same control surface.

## Campaign loop

Use campaigns when the work is larger than a single task:

```bash
hive campaign create --title "Launch week" --goal "Ship the site" --project-id website
hive campaign tick <campaign-id>
hive brief daily
```

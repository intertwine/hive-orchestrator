# @mellona/pi-hive

Native Pi companion commands for [Agent Hive](https://github.com/intertwine/hive-orchestrator) v2.4.

## What this package includes

- `pi-hive connect` to inspect workspace readiness through `hive integrate pi`
- `pi-hive doctor` to run `hive integrate doctor pi`
- native wrappers for `next`, `search`, `open`, `attach`, `finish`, `note`, and `status`
- a `pi-hive-runner` entrypoint that Hive launches for governed Pi runs
- a lightweight local native-session helper for attach-mode development and tests

## Truthful status

This package now covers the v2.4 Pi milestone in-repo:

- `open` launches a real Hive-managed Pi run through the `pi` driver
- `attach` binds an existing live Pi session to a real advisory Hive run
- managed and attach modes both persist normalized `trajectory.jsonl` and `steering.ndjson`
- steering notes round-trip into the live Pi session surfaces

It is still intentionally dependency-light:

- the companion shells out to stable `hive` CLI surfaces
- the managed runner is a lightweight Node process, not a separate daemon

## Install

```bash
npm install -g @mellona/pi-hive
```

Or from this repo checkout:

```bash
cd packages/pi-hive
npm link
```

## Usage

```bash
pi-hive connect
pi-hive doctor --json
pi-hive next --project-id hive-v24
pi-hive search "PiWorkerAdapter"
pi-hive open task_123 --json
pi-hive attach pi-live-42 --task-id task_456 --json
pi-hive status run_123
pi-hive note run_123 "Steering note from Pi"
```

## Development

The companion is intentionally dependency-light. It shells out to the stable `hive`
CLI surfaces instead of reading workspace files directly, and the bundled `session-start`
helper exists mainly so attach-mode tests can stand up a live native session without an
external Pi install.

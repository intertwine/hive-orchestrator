# @mellona/pi-hive

Native Pi companion scaffolding for [Agent Hive](https://github.com/intertwine/hive-orchestrator) v2.4.

## What this slice includes

- `pi-hive connect` to inspect workspace readiness through `hive integrate pi`
- `pi-hive doctor` to run `hive integrate doctor pi`
- thin CLI wrappers for `next`, `search`, `finish`, `note`, and `status`
- a `pi-hive-runner` entrypoint that accepts managed-run metadata and writes a local manifest

## Truthful status

This package is the M2 foundation slice, not the completed Pi milestone.

- attach and managed runner entrypoints are scaffolded
- the live Pi SDK session binding flow is still forthcoming
- `open` and `attach` intentionally return a clear "not yet wired" error for now

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
pi-hive status run_123
pi-hive note run_123 "Steering note from Pi"
```

## Development

The companion is intentionally dependency-light right now. It shells out to the stable `hive`
CLI surfaces instead of reading workspace files directly.

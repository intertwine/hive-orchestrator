# Driver Development Guide

Drivers let Hive supervise different worker harnesses through one normalized run model.

## Every driver must implement

- `probe()`
- `launch()`
- `resume()`
- `status()`
- `interrupt()`
- `steer()`
- `collect_artifacts()`
- `stream_events()`

See [docs/hive-v2.2-rfc/HIVE_V2_2_DRIVER_SPEC.md](../hive-v2.2-rfc/HIVE_V2_2_DRIVER_SPEC.md) for the contract.

## What Hive expects

- stable driver name
- truthful capability reporting
- normalized run status
- normalized artifacts under `.hive/runs/run_<id>/`
- typed steering acknowledgements

## The design rule

Do not push product logic into the driver. The driver adapts a harness. Hive still owns the task graph, policy, memory, audit trail, and promotion decision.

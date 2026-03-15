# Handoff to Codex: recommended implementation order

This handoff assumes Codex is working inside the `intertwine/hive-orchestrator` repository.

## Core instruction

Do **not** try to ship every feature at once. Land a thin vertical slice that proves the architecture:

1. canonical task files
2. CLI JSON surface
3. `PROGRAM.md`
4. run engine
5. memory observe/search for one harness
6. migration path
7. only then optional Code Mode / MCP

## First PR plan

### PR 1 — scaffold and parsing
Ship:
- `.hive/` layout helpers
- task file parser/serializer
- ID generation
- cache schema
- `hive init`
- `hive doctor`

Tests:
- round-trip task file tests
- init smoke test

### PR 2 — task commands and projections
Ship:
- `hive task list/show/create/update/link/ready`
- `hive sync projections`
- generated task rollup in `AGENCY.md`

Tests:
- ready detection
- blockers
- projection golden tests

### PR 3 — `PROGRAM.md` and run engine
Ship:
- `PROGRAM.md` parser
- `hive run start/show/eval/accept/reject/escalate`
- worktree management
- run artifacts

Tests:
- evaluator pass/fail
- promotion decision rules
- run artifact contract

### PR 4 — memory slice
Ship:
- project-local memory docs
- observer job
- `hive memory search`
- `hive context startup`
- one harness integration (Claude or Codex first)

Tests:
- sample transcript -> observations
- observations -> reflections/profile/active
- startup context assembly

### PR 5 — migration
Ship:
- `hive migrate v1-to-v2`
- `AGENTS.md` shim
- `PROGRAM.md` stubs

Tests:
- migrate a fixture repo
- compare projections

### PR 6 — optional Code Mode adapter
Ship:
- `search`
- `execute`
- typed client
- feature flag
- thin MCP wrapper only if still wanted

Tests:
- API search results
- safe timeout behavior
- simple multi-call composition via execute

## Technical shortcuts that are acceptable

1. Use a local SQLite cache and rebuild it often.
2. Start with project-local memory only; add user-global memory right after.
3. Start with `bm25`; add QMD later behind a backend flag.
4. Start with `local` executor only; stub `github-actions`.
5. Implement Code Mode sandbox as bounded subprocess first; harden later.

## Technical shortcuts that are *not* acceptable

1. Making checkbox lists in `AGENCY.md` canonical again.
2. Making SQLite canonical repo state.
3. Adding a giant MCP tool catalog because it is convenient.
4. Treating `PROGRAM.md` as optional for autonomous runs.
5. Marking tasks complete without evaluator results.
6. Hiding task state in harness-local todo/plan modes.

## File ownership recommendation

### Existing code likely to evolve
- current Cortex logic -> ready detection / scheduler package
- current MCP server -> thin compatibility wrapper or feature-flagged module
- current coordinator -> optional lease service
- current tracing -> event + telemetry adapters

### New packages to add
- `src/hive/cli/`
- `src/hive/models/`
- `src/hive/store/`
- `src/hive/projections/`
- `src/hive/runs/`
- `src/hive/memory/`
- `src/hive/codemode/` (optional)
- `src/hive/migrate/`

## Recommended internal package split

```text
src/hive/
  ids.py
  clock.py
  models/
    task.py
    project.py
    run.py
    program.py
  store/
    task_files.py
    cache.py
    events.py
  projections/
    global_md.py
    agency_md.py
    agents_md.py
  runs/
    engine.py
    evaluators.py
    worktree.py
  memory/
    observe.py
    reflect.py
    search.py
    context.py
    adapters/
      claude.py
      codex.py
      opencode.py
      pi.py
      hermes.py
  cli/
    main.py
    task_cmd.py
    run_cmd.py
    memory_cmd.py
    project_cmd.py
    migrate_cmd.py
  codemode/
    search.py
    execute.py
    client.py
```

## Definition of a good first demo

A good first end-to-end demo is:

1. initialize Hive 2.0 in a sample project
2. create/import two tasks and one blocker edge
3. show `hive task ready --json`
4. create a `PROGRAM.md`
5. start a run in a worktree
6. run evaluators
7. accept the run
8. generate updated `AGENCY.md`
9. ingest a transcript and produce `profile.md` / `active.md`
10. start a second session that reads startup context and picks up where the first left off

If that demo is smooth, the architecture is probably right.

# Hive 2.0 Migration Plan

Status: Proposed  
Target: migrate an existing Hive 1.x repository to the Hive 2.0 layout with minimal disruption.

## Principles

1. **Git-safe first.** Migration must be done in a branch and reviewable as normal text diffs.
2. **No destructive rewrite by default.** Existing `GLOBAL.md` and `AGENCY.md` content stays in place unless `--rewrite` is explicitly requested.
3. **Checkbox tasks are imported, not trusted forever.** Legacy task lists become structured task files.
4. **Project docs stay readable throughout.** The migration adds generated markers and compatibility shims rather than forcing a hard cutover on day one.
5. **SQLite is never the migration target.** The cache is rebuilt locally after migration.

## Inputs expected from Hive 1.x

- `GLOBAL.md`
- `projects/**/AGENCY.md`
- optional current coordinator config
- optional current MCP config
- optional current skills

## Outputs produced by migration

- `.hive/tasks/*.md`
- `.hive/events/<date>.jsonl`
- `projects/**/PROGRAM.md` stubs where missing
- root `AGENTS.md` compatibility shim
- generated section markers inserted into `GLOBAL.md` and `AGENCY.md`
- `.hive/cache/index.sqlite` rebuilt locally (gitignored)

## Migration command

```bash
hive migrate v1-to-v2
```

Recommended flags:

```bash
hive migrate v1-to-v2 --dry-run
hive migrate v1-to-v2 --project projects/my-project
hive migrate v1-to-v2 --rewrite               # optional destructive cleanup
hive migrate v1-to-v2 --owner codex           # default owner label for imported claims/notes
```

## Step-by-step behavior

### Step 1: inventory projects

1. Parse `GLOBAL.md` for project references if present.
2. Walk `projects/**/AGENCY.md`.
3. Create a project record for each discovered project path.
4. If the project already has a frontmatter `project_id`, keep it; otherwise assign a new stable ID.

### Step 2: import legacy tasks

For each `AGENCY.md`:

1. Detect legacy task sections:
   - checkbox lists
   - heading-scoped checklists
   - indented nested checklists
2. Convert each checkbox item into a canonical task file under `.hive/tasks/`.
3. Preserve:
   - original text
   - source path
   - source line number
   - checked vs unchecked state
   - indentation / heading ancestry for parent-child inference

Import rules:

- checked item -> `status: done`
- unchecked item with no blockers -> `status: ready`
- unchecked item under “blocked” headings or explicit dependency notes -> `status: blocked`
- ambiguous items -> `status: proposed`

### Step 3: infer hierarchy and edges

Hierarchy inference order:

1. explicit dependency metadata in frontmatter
2. nested checklist indentation
3. enclosing headings (`##`, `###`) treated as epics or grouping nodes
4. textual heuristics (only in warning mode; do not auto-create edges without confidence)

MVP edge inference:
- indentation implies `parent_of`
- explicit “depends on X” lines MAY produce `blocks`
- explicit “duplicate of / supersedes” lines MAY produce typed edges if confidence is high
- otherwise leave unlinked and emit a migration warning

### Step 4: preserve narrative docs

Migration MUST NOT destroy the explanatory parts of `AGENCY.md`.

The migrator inserts markers:

```md
<!-- hive:begin task-rollup -->
<!-- hive:end task-rollup -->
<!-- hive:begin recent-runs -->
<!-- hive:end recent-runs -->
```

The old checklist section is either:
- left in place and relabeled as “Imported legacy tasks” (default), or
- removed/replaced (`--rewrite` only)

### Step 5: create `PROGRAM.md` stubs

For each project without `PROGRAM.md`, create a stub:

- `program_version: 1`
- `mode: workflow`
- empty or conservative evaluator list
- placeholder allow/deny paths
- section reminding a human to set budgets and promotion rules

The migrator SHOULD never invent risky evaluator commands.

### Step 6: create `AGENTS.md` shim

If the repo lacks a root `AGENTS.md`, create one.

If it already exists:
- append a bounded Hive section
- do not overwrite unrelated instructions

### Step 7: emit bootstrap events

Create a bootstrap event log like:

```json
{"id":"evt_...","occurred_at":"...","actor":"migration","entity_type":"project","entity_id":"proj_...","event_type":"project.imported","source":"migrate","payload_json":"{...}"}
{"id":"evt_...","occurred_at":"...","actor":"migration","entity_type":"task","entity_id":"task_...","event_type":"task.imported","source":"migrate","payload_json":"{...}"}
```

Events are for audit only. The imported task files remain the current-state authority.

### Step 8: rebuild cache

After files are written:

```bash
hive cache rebuild
hive sync projections
```

## Acceptance criteria

A migration is considered successful when:

1. Every discovered `AGENCY.md` has a project ID.
2. Every imported legacy task has a task file.
3. `hive task list --json` returns imported tasks.
4. `hive task ready --json` returns a plausible ready set.
5. `GLOBAL.md` and `AGENCY.md` generated sections render without clobbering human text.
6. A root `AGENTS.md` exists.
7. The repo remains understandable to a human reading the markdown docs.
8. The branch diff is reviewable without opening binary files.

## Failure modes to handle

### Ambiguous checklist structure

Behavior:
- import as flat tasks
- emit warnings to stderr and a migration report
- do not invent hierarchy unless confidence is high

### Duplicate legacy task titles

Behavior:
- assign distinct immutable IDs
- add a note in task history with source path/line

### Existing partial v2 state

Behavior:
- detect and merge only if safe
- otherwise stop with a message and ask the caller to use `--force` or clean up manually

### Broken frontmatter

Behavior:
- keep raw file content untouched
- emit a structured migration error
- continue other projects unless `--fail-fast` is set

## Suggested report format

`hive migrate v1-to-v2 --json` SHOULD return:

```json
{
  "ok": true,
  "projects_imported": 4,
  "tasks_imported": 37,
  "warnings": [
    {
      "path": "projects/demo/AGENCY.md",
      "line": 44,
      "message": "Could not confidently infer dependency for 'Ship docs'"
    }
  ],
  "created_files": [
    ".hive/tasks/task_....md",
    "projects/demo/PROGRAM.md",
    "AGENTS.md"
  ]
}
```

## Recommended rollout strategy

### Phase A: shadow mode

1. Run migration in a branch.
2. Keep legacy checklist sections in place.
3. Ask agents to use the new CLI and task files.
4. Compare `hive task ready` results with current v1 behavior.

### Phase B: generated rollups

1. Turn on `hive sync projections`.
2. Make task rollup sections generated.
3. Keep old checklist section as a “legacy import” appendix.

### Phase C: full cutover

1. Remove the legacy checklist appendix with `--rewrite`.
2. Require `PROGRAM.md` for autonomous runs.
3. Deprecate broad MCP tools in favor of CLI + thin Code Mode adapter.

## Recommendation

Use migration to establish the new substrate quickly, but keep humans oriented by preserving the narrative markdown documents. The goal is not to surprise maintainers with an invisible system; it is to move machine state into a better place while keeping the repo easy to read.

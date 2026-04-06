# Hive Dogfood Scratchpad

Purpose: capture friction, missing capabilities, and improvement ideas while using Hive itself to plan and execute Hive work.

## 2026-04-06

### Current blockers and friction

- `hive task create`, `hive task claim`, and `hive sync projections` frequently collide on a workspace-level refresh lock with the message `Hive is already refreshing this workspace. Wait a moment, then retry the command.`
- The lock behavior makes normal multi-step task-tree creation feel much slower than it should, especially when several CLI calls are required in sequence.
- Retry behavior is not idempotent enough at the workflow level. A partial retry created a duplicate task with the same title, which then needed cleanup.
- The user-facing workflow language uses `blocked_by`, but the canonical edge type accepted by `hive task link` is `blocks`. That mismatch cost time and produced failed commands.
- Cross-project dependency authoring is possible in principle, but it is not ergonomic. The CLI does not help much with expressing “task A in project X blocks task B in project Y.”
- Long-running refresh or context operations do not expose enough progress to tell whether Hive is healthy, busy, or wedged.
- There is no obvious `hive task archive` affordance. The working path is `hive task update <id> --status archived`, which is functional but discoverability-poor during cleanup work.
- `hive task ready` does support `--project-id`, but focused planning still feels too global because nearby `task` and `context` flows do not consistently keep one project in view.

### Improvement ideas

- Add first-class batch task creation from a YAML/JSON plan so a whole task tree can be created atomically.
- Add idempotent task upsert behavior keyed by `(project_id, title)` or an explicit external key, so retries do not create duplicates.
- Make dependency verbs consistent across docs, CLI help, and storage semantics. If the canonical edge is `blocks`, expose `blocked_by` as a supported alias everywhere.
- Add better refresh-state observability:
  `hive workspace refresh-status --json`
  or visible progress / queue ownership in current commands.
- Improve lock handling so read-only commands can proceed during refresh, and write commands can optionally wait with progress rather than fail-fast.
- Add a single command for milestone/task-tree import from RFC planning docs or a local manifest.
- Add a safer “claim + context startup” combined command for manual/non-`hive work` flows.
- Add a first-class `hive task archive <id>` helper so duplicate cleanup is easier to discover and script.
- Add better project-scoped ergonomics across `task`, `context`, and dependency commands so maintainers can stay focused inside one release line at a time.

### What worked well

- Project bootstrap via `hive project create` gave us the right canonical home quickly.
- Canonical tasks and parent relationships are still a much better substrate than ad hoc markdown checklists.

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
- `hive quickstart demo --json` does not expose a simple top-level workspace path, even though the caller often needs that path immediately for follow-up commands. The data is present under `layout.workspace`, but that is not obvious from the shape or command story.
- `hive --version --json` currently prints plain text (`hive 2.4.0`) instead of JSON, which makes automation scripts guess at command-specific formatting rules.
- Narrow implementation slices still pay the cost of broad repo validation, and when an unrelated late-suite test flakes it is hard to distinguish “my slice regressed” from “the suite is noisy” without manual reruns and judgment.
- `hive work` can mutate task state before it finishes run-start preflight. In this session it claimed the v2.5 preferences task and only then failed because the project `PROGRAM.md` had no required evaluators, leaving a partial side effect and forcing a manual fallback to `hive context startup`.
- When work is driven through normal PR/merge flow instead of a governed `hive finish`, task state can drift from reality. After merging the v2.5 preferences slice, the canonical task still showed up as `claimed`/`ready` until we manually ran `hive task update ... --status done`, `hive task release`, and `hive sync projections`.
- Maintainer work inside the repo can silently run through a stale globally installed `hive` binary. In this session `/Users/bryanyoung/.local/bin/hive` still reported `2.3.0` even though the checked-out repo and the released line were already at `2.4.0`, which makes dogfooding truth harder to reason about.

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
- Add a top-level `workspace_path` (or `path`) field to `quickstart demo --json` so shell automation does not need to know internal `layout` structure.
- Make `--json` output consistent for meta commands like `--version`, or reserve `--json` only for subcommands that truly emit JSON.
- Add task- or PR-scoped validation profiles plus simple flake memory/reporting, so maintainers can prove the changed surface quickly while still tracking broad-suite health separately.
- Run `hive work` preflight before mutating task ownership, or automatically roll back the claim when run start fails.
- Surface project run-readiness earlier in task recommendation flows so `hive next` does not hand back a task that `hive work` cannot actually start.
- Add a first-class “landed via PR” or “close from merge” flow so maintainers can reconcile canonical task state with merged Git history without manual task-update/release/projection cleanup.
- Detect when the repo checkout and the globally installed `hive` CLI disagree on version, and either warn loudly or offer a repo-local execution path so maintainers do not unknowingly dogfood the wrong build.

### What worked well

- Project bootstrap via `hive project create` gave us the right canonical home quickly.
- Canonical tasks and parent relationships are still a much better substrate than ad hoc markdown checklists.

## 2026-04-07

### Current blockers and friction

- `hive task release` after `hive task update <id> --status done` moved a completed task back to `ready`, which made the canonical task state temporarily lie until we manually re-marked it `done`. The release flow for completed tasks is too footgun-prone.
- A delegated implementation worker ended up using the shared maintainer checkout instead of an isolated worktree, switched branches underneath the active thread, and dirtied shared `.hive` task/projection state before any code changes were made.
- Normal Hive commands still emit append-only `.hive/events/<date>.jsonl` noise into maintainer branches, which is easy to mistake for intentional reviewable work during PR prep.
- GitHub-managed Claude review did not reliably produce a review artifact for an active console PR, so the maintainer flow had to fall back to `claude -p "/review <pr>"` locally and then manually summarize the findings back onto the PR.
- Reconciliatory Hive commands like `hive task update ... --status done` plus `hive sync projections` immediately dirty `GLOBAL.md`, project rollups, and task files in the current checkout. That is correct canonically, but it means a freshly green local `main` stops being clean again before the maintainer has even branched for the next slice.

### Improvement ideas

- Make `hive task release` status-aware:
  if a task is already `done`, release the lease metadata without demoting the task back to `ready`.
- Add an explicit `hive task complete <id>` or `hive task close-from-merge <id>` path that clears the claim and preserves `done` in one command.
- Ensure delegated/worker runs always use isolated worktrees or fail loudly before they can switch the shared checkout branch.
- Add a maintainer mode or config that keeps `.hive/events/*.jsonl` out of normal PR branches unless the operator explicitly asks to record or stage them.
- Make GitHub-managed Claude review status more observable from Hive/maintainer surfaces, and add a first-class “fallback to local review” breadcrumb so reviewers do not have to infer whether an `eyes` reaction means “pending,” “stuck,” or “done elsewhere.”
- Add a cleaner “post-merge reconcile” flow that can update canonical task/project state without surprising maintainers in `main`, for example by steering those writes into the current feature branch or by offering an explicit staged projection refresh step.

# Hive UX Sweep

Archived note: this is a historical usability findings log, not a canonical public or maintainer guide. Prefer the
active onboarding docs and `docs/V2_4_STATUS.md` for current product truth.

This file tracks real usability findings from hands-on Hive testing.

The goal is simple: use Hive the way a new user, adopter, or maintainer would use it, then write down the rough edges while they are still fresh. We can fix these in focused polish passes instead of losing them in chat history.

## Open Findings

### 2026-03-15 - First run requires a Git checkpoint, but the CLI does not explain that clearly

**Workflow**

- Fresh directory
- `git init`
- `hive init`
- `hive quickstart ...`
- `hive task claim ...`
- `hive context startup ...`
- `hive run start <task-id>`

**What happened**

`hive run start` failed until the workspace had an initial Git commit. The command surfaced a Python stack trace and a low-level clean-repo error instead of guiding the user toward the next correct step.

**Why this matters**

This is likely to be one of the first advanced actions a new user tries after quickstart. Hitting a raw traceback here makes the product feel less polished than it actually is.

**Ideal behavior**

- Detect that the workspace has only bootstrap changes and no commit yet.
- Explain that runs need a clean Git checkpoint before a worktree can be created.
- Suggest a concrete next step such as making an initial commit.
- Exit with a friendly, product-level error message rather than a traceback.

### 2026-03-15 - Migration dry-run does not faithfully preview the real migration

**Workflow**

- Fresh legacy-style repo with `GLOBAL.md` and a checkbox-driven `projects/legacy-product/AGENCY.md`
- `hive init`
- `hive migrate v1-to-v2 --dry-run`
- `hive migrate v1-to-v2`

**What happened**

The dry-run reported:

- `tasks_imported: 6`
- `edges_inferred: 0`
- `warnings: []`

The real migration on the same repo reported:

- `tasks_imported: 6`
- `edges_inferred: 1`
- warning: `Ambiguous relation target 'Draft landing page copy' matched multiple tasks`

The same mismatch happened in `--rewrite` mode.

**Why this matters**

Dry-run is where a cautious adopter decides whether to trust the migration. If the preview hides warnings and inferred edges, the real run feels surprising instead of safe.

**Ideal behavior**

- Dry-run should use the same inference and warning pipeline as the real migration.
- If any preview limitations remain, the CLI should say so clearly.
- The human-readable output should make it obvious when relation inference is tentative or ambiguous.

### 2026-03-15 - Invalid run lifecycle actions still surface raw Python tracebacks

**Workflow**

- Existing run in a fresh test workspace
- Attempted `hive run eval`, `hive run accept`, `hive run reject`, and `hive run escalate` against a run that was already in `accepted`

**What happened**

Each command failed with a Python traceback ending in a `ValueError`, for example:

- `ValueError: Cannot evaluate run with status 'accepted'`

The message itself is useful, but the delivery is low-level and jarring.

**Why this matters**

This is exactly the kind of state mistake a real user will make while learning the run lifecycle. A traceback makes Hive feel like a library rather than a polished operator tool.

**Ideal behavior**

- Return a clean CLI error with the current run status and the allowed next actions.
- Preserve the structured `--json` contract for machine users.
- Avoid exposing Python tracebacks for expected product-level validation failures.

### 2026-03-15 - Parallel memory commands can collide during cache rebuild

**Workflow**

- In the same workspace, run `hive memory observe ...` and `hive memory reflect ...` at the same time

**What happened**

`hive memory observe` failed with:

- `sqlite3.OperationalError: disk I/O error`

Running the same `memory observe` command again immediately, on its own, succeeded.

**Why this matters**

A human may never hit this by hand, but agents, hooks, and wrappers absolutely can. If Hive is meant to orchestrate agent work, the CLI should not be fragile when two safe commands touch the cache at once.

**Ideal behavior**

- Serialize cache rebuilds or retry safely around transient SQLite conflicts.
- Return a friendly concurrency error if serialization is not possible.
- Document whether the cache is single-writer by design.

### 2026-03-15 - `context startup` can present stale projection state after a claim

**Workflow**

- Fresh workspace via `hive quickstart`
- Claim the top ready task with `hive task claim ...`
- Run `hive task ready --project-id ...`
- Run `hive context startup --project ... --json` without syncing projections first

**What happened**

The canonical ready queue was empty after the claim, but the `AGENCY.md` section inside the startup context still showed the task as `ready` with no owner because it was reading an unsynced projection. The same workspace was effectively telling two different stories at once.

**Why this matters**

Context bundles are supposed to reduce ambiguity, not introduce it. If an agent sees “no ready work” in one part of the system and “ready task” in the bundled project doc, trust drops fast.

**Ideal behavior**

- Either sync projections automatically before building context, or
- Build the context from canonical task state even when the projected markdown has not been refreshed yet, and
- Make the task-specific startup path the obvious default in docs and CLI nudges.

### 2026-03-15 - Concurrent memory writes can fail with a raw SQLite disk I/O error

**Workflow**

- Fresh workspace via `hive quickstart`
- Run two `hive memory observe ...` commands at nearly the same time

**What happened**

One observation succeeded, while the other crashed with `sqlite3.OperationalError: disk I/O error` during cache rebuild.

**Why this matters**

Hive is explicitly aimed at multi-agent use. Even if humans do not trigger memory writes in parallel very often, agents absolutely can. A raw SQLite error feels brittle and hard to reason about.

**Ideal behavior**

- Serialize or retry cache rebuilds around memory writes.
- Return a Hive-level error if the cache is temporarily busy.
- Treat concurrent observation as a supported case, not an accidental one.

### 2026-03-15 - `memory reflect` currently mirrors observations instead of producing differentiated memory docs

**Workflow**

- Record a note and a short transcript with `hive memory observe`
- Run `hive memory reflect`
- Search memory with `hive search --scope memory ...`

**What happened**

`active.md`, `profile.md`, and `reflections.md` all ended up containing essentially the same lines as `observations.md`. A memory search then returned multiple near-duplicate hits for the same small piece of context.

**Why this matters**

The feature technically works, but it does not yet feel like distinct memory layers. From a user perspective it looks like duplication, not synthesis.

**Ideal behavior**

- `observations.md` should stay raw and recent.
- `active.md` should be short and current.
- `profile.md` should stabilize longer-lived traits or preferences.
- `reflections.md` should summarize patterns or lessons instead of copying the source.

### 2026-03-15 - `execute` advertises bounded execution, but the current boundaries are hard to understand

**Workflow**

- Run `hive execute` with simple Python snippets
- Try filesystem reads outside the workspace
- Try DNS resolution and outbound HTTP

**What happened**

- Outbound HTTP was blocked with a good product-level error.
- DNS resolution still worked.
- Reading `/etc/hosts` from inside `hive execute` also worked.

**Why this matters**

The current behavior is not obviously wrong if the boundary is “best effort network denial inside a local helper,” but it is surprising if a user reads `execute` as a sandbox. Right now the practical security model is not obvious from the user-facing surface.

**Ideal behavior**

- Either harden the sandbox so off-workspace filesystem reads and network primitives are actually blocked, or
- Describe the true boundary very explicitly: local execution helper, not a full sandbox.
- Keep the error messaging strong and consistent across all network-related operations.

### 2026-03-15 - General search ranks projected rollups above canonical task hits for task-shaped queries

**Workflow**

- Fresh workspace via `hive quickstart`
- Search for a task phrase such as `hive search "thin slice"`

**What happened**

The top hit was the projected `AGENCY.md` rollup rather than the canonical task file, even though the query was clearly looking for a task.

**Why this matters**

For everyday work, the canonical task is usually the thing the user actually wants to open, claim, or update. Leading with the rollup makes search feel less precise than the underlying data really is.

**Ideal behavior**

- Boost canonical task hits for clearly task-shaped queries.
- Consider de-duplicating or downranking projection documents when they mostly repeat canonical state.

### 2026-03-15 - Legacy dependency inference misses simple `depends on` lines during migration

**Workflow**

- Fresh legacy-style repo with checkbox tasks in `projects/*/AGENCY.md`
- Add a small dependency section such as `Build the first page depends on Define the slice`
- Run `hive init`
- Run `hive migrate v1-to-v2`

**What happened**

The tasks were imported cleanly, but `edges_inferred` stayed at `0` and every imported task showed up as ready. In practice, the importer preserved the task titles but failed to recover the obvious dependency chain from plain-English `depends on` lines.

**Why this matters**

This is exactly the kind of lightweight dependency notation a real v1-style repo is likely to contain. If Hive silently drops those edges, the migrated queue looks healthier than it really is and teams may dispatch work too early.

**Ideal behavior**

- Recognize straightforward `X depends on Y` patterns reliably.
- Warn clearly when dependency text could not be mapped into canonical edges.
- Make it easy to review inferred and skipped relations before trusting the migrated ready queue.

### 2026-03-15 - Parallel project and task mutations still assume a single cache writer

**Workflow**

- Fresh workspace with `hive init`
- Run multiple state-changing commands close together, such as:
  - two `hive project create ...` commands at nearly the same time
  - two `hive task link ...` commands at nearly the same time

**What happened**

- Two successful `project create` calls were followed by a `project list` result that only showed one project until a later sync.
- Parallel `task link` calls triggered a raw SQLite error: `UNIQUE constraint failed: projects.path`.

**Why this matters**

Hive is explicitly aimed at multi-agent and tool-driven workflows. If normal write operations collide this easily, the product will feel flaky under exactly the coordination patterns it is trying to support.

**Ideal behavior**

- Serialize cache rebuilds around state-changing commands, or retry safely when the cache is busy.
- Return Hive-level errors instead of raw SQLite exceptions.
- Be explicit in docs if the current cache implementation is single-writer by design.

### 2026-03-15 - Some successful state changes leave the human-facing projections stale without saying so

**Workflow**

- Fresh workspace via `hive quickstart`
- Run a state-changing command such as `hive run accept ...` or `hive migrate v1-to-v2 --rewrite`
- Open `projects/*/AGENCY.md` immediately after the command

**What happened**

The canonical state changed, but the projected `AGENCY.md` did not immediately reflect that change until a later `hive sync projections`. In one rewrite-mode migration, the command reported `rewritten_files`, but the visible project doc still looked unchanged until projections were synced afterward.

**Why this matters**

The CLI feels much more trustworthy when the human-readable surface matches the command that just succeeded. Right now some operations work correctly under the hood while still making the workspace look unchanged to a human operator.

**Ideal behavior**

- Either sync projections automatically after these commands, or
- make the need to run `hive sync projections` unmissable in the success output.

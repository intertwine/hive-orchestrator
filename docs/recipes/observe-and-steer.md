# Observe And Steer

Use this flow when you want Hive to keep work moving while you stay in a supervisor role.

## What to watch

- `hive console home --json` shows the current recommendation, active runs, blocked projects, and inbox items.
- `hive console inbox --json` is the fastest way to see what needs attention right now.
- `hive console runs --json` shows the whole run board, including driver and health.

## Typical loop

1. Check the home view.
2. Start a run with `hive work --project-id <project> --driver <driver> --json`.
3. Let the harness work in its run worktree.
4. Use `hive finish <run-id> --json` when the run is ready for evaluation and promotion.
5. Use steering only when Hive needs help choosing, pausing, or rerouting work.

## Good steering moves

- Pause a noisy or risky project.
- Pin a focus task when a project has too many equally valid options.
- Force review when a run touches sensitive paths.
- Reroute a run when another harness is a better fit for the task.

## What not to do

- Do not edit projections by hand when the canonical task or run state is the real source of truth.
- Do not keep refreshing the workspace manually. Let Hive sync derived state for you.
- Do not steer every step. The point is to intervene only when the system has a real fork in the road.

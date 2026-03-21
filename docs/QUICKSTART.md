# Hive Quickstart

This guide is for everyday users of Hive.

If you want the install matrix and the lane chooser, start with [docs/START_HERE.md](./START_HERE.md).
If you are bringing Hive into an existing repository, use [docs/ADOPT_EXISTING_REPO.md](./ADOPT_EXISTING_REPO.md).
If you are maintaining Hive itself, publishing releases, or updating Homebrew and PyPI automation, use the
maintainer docs instead. This page is about getting from install to first useful task quickly.

## Before You Start

Install Hive with the console extra. Use [docs/START_HERE.md](./START_HERE.md) for the full install matrix and
alternatives.

```bash
uv tool install 'mellona-hive[console]'
```

Then verify:

```bash
hive --version
hive doctor
```

- `hive --version` prints the installed CLI version
- `hive doctor` confirms the workspace layout or tells you the next missing step in plain language

## Create A Workspace And Open The Console

Make a clean directory and run:

```bash
mkdir my-hive
cd my-hive
git init
hive onboard demo --prompt "Create a small React website about bees."
```

Use a fresh directory for this walkthrough. If you run these commands inside the Hive repository checkout,
`hive task ready` will also see the maintainer tasks that ship with this repo.

That command creates your workspace — a `.hive/` directory with machine state, a starter project with governance
policy, and three sequenced tasks. You do not need to hand-write any of that to begin.

Now open the operator console:

```bash
hive console serve
```

Open `http://127.0.0.1:8787/console/` in your browser. The console shows your projects, tasks, governance
health, and — once you start running work — live run status, approvals, and reasoning.

> **CLI-only alternative:** If you prefer staying in the terminal, skip `hive console serve` and use
> `hive next --project-id demo` to see the first ready task directly.

The `git init` is worth doing up front. `hive onboard` leaves the repo in a state where the normal manager loop
and console are ready to go. Hive can manage tasks without Git, but governed runs and promotion work much more
smoothly once the workspace has an initial commit.

## Find Work

Use the manager loop, not raw Markdown edits:

```bash
hive next --project-id demo
hive work <task-id> --owner <your-name> --output SESSION_CONTEXT.md
```

That one command claims the task, checkpoints the repo when needed, starts the governed run, and assembles fresh
startup context. If you pass `--output`, Hive writes a reusable bundle for Codex, Claude Code, or another agent
session. Without `--output`, the plain-text path stays summary-first. Use `--print-context` if you want the full
bundle echoed to stdout.

If `hive console serve` is running in another terminal, the console updates live as you work.

What you should expect here:

- `hive next` points at the ready demo task
- `hive work` claims it, starts a governed run, and can write a reusable context bundle
- `hive work` also prints the dedicated run worktree path; make your edits there, not in the workspace root
- the context bundle is what you hand to Codex, Claude, or another worker session when you want Hive to supervise the loop

If you want to see or save the bundle yourself, use the lower-level commands:

```bash
hive task ready --project-id demo
hive task claim <task-id> --owner <your-name> --ttl-minutes 60
hive context startup --project demo --task <task-id>
```

If you want a file you can hand to another agent session, write it directly:

```bash
hive context startup --project demo --task <task-id> --output SESSION_CONTEXT.md
```

That is the normal daily-use loop in Hive. Add `--json` when you are scripting the CLI instead of reading it yourself.
The console gives you the same loop visually, plus the inbox, run board, campaigns, and run detail inspector.

Once you have more than one project and want the cross-project queue, drop `--project-id demo`.

If you are working from a source checkout and want a saved prompt bundle, `make session PROJECT=demo`
writes the same startup context to `projects/demo/SESSION_CONTEXT.md`. Treat that as a maintainer
convenience, not the normal installed-user path.

## Create Better Tasks From The CLI

You do not need to drop into raw Markdown to define useful work. Hive task records already support labels,
relevant files, acceptance criteria, and summary sections:

```bash
hive task create \
  --project-id demo \
  --title "Add a launch hero section" \
  --label launch \
  --label website \
  --relevant-file src/App.jsx \
  --acceptance "The hero explains what Hive is in one screen." \
  --acceptance "The page still passes lint and tests." \
  --summary "Keep the first version small and shippable."
```

You can refine the task later without editing the task file by hand:

```bash
hive task update <task-id> \
  --label copy \
  --relevant-file src/styles.css \
  --acceptance "The mobile layout stays readable." \
  --notes "Tighten the copy after the structure is in place."
```

Use `--clear-labels`, `--clear-relevant-files`, `--clear-acceptance`, or `--clear-parent` when you want to replace
those fields cleanly.

## Make The First Finish Feel Real

The starter defaults allow no-change runs to promote cleanly, so your first `hive finish` should succeed even
if you have not made any edits yet. This lets you verify the full loop works before adding real evaluators.

To see a more meaningful promotion, make one small change inside the run worktree that `hive work` printed
(usually `.hive/worktrees/run_<id>/`), then run `hive finish`. The evaluator runs, the change promotes, and the
task auto-closes.

Important detail: governed edits happen inside the run worktree, not in the workspace root. If you edit files
only in the workspace root, `hive finish` will correctly see no run changes.

Once you are ready for production governance, tighten the defaults in `projects/demo/PROGRAM.md`:

- Set `promotion.allow_accept_without_changes: false` to require real changes
- Set `promotion.auto_close_task: false` to add an explicit review step
- Replace the `local-smoke` evaluator with repo-specific checks

## Governed Runs

When a task should run through the governed worktree flow, make sure `projects/*/PROGRAM.md` has at least one
required evaluator and lists it under `promotion.requires_all`. Freshly onboarded blank workspaces may already carry
the fallback `local-smoke` evaluator so the happy path works immediately. That starter stub proves the loop is wired
up, but it does not validate project behavior. Replace it with repo-specific evaluators once you know the real
checks. If a project is still blocked, run:

```bash
hive program doctor demo
```

After that, the shortest path is:

```bash
hive work <task-id> --owner <your-name>
hive finish <run-id>
```

Under the hood, that covers the same governed sequence:

- opens a dedicated run worktree and branch
- captures evaluator output and patch data
- marks the run accepted
- merges the accepted run back into your main branch
- prunes the run worktree when you pass `--cleanup-worktree`
- deletes the merged local run branch after that cleanup step

If you want to separate acceptance from merge, keep the lower-level run commands separate:

```bash
hive run accept <run-id>
hive run promote <run-id>
```

If you want to clear old terminal worktrees later, run:

```bash
hive run cleanup --terminal
```

## The Files That Matter

- `.hive/tasks/*.md` is the canonical task store.
- `projects/*/AGENCY.md` is the human project document.
- `projects/*/PROGRAM.md` is the policy contract for autonomous work.
- `.hive/runs/*` stores governed run artifacts.

The short version is:

- machine truth lives under `.hive/`
- human context lives in Markdown

## Optional Next Steps

- Keep `hive console serve` running in a terminal while you work — it updates live
- Use `hive memory observe --note "..."` to preserve useful decisions
- Use `hive sync projections` after task, run, or memory changes
- Add `mellona-hive[mcp]` if you want the thin `search` + bounded local `execute` adapter for MCP
- If you installed through Homebrew, add console and MCP extras through `uv tool`, `pipx`,
  or `pip` as described in [docs/START_HERE.md](./START_HERE.md)

## Troubleshooting

If you are unsure what to do next:

```bash
hive doctor
```

That will tell you whether the workspace is missing layout, projects, tasks, or cache, and it will print the next recommended step.

If the worker runtime is fine but sandboxed execution is blocked, inspect the backend truth directly:

```bash
hive sandbox doctor --json
```

The sandbox profile and backend guide lives in [docs/recipes/sandbox-doctor.md](./recipes/sandbox-doctor.md).

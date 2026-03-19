# Hive Quickstart

This guide is for everyday users of Hive.

If you want the install matrix and the lane chooser, start with [docs/START_HERE.md](./START_HERE.md).
If you are bringing Hive into an existing repository, use [docs/ADOPT_EXISTING_REPO.md](./ADOPT_EXISTING_REPO.md).
If you are maintaining Hive itself, publishing releases, or updating Homebrew and PyPI automation, use the
maintainer docs instead. This page is about getting from install to first useful task quickly.

## Before You Start

Install the base CLI first. Use [docs/START_HERE.md](./START_HERE.md) for the canonical install matrix, optional
extras, and git-install fallback.

Then verify the CLI you installed:

```bash
hive --version
hive doctor
```

## Create A Workspace In One Command

Make a clean directory and run:

```bash
mkdir my-hive
cd my-hive
git init
hive onboard demo --title "Demo project" --objective "Ship one governed slice."
```

Use a fresh directory for this walkthrough. If you run these commands inside the Hive repository checkout, `hive task ready` will also see the maintainer tasks that ship with this repo.

That command:

- bootstraps `.hive/`
- creates `GLOBAL.md` and `AGENTS.md`
- scaffolds `projects/demo/AGENCY.md`
- scaffolds `projects/demo/PROGRAM.md`
- creates a small starter task chain
- runs Program Doctor and applies a safe starter evaluator when there is one obvious choice
- syncs projections and cache

You do not need to hand-write any of that to begin.

The `git init` is worth doing up front. `hive onboard` leaves the repo in a state where the normal manager loop and
console are ready to go. If you want an explicit checkpoint commit after onboarding, run:

```bash
hive workspace checkpoint --message "Bootstrap Hive workspace"
```

Hive can manage tasks without Git, but governed runs and promotion work much more smoothly once the workspace has an
initial commit.

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

If you want the live observe-and-steer board, install `mellona-hive[console]` first and run `hive console serve` in a
separate terminal.

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

- Use `hive next`, `hive work`, and `hive finish` if you want the manager-style happy path
- Use `hive memory observe --note "..."` to preserve useful decisions
- Use `hive sync projections` after task, run, or memory changes
- Install `mellona-hive[console]` and run `hive console serve` if you want the visual observe-and-steer command center
- Install `mellona-hive[mcp]` and run `hive-mcp` if you want the thin `search` + bounded local `execute` adapter
- If you installed through Homebrew and want the console or MCP support, add those extras through `uv tool`, `pipx`,
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

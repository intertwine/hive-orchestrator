# Hive Quickstart

This guide is for everyday users of Hive.

If you want the install matrix and the lane chooser, start with [docs/START_HERE.md](./START_HERE.md).
If you are bringing Hive into an existing repository, use [docs/ADOPT_EXISTING_REPO.md](./ADOPT_EXISTING_REPO.md).
If you are maintaining Hive itself, publishing releases, or updating Homebrew and PyPI automation, use the
maintainer docs instead. This page is about getting from install to first useful task quickly.

## Install

Pick the install path you already trust:

```bash
uv tool install agent-hive
```

```bash
pipx install agent-hive
```

```bash
brew tap intertwine/tap
brew install intertwine/tap/agent-hive
```

Then verify:

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
hive quickstart demo --title "Demo project"
hive workspace checkpoint --message "Bootstrap Hive workspace"
```

Use a fresh directory for this walkthrough. If you run these commands inside the Hive repository checkout, `hive task ready` will also see the maintainer tasks that ship with this repo.

That command:

- bootstraps `.hive/`
- creates `GLOBAL.md` and `AGENTS.md`
- scaffolds `projects/demo/AGENCY.md`
- scaffolds `projects/demo/PROGRAM.md`
- creates a small starter task chain
- syncs projections and cache

You do not need to hand-write any of that to begin.

The `git init` and first `hive workspace checkpoint` are worth doing up front. Hive can manage tasks without Git,
but governed runs and promotion work much more smoothly once the workspace has an initial commit.

## Find Work

```bash
hive next --project-id demo
```

If you want the manager-style happy path, take the recommended task straight into work:

```bash
hive work <task-id> --owner <your-name> --output SESSION_CONTEXT.md
```

That one command checkpoints the repo when needed, claims the task, starts the governed run, and assembles fresh
startup context. If you pass `--output`, Hive writes a reusable bundle for Claude, Codex, or another agent session.

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
required evaluator and lists it under `promotion.requires_all`. The default stub is intentionally safe and will block
autonomous acceptance until you make that decision. After that, the shortest path is:

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
- Install `agent-hive[dashboard]` and run `hive dashboard` if you want a visual observe-and-steer view
- Install `agent-hive[mcp]` and run `hive-mcp` if you want the thin `search` + bounded local `execute` adapter
- If you installed through Homebrew and want dashboard or MCP support, add those extras through `uv tool`, `pipx`,
  or `pip` as described in [docs/START_HERE.md](./START_HERE.md)

## Troubleshooting

If you are unsure what to do next:

```bash
hive doctor
```

That will tell you whether the workspace is missing layout, projects, tasks, or cache, and it will print the next recommended step.

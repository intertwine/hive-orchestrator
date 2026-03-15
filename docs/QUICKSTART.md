# Hive Quickstart

This guide is for everyday users of Hive.

If you are maintaining Hive itself, publishing releases, or updating Homebrew and PyPI automation, use the maintainer docs instead. This page is about getting from install to first useful task quickly.

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
hive quickstart demo --title "Demo project"
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

## Find Work

```bash
hive task ready --project-id demo
```

Claim the first task:

```bash
hive task claim <task-id> --owner <your-name> --ttl-minutes 60
```

Build a startup context:

```bash
hive context startup --project demo --task <task-id>
```

If you want a file you can hand to another agent session, write it directly:

```bash
hive context startup --project demo --task <task-id> --output SESSION_CONTEXT.md
```

That is the normal daily-use loop in Hive. Add `--json` when you are scripting the CLI instead of reading it yourself.

Once you have more than one project and want the cross-project queue, drop `--project-id demo`.

## The Files That Matter

- `.hive/tasks/*.md` is the canonical task store.
- `projects/*/AGENCY.md` is the human project document.
- `projects/*/PROGRAM.md` is the policy contract for autonomous work.
- `.hive/runs/*` stores governed run artifacts.

The short version is:

- machine truth lives under `.hive/`
- human context lives in Markdown

## Optional Next Steps

- Use `hive run start <task-id>` if the project has evaluator policy in `PROGRAM.md`
- Use `hive memory observe --note "..."` to preserve useful decisions
- Use `hive sync projections` after task, run, or memory changes
- Install `agent-hive[dashboard]` and run `hive dashboard` if you want a visual workspace view
- Install `agent-hive[mcp]` and run `hive-mcp` if you want the thin MCP server

## Troubleshooting

If you are unsure what to do next:

```bash
hive doctor
```

That will tell you whether the workspace is missing layout, projects, tasks, or cache, and it will print the next recommended step.

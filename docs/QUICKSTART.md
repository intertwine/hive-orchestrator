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
```

## Create A Workspace In One Command

Make a clean directory and run:

```bash
mkdir my-hive
cd my-hive
hive quickstart demo --title "Demo project" --json
```

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
hive task ready --json
```

Claim the first task:

```bash
hive task claim <task-id> --owner <your-name> --ttl-minutes 60 --json
```

Build a startup context:

```bash
hive context startup --project demo --task <task-id> --json
```

That is the normal daily-use loop in Hive.

## The Files That Matter

- `.hive/tasks/*.md` is the canonical task store.
- `projects/*/AGENCY.md` is the human project document.
- `projects/*/PROGRAM.md` is the policy contract for autonomous work.
- `.hive/runs/*` stores governed run artifacts.

The short version is:

- machine truth lives under `.hive/`
- human context lives in Markdown

## Optional Next Steps

- Use `hive run start <task-id> --json` if the project has evaluator policy in `PROGRAM.md`
- Use `hive memory observe --note "..." --json` to preserve useful decisions
- Use `hive sync projections --json` after task, run, or memory changes
- Use the optional dashboard if you want a visual view of the workspace

## Troubleshooting

If you are unsure what to do next:

```bash
hive doctor --json
```

That will tell you whether the workspace is missing layout, projects, tasks, or cache, and it will print the next recommended step.

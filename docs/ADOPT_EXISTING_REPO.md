# Adopt Hive In An Existing Repo

This guide is for teams who already have a repository and want to add Hive without starting over.

If you want a fresh demo workspace instead, use [Quickstart](./QUICKSTART.md). If you are working on Hive itself,
use [Maintaining Hive](./MAINTAINING.md).

## Case 1: Your Repo Does Not Use Hive Yet

Install Hive, then work from the root of the repo you want to manage:

```bash
cd your-repo
hive adopt app --title "App" --objective "Delegate the first governed slice safely."
```

If you want to stay closer to the primitives, you can still do the same thing in smaller steps:

```bash
hive init
hive project create app --title "App"
```

Then create the first task:

```bash
hive task create \
  --project-id app \
  --title "Describe the first real task for this repo" \
  --label setup \
  --relevant-file src/app.py \
  --acceptance "The task is small enough to finish in one session." \
  --summary "Keep the first slice narrow and concrete."
```

Then run the normal loop:

```bash
hive console serve
hive next --project-id app
hive work --project-id app --owner <your-name> --output SESSION_CONTEXT.md
```

That manager loop only works once `projects/app/PROGRAM.md` has at least one required evaluator and lists it under
`promotion.requires_all`. `hive adopt` runs Program Doctor during setup and will apply a safe default when it has one
obvious choice. If you need to tighten the policy yourself, run:

```bash
hive program doctor app
```

If this repository is brand new or you want governed runs immediately after adding Hive, create a first commit for
the workspace state:

```bash
hive workspace checkpoint --message "Bootstrap Hive workspace"
```

## Case 2: Your Repo Has Older Hive Checklists

If the repo already has older `GLOBAL.md` or `projects/*/AGENCY.md` checklist history, import it first:

```bash
hive migrate v1-to-v2 --dry-run
```

If the preview looks right, run the real import:

```bash
hive migrate v1-to-v2
```

If you want the old checklist section replaced with generated rollups after the import:

```bash
hive migrate v1-to-v2 --rewrite
```

That keeps the old history available in git while moving the machine state into `.hive/tasks/*.md`.

## After The Cutover

Once Hive is in the repo, the daily path is the same everywhere:

```bash
hive console serve
hive next
hive work --project-id <project-id> --owner <your-name>
hive finish <run-id>
```

`hive work` assumes the project already has a real `PROGRAM.md` contract. If the file is still on the default
stub, Hive will stop and tell you what to configure.

The short mental model is simple:

- `.hive/` is the machine substrate
- `projects/*/AGENCY.md` stays readable for humans
- `projects/*/PROGRAM.md` governs autonomous runs

## When To Widen The Setup

Start with the base CLI. Add extras only when you need them:

- install `agent-hive[console]` if you want the observe-and-steer console
- install `agent-hive[mcp]` if you want the thin `search` + bounded local `execute` adapter
- install the Claude Code GitHub App only if issue-driven dispatch is part of your workflow

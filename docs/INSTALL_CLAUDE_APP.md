# Installing the Claude Code GitHub App

This is optional.

Hive works fine with the CLI alone. Install the Claude Code GitHub App only if you want GitHub issues and `@claude` mentions to become part of your workflow.

If you are brand new to Hive, start with [docs/QUICKSTART.md](./QUICKSTART.md) first. Get one local project working through the CLI, then add the GitHub App if issue-driven dispatch actually helps your workflow.

## When it helps

Install the app if you want any of these:

- issue-driven assignment instead of direct local CLI work
- `@claude` responses on issues or PR comments
- PRs opened by Claude after a GitHub-triggered work loop

If you mostly work locally with `hive task ready`, `hive context startup`, and normal Git branches, you can skip this guide.

## Install

1. Open the [Claude Code GitHub App](https://github.com/apps/claude).
2. Click **Install** or **Configure**.
3. Choose the organization or account that owns your repository.
4. Grant access to this repository.
5. Confirm the installation in **Settings > GitHub Apps**.

## Quick check

Open an issue and mention `@claude` in the body. A simple test is enough:

```markdown
@claude Please confirm that you can read this issue.
```

If the app is installed correctly, Claude should reply within a few minutes.

## How it fits into Hive

The normal Hive flow stays the same:

1. `hive task ready` finds ready work. If you are following the demo walkthrough, use `hive task ready --project-id demo`.
2. `hive task claim <task-id> --owner <your-name> --ttl-minutes 60` leases one task.
3. `hive context startup --project <project-id> --task <task-id>` builds task-specific context.
4. Optional dispatch tools can turn that work into a GitHub issue.
5. Claude can pick up the issue when it sees `@claude`.

The app is a convenience layer. It is not the core orchestration engine.

## Repository settings

Make sure these are enabled:

- GitHub Issues
- GitHub Actions

If you use the optional dispatcher, the workflow or token that opens issues also needs `issues: write`.

## Troubleshooting

### Claude does not respond

- Check that the app is installed on the repository you are testing.
- Check that the issue or PR comment includes `@claude`.
- Give it a few minutes before assuming it failed.

### The dispatcher does not open issues

- Verify ready work exists first: `uv run hive task ready --json`
- From a checkout, dry-run the optional dispatcher preview: `uv run python -m src.agent_dispatcher --dry-run`
- Verify the GitHub token has permission to create issues

## Security notes

- The app only has access to repositories you authorize.
- Claude still works through pull requests, so changes stay reviewable.
- Branch protection remains your backstop.

## Related docs

- [Quickstart](./QUICKSTART.md)
- [README](../README.md)
- [Claude Code documentation](https://docs.anthropic.com/claude-code)

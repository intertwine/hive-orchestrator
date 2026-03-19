# Installing the Claude Code GitHub App

This is optional.

Hive works fine with the CLI alone. Install the Claude Code GitHub App if you want Anthropic-managed PR reviews or
you plan to add your own Claude GitHub automation on top of the app.

For pull request review, Anthropic's current best-practice path is the managed Code Review app flow, not a repo-local
custom GitHub Actions workflow. This repository no longer ships a `claude.yml` Actions workflow for review automation.
If Anthropic Code Review is enabled for the repo, use a top-level `@claude review` comment or the configured automatic
review mode in Anthropic admin settings.

If you are brand new to Hive, start with [docs/START_HERE.md](./START_HERE.md) first. Get one local project working
through the CLI, then add the GitHub App if issue-driven dispatch actually helps your workflow.

## When it helps

Install the app if you want any of these:

- managed Anthropic PR reviews via `@claude review` or repo-level review settings
- a foundation for custom Claude GitHub automation that you maintain yourself

If you mostly work locally with `hive task ready`, `hive context startup`, and normal Git branches, you can skip this guide.

## Installed-user setup

1. Open the [Claude Code GitHub App](https://github.com/apps/claude).
2. Click **Install** or **Configure**.
3. Choose the organization or account that owns your repository.
4. Grant access to this repository.
5. Confirm the installation in **Settings > GitHub Apps**.

## Quick check

For managed Code Review, open a non-draft PR and leave a top-level comment:

```markdown
@claude review
```

If Anthropic Code Review is enabled correctly for the repository, a review/check should appear within a few minutes.

For maintainer-critical PRs, local Claude review is also a valid primary or fallback path when you want a
deterministic completion loop. The built-in `claude -p "/review <pr-number>"` flow works well for this. If you use
local review instead of the GitHub app, paste the findings and resolutions into the PR thread so the final review
state is visible to other maintainers.

If you want generic `@claude` issue or PR automation beyond review, Anthropic recommends GitHub Actions for that. This
repository does not ship that automation workflow anymore; add your own from Anthropic's examples if you intentionally
want Claude to implement code or open PRs from GitHub comments.

## How it fits into Hive

The normal Hive flow stays the same:

1. `hive task ready` finds ready work. If you are following the demo walkthrough, use `hive task ready --project-id demo`.
2. `hive task claim <task-id> --owner <your-name> --ttl-minutes 60` leases one task.
3. `hive context startup --project <project-id> --task <task-id>` builds task-specific context.
4. Optional dispatch tools can turn that work into a GitHub issue.
5. If you add your own Claude automation workflow, Claude can pick up the issue from GitHub. Managed Code Review alone
   is review-focused and does not replace Hive's local CLI loop.

The app is a convenience layer. It is not the core orchestration engine.

## Repository settings

Make sure these are enabled:

- GitHub Issues
- GitHub Actions if you use the optional dispatcher or other repo-owned automations

If you use the optional dispatcher, the workflow or token that opens issues also needs `issues: write`.

## Troubleshooting

### Claude does not respond

- Check that the app is installed on the repository you are testing.
- Check that you are testing the flow you actually enabled:
  - managed review: top-level PR comment `@claude review`
  - custom automation: your own GitHub Actions workflow
- Give it a few minutes before assuming it failed.

### `@claude review` does not start a PR review

- Check Anthropic admin settings and confirm Code Review is enabled for this repository.
- Post `@claude review` as a top-level PR comment, not an inline diff comment.
- Make sure the PR is open and not a draft.
- If the repository is in manual review mode, the first `@claude review` opts that PR into review.
- Treat the request as still pending until GitHub shows a new Claude comment or review artifact on the latest PR
  head. An `eyes` reaction alone is not completion.

## Checkout-only dispatcher diagnostics

This section is only for maintainers or teams running the optional dispatcher from a source checkout.

- Verify ready work exists first: `hive task ready --json`
- From a checkout, dry-run the optional dispatcher preview: `uv run python -m src.agent_dispatcher --dry-run`
- Verify the GitHub token has permission to create issues
- If you only want local Hive usage, skip the dispatcher entirely

## Security notes

- The app only has access to repositories you authorize.
- Claude still works through pull requests, so changes stay reviewable.
- Branch protection remains your backstop.

## Related docs

- [Quickstart](./QUICKSTART.md)
- [README](../README.md)
- [Claude Code documentation](https://docs.anthropic.com/claude-code)

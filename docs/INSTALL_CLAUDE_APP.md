# Installing the Claude Code GitHub App

This guide walks you through installing the Claude Code GitHub App on your repository to enable automated AI agent work via `@claude` mentions.

## Overview

The Agent Hive system uses the [Claude Code GitHub App](https://github.com/apps/claude) to automatically assign work to Claude. When the Agent Dispatcher creates an issue with `@claude` mention, the Claude Code app responds and works on the task.

## Prerequisites

- Repository owner or admin access
- GitHub account with access to install apps

## Installation Steps

### Step 1: Visit the Claude Code App Page

Go to the official Claude Code GitHub App:

**https://github.com/apps/claude**

### Step 2: Install the App

1. Click **"Install"** or **"Configure"**
2. Select the organization or account where you want to install
3. Choose repository access:
   - **All repositories** - Claude can respond to mentions in any repo
   - **Only select repositories** - Choose specific repos (recommended for security)
4. Select this repository: `intertwine/hive-orchestrator`
5. Click **"Install"**

### Step 3: Verify Installation

After installation, verify it's working:

1. Go to your repository settings
2. Navigate to **Settings > GitHub Apps**
3. Confirm "Claude" appears in the installed apps list

### Step 4: Test the Integration

Create a test issue to verify Claude responds:

```markdown
Title: Test Claude Integration

Body:
@claude Please confirm you can see this issue by responding with a brief acknowledgment.
```

Claude should respond within a few minutes.

## How It Works with Agent Hive

1. **Hive projections/cache** can be refreshed on demand with `uv run hive sync projections --json`
2. **Ready work** is available from `uv run hive task ready --json` and the dashboard
3. **Optional manual dispatch** can open a GitHub issue with `@claude` if you want issue-based assignment
4. **Claude Code** also responds directly to `@claude` mentions on issues and PR comments
5. Claude creates a PR with the changes when it completes the requested work

### Workflow Diagram

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Ready Work     │────▶│ Optional Manual   │────▶│  GitHub Issue   │
│  (`hive task`)  │     │ Dispatcher        │     │  (@claude)      │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Pull Request  │◀────│   Claude Code    │◀────│  Claude App     │
│   (changes)     │     │   (work on task) │     │  (picks up)     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## Configuration

### Repository Settings

Ensure your repository has the following settings:

1. **Issues enabled** - Settings > Features > Issues ✓
2. **Actions enabled** - Settings > Actions > General > Allow all actions

### Workflow Permissions

The GitHub Actions workflows need proper permissions. Verify in `.github/workflows/agent-assignment.yml`:

```yaml
permissions:
  contents: write
  issues: write
```

## Troubleshooting

### Claude doesn't respond to @mention

1. Verify the app is installed: Settings > GitHub Apps
2. Check the issue has a valid `@claude` mention in the body
3. Ensure the repository is selected in the app's configuration
4. Wait a few minutes - Claude may have processing delays

### Agent Dispatcher issues not created

1. Run manually to debug: `uv run python -m src.agent_dispatcher --dry-run`
2. Check canonical ready work: `uv run hive task ready --json`
3. Verify `GITHUB_TOKEN` is set with `issues: write` permission

### Claude creates PR but can't push

1. Ensure Claude app has `contents: write` permission
2. Check branch protection rules allow the app to push
3. Verify the app is authorized for the target branch

## Security Considerations

- Claude Code only responds to `@claude` mentions
- The app only has access to repositories you explicitly authorize
- All changes are made via Pull Requests for review
- Branch protection rules are respected

## Manual Trigger

To manually trigger agent assignment:

```bash
# Inspect canonical ready tasks first
uv run hive task ready --json

# Dry run (preview without changes)
uv run python -m src.agent_dispatcher --dry-run

# Actually dispatch work
uv run python -m src.agent_dispatcher
```

Or via GitHub Actions:

1. Go to **Actions** tab
2. Select **"Ready Work Snapshot"** workflow
3. Click **"Run workflow"**

## Additional Resources

- [Claude Code Documentation](https://docs.anthropic.com/claude-code)
- [GitHub Apps Documentation](https://docs.github.com/en/apps)
- [Agent Hive README](../README.md)

## Support

If you encounter issues:

1. Check the [Claude Code GitHub Issues](https://github.com/anthropics/claude-code/issues)
2. Review workflow logs in the Actions tab
3. Open an issue in this repository

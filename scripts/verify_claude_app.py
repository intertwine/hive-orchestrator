#!/usr/bin/env python3
"""Verify Claude Code GitHub App installation and configuration.

This script checks that the Claude Code GitHub App is properly installed
and configured for use with the Agent Hive system.

Usage:
    uv run python scripts/verify_claude_app.py
    uv run python scripts/verify_claude_app.py --repo owner/repo
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str]) -> tuple[int, str, str]:
    """Run a command and return exit code, stdout, stderr."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def run_hive_json(args: list[str]) -> dict | None:
    """Run the installed Hive CLI in JSON mode and parse the response."""
    code, stdout, stderr = run_command([sys.executable, "-m", "hive", "--json", *args])
    if code != 0:
        if stderr.strip():
            print(stderr.strip())
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        print("✗ Could not parse Hive CLI output")
        return None


def get_repo_info() -> tuple[str, str] | None:
    """Get the current repository owner and name from git remote."""
    code, stdout, _ = run_command(["git", "remote", "get-url", "origin"])
    if code != 0:
        return None

    url = stdout.strip()
    # Handle both SSH and HTTPS URLs
    # git@github.com:owner/repo.git
    # https://github.com/owner/repo.git
    if "github.com" not in url:
        return None

    if url.startswith("git@"):
        # SSH format
        path = url.split(":")[-1]
    else:
        # HTTPS format
        path = url.split("github.com/")[-1]

    path = path.rstrip(".git")
    parts = path.split("/")
    if len(parts) >= 2:
        return parts[0], parts[1]
    return None


def check_github_token() -> bool:
    """Check if GITHUB_TOKEN environment variable is set."""
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        print("✓ GITHUB_TOKEN is set")
        return True
    print("✗ GITHUB_TOKEN is not set")
    print("  Set it with: export GITHUB_TOKEN=your_token")
    return False


def check_git_remote() -> bool:
    """Check if git remote is configured."""
    repo_info = get_repo_info()
    if repo_info:
        owner, repo = repo_info
        print(f"✓ Git remote configured: {owner}/{repo}")
        return True
    print("✗ Git remote not configured or not a GitHub repository")
    return False


def check_workflow_files() -> bool:
    """Check if required workflow files exist."""
    workflows_dir = Path(".github/workflows")
    required_files = ["projection-sync.yml", "agent-assignment.yml"]

    all_exist = True
    for filename in required_files:
        filepath = workflows_dir / filename
        if filepath.exists():
            print(f"✓ Workflow file exists: {filepath}")
        else:
            print(f"✗ Workflow file missing: {filepath}")
            all_exist = False

    return all_exist


def check_workflow_permissions() -> bool:
    """Check if workflow has proper permissions."""
    workflow_path = Path(".github/workflows/agent-assignment.yml")
    if not workflow_path.exists():
        return False

    content = workflow_path.read_text()
    has_contents = "contents:" in content and "write" in content
    has_issues = "issues:" in content and "write" in content

    if has_contents and has_issues:
        print("✓ Workflow has required permissions (contents: write, issues: write)")
        return True

    print("✗ Workflow missing required permissions")
    if not has_contents:
        print("  - Missing: contents: write")
    if not has_issues:
        print("  - Missing: issues: write")
    return False


def check_workspace_state() -> bool:
    """Check that Hive sees a usable workspace through the public CLI."""
    doctor = run_hive_json(["doctor"])
    if doctor is None:
        print("✗ Could not read workspace state through `python -m hive doctor --json`")
        return False

    if not doctor.get("checks", {}).get("layout"):
        print("✗ Hive workspace layout is missing")
        print("  Run: hive quickstart demo --title \"Demo project\"")
        return False

    ready_payload = run_hive_json(["task", "ready"])
    ready_count = len(ready_payload.get("tasks", [])) if ready_payload else 0
    print(
        "✓ Hive workspace detected: "
        f"{doctor.get('projects', 0)} project(s), "
        f"{doctor.get('tasks', 0)} task(s), "
        f"{ready_count} ready"
    )
    return True


def print_installation_guide():
    """Print the Claude Code app installation guide."""
    print("\n" + "=" * 60)
    print("Claude Code GitHub App Installation Guide")
    print("=" * 60)
    print(
        """
To install the Claude Code GitHub App:

1. Visit: https://github.com/apps/claude

2. Click "Install" or "Configure"

3. Select your organization/account

4. Choose repository access:
   - Select "Only select repositories"
   - Add this repository

5. Click "Install"

6. Verify installation:
   - Go to Settings > GitHub Apps
   - Confirm "Claude" is listed

For detailed instructions, see:
  docs/INSTALL_CLAUDE_APP.md
"""
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Verify Claude Code GitHub App installation")
    parser.add_argument(
        "--repo",
        help="Repository in owner/repo format (auto-detected if not provided)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Claude Code GitHub App Verification")
    print("=" * 60)
    print()

    checks_passed = 0
    total_checks = 5

    # Check 1: Git remote
    print("[1/5] Checking git remote...")
    if check_git_remote():
        checks_passed += 1
    print()

    # Check 2: GitHub token
    print("[2/5] Checking GITHUB_TOKEN...")
    if check_github_token():
        checks_passed += 1
    print()

    # Check 3: Workflow files
    print("[3/5] Checking workflow files...")
    if check_workflow_files():
        checks_passed += 1
    print()

    # Check 4: Workflow permissions
    print("[4/5] Checking workflow permissions...")
    if check_workflow_permissions():
        checks_passed += 1
    print()

    # Check 5: Hive workspace state
    print("[5/5] Checking Hive workspace state...")
    if check_workspace_state():
        checks_passed += 1
    print()

    # Summary
    print("=" * 60)
    print(f"Verification Complete: {checks_passed}/{total_checks} checks passed")
    print("=" * 60)

    if checks_passed == total_checks:
        print("\n✓ All local checks passed!")
        print("\nNext steps:")
        print("1. Install the Claude Code app (if not already):")
        print("   https://github.com/apps/claude")
        print("\n2. Inspect canonical ready work:")
        print("   uv run hive task ready --json")
        print("\n3. Optional: preview manual GitHub issue dispatch:")
        print("   uv run python -m src.agent_dispatcher --dry-run")
    else:
        print("\n✗ Some checks failed. Review the issues above.")
        print_installation_guide()

    return 0 if checks_passed == total_checks else 1


if __name__ == "__main__":
    sys.exit(main())

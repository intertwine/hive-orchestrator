#!/usr/bin/env python3
"""
Agent Hive Agent Dispatcher

Finds ready work, assembles context, creates GitHub issues, and assigns
work to Claude Code for autonomous execution.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import frontmatter
from dotenv import load_dotenv

from src.cortex import Cortex
from src.context_assembler import (
    build_issue_title,
    build_issue_body,
    build_issue_labels,
    get_next_task,
)

# Load environment variables
load_dotenv()


class DispatcherError(Exception):
    """Base exception for Dispatcher-related errors."""


class AgentDispatcher:
    """
    The Agent Dispatcher for Agent Hive.

    Responsibilities:
    - Find ready work using Cortex
    - Select highest priority project
    - Build rich context for agent assignment
    - Create GitHub issue with @claude mention
    - Update AGENCY.md to claim ownership
    """

    # Agent name used when claiming projects
    AGENT_NAME = "claude-code"

    def __init__(self, base_path: str = None, dry_run: bool = False):
        """
        Initialize the Agent Dispatcher.

        Args:
            base_path: Base path for the hive (defaults to current directory)
            dry_run: If True, don't actually create issues or modify files
        """
        self.base_path = Path(base_path or os.getcwd())
        self.dry_run = dry_run
        self.cortex = Cortex(str(self.base_path))

    def validate_environment(self) -> bool:
        """
        Validate that required tools are available.

        Returns:
            True if environment is valid, False otherwise
        """
        # Check if gh CLI is available
        try:
            result = subprocess.run(
                ["gh", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if result.returncode != 0:
                print("   gh CLI not available or version check failed")
                return False
        except FileNotFoundError:
            print("   gh CLI not installed")
            return False
        except subprocess.TimeoutExpired:
            print("   gh CLI timed out")
            return False

        # Check gh auth status
        try:
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if result.returncode != 0:
                print("   gh CLI not authenticated. Run: gh auth login")
                return False
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

        return True

    def select_work(self, projects: List[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Select the highest priority project ready for work.

        Priority ordering:
        1. Priority level (critical > high > medium > low)
        2. Age (oldest last_updated first)

        Args:
            projects: Optional list of ready projects. If None, discovers them.

        Returns:
            Selected project dict, or None if no work available
        """
        if projects is None:
            projects = self.cortex.ready_work()

        if not projects:
            return None

        # Priority ordering
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}

        def sort_key(project):
            metadata = project.get("metadata", {})
            priority = metadata.get("priority", "medium")
            last_updated = metadata.get("last_updated", "")

            # Parse last_updated for age-based sorting (older = higher priority)
            try:
                if last_updated:
                    # ISO format timestamp
                    timestamp = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
                else:
                    timestamp = datetime.max.replace(tzinfo=None)
            except ValueError:
                timestamp = datetime.max.replace(tzinfo=None)

            return (priority_order.get(priority, 2), timestamp)

        sorted_projects = sorted(projects, key=sort_key)
        return sorted_projects[0] if sorted_projects else None

    def is_already_assigned(self, project: Dict[str, Any]) -> bool:
        """
        Check if a project is already assigned (has an owner).

        This is the primary duplicate prevention mechanism.

        Args:
            project: Project to check

        Returns:
            True if already assigned, False otherwise
        """
        owner = project.get("metadata", {}).get("owner")
        return owner is not None

    def claim_project(self, project: Dict[str, Any], issue_url: str) -> bool:
        """
        Claim a project by setting owner and adding issue link to AGENCY.md.

        Args:
            project: Project to claim
            issue_url: URL of the created GitHub issue

        Returns:
            True on success, False on failure
        """
        if self.dry_run:
            print(f"   [DRY RUN] Would claim project and add issue link: {issue_url}")
            return True

        try:
            project_path = Path(project["path"])

            with open(project_path, "r", encoding="utf-8") as f:
                post = frontmatter.load(f)

            # Update metadata
            post.metadata["owner"] = self.AGENT_NAME
            post.metadata["last_updated"] = datetime.utcnow().isoformat() + "Z"

            # Add agent note with issue link
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
            note = (
                f"\n- **{timestamp} - Agent Dispatcher**: "
                f"Assigned to Claude Code. Issue: {issue_url}"
            )

            # Find or create Agent Notes section
            if "## Agent Notes" in post.content:
                # Append to existing section
                post.content = post.content.replace(
                    "## Agent Notes", f"## Agent Notes{note}", 1
                )
            else:
                # Add new section at the end
                post.content += f"\n\n## Agent Notes{note}"

            # Write back
            with open(project_path, "w", encoding="utf-8") as f:
                f.write(frontmatter.dumps(post))

            return True

        except Exception as e:
            print(f"   ERROR claiming project: {e}")
            return False

    def create_github_issue(
        self, title: str, body: str, labels: List[str]
    ) -> Optional[str]:
        """
        Create a GitHub issue using the gh CLI.

        Args:
            title: Issue title
            body: Issue body (markdown)
            labels: List of labels to apply

        Returns:
            Issue URL on success, None on failure
        """
        if self.dry_run:
            print(f"   [DRY RUN] Would create issue: {title}")
            print(f"   [DRY RUN] Labels: {', '.join(labels)}")
            return "https://github.com/example/repo/issues/999"

        try:
            # Build gh command
            cmd = ["gh", "issue", "create", "--title", title, "--body", body]

            # Add labels
            for label in labels:
                cmd.extend(["--label", label])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )

            if result.returncode != 0:
                # Check if it's a label error (labels might not exist)
                if "label" in result.stderr.lower():
                    print("   Warning: Label issue, retrying without labels...")
                    # Retry without labels
                    cmd = ["gh", "issue", "create", "--title", title, "--body", body]
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=60,
                        check=False,
                    )

                if result.returncode != 0:
                    print(f"   ERROR creating issue: {result.stderr}")
                    return None

            # gh issue create outputs the issue URL
            issue_url = result.stdout.strip()
            return issue_url

        except subprocess.TimeoutExpired:
            print("   ERROR: gh command timed out")
            return None
        except Exception as e:
            print(f"   ERROR creating issue: {e}")
            return None

    def dispatch(self, project: Dict[str, Any]) -> bool:
        """
        Dispatch a single project to Claude Code.

        Args:
            project: Project to dispatch

        Returns:
            True on success, False on failure
        """
        metadata = project.get("metadata", {})
        project_id = project.get("project_id", metadata.get("project_id", "unknown"))
        print(f"\n   Dispatching: {project_id}")

        # Check if already assigned
        if self.is_already_assigned(project):
            print(f"   Skipping: already assigned to {project['metadata'].get('owner')}")
            return False

        # Get the next task
        next_task = get_next_task(project.get("content", ""))

        # Build issue content
        title = build_issue_title(project_id, next_task)
        body = build_issue_body(project, self.base_path, next_task)
        labels = build_issue_labels(project)

        print(f"   Title: {title}")
        print(f"   Next task: {next_task or 'none identified'}")

        # Create the issue
        print("   Creating GitHub issue...")
        issue_url = self.create_github_issue(title, body, labels)

        if not issue_url:
            print("   Failed to create issue")
            return False

        print(f"   Issue created: {issue_url}")

        # Claim the project
        print("   Claiming project...")
        if not self.claim_project(project, issue_url):
            print("   Failed to claim project (issue was created)")
            return False

        print(f"   Successfully dispatched {project_id}")
        return True

    def run(self, max_dispatches: int = 1) -> bool:
        """
        Main dispatcher execution.

        Args:
            max_dispatches: Maximum number of projects to dispatch (default: 1)

        Returns:
            True if at least one project was dispatched, False otherwise
        """
        print("=" * 60)
        print(" AGENT HIVE DISPATCHER")
        print("=" * 60)
        print(f"Timestamp: {datetime.utcnow().isoformat()}")
        print(f"Base Path: {self.base_path}")
        print(f"Dry Run: {self.dry_run}")
        print(f"Max Dispatches: {max_dispatches}")
        print()

        # Validate environment
        print(" Validating environment...")
        if not self.dry_run and not self.validate_environment():
            print("   Environment validation failed")
            return False
        print("   Environment OK")

        # Find ready work
        print("\n Finding ready work...")
        ready_projects = self.cortex.ready_work()
        print(f"   Found {len(ready_projects)} project(s) ready for work")

        if not ready_projects:
            print("\n No work available to dispatch")
            print("=" * 60)
            return True  # No work is not an error, just nothing to do

        # Display candidates
        print("\n Candidates:")
        for proj in ready_projects:
            meta = proj.get("metadata", {})
            proj_id = meta.get('project_id', 'unknown')
            priority = meta.get('priority', 'medium')
            print(f"   - {proj_id} (priority: {priority})")

        # Dispatch projects
        dispatched = 0
        print(f"\n Dispatching (max {max_dispatches})...")

        for _ in range(max_dispatches):
            # Re-check ready work each iteration (in case state changed)
            if dispatched > 0:
                ready_projects = self.cortex.ready_work()

            project = self.select_work(ready_projects)
            if not project:
                print("   No more projects to dispatch")
                break

            if self.dispatch(project):
                dispatched += 1
            else:
                # If dispatch failed, remove from candidates and try next
                ready_projects = [
                    p for p in ready_projects
                    if p.get("path") != project.get("path")
                ]

        # Summary
        print("\n" + "=" * 60)
        print(f" DISPATCH COMPLETE: {dispatched} project(s) dispatched")
        print("=" * 60)

        return True  # Successful completion, regardless of dispatch count


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Agent Hive Dispatcher - Assign work to Claude Code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run dispatcher (dispatch 1 project)
  python -m src.agent_dispatcher

  # Dry run (no actual changes)
  python -m src.agent_dispatcher --dry-run

  # Dispatch up to 3 projects
  python -m src.agent_dispatcher --max 3

  # Specify custom base path
  python -m src.agent_dispatcher --path /path/to/hive
        """,
    )

    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Preview what would be done without making changes",
    )

    parser.add_argument(
        "--max",
        "-m",
        type=int,
        default=1,
        help="Maximum number of projects to dispatch (default: 1)",
    )

    parser.add_argument(
        "--path",
        "-p",
        type=str,
        default=None,
        help="Base path for the hive (default: current directory)",
    )

    return parser.parse_args()


def main():
    """CLI entry point for Agent Dispatcher."""
    args = parse_args()

    dispatcher = AgentDispatcher(base_path=args.path, dry_run=args.dry_run)
    success = dispatcher.run(max_dispatches=args.max)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

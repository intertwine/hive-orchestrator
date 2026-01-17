#!/usr/bin/env python3
"""
Agent Hive Agent Dispatcher

Finds ready work, assembles context, creates GitHub issues, and assigns
work to configured agents for autonomous execution.
"""

import argparse
import os
import subprocess
import sys
import time
import json
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

from src.cortex import Cortex
from src.context_assembler import (
    build_issue_title,
    build_issue_body,
    build_issue_labels,
    get_next_task,
)
from src.security import (
    safe_load_agency_md,
    safe_dump_agency_md,
    sanitize_issue_body,
    validate_max_dispatches,
)

# Load environment variables
load_dotenv()


class DispatcherError(Exception):
    """Base exception for Dispatcher-related errors."""


DEFAULT_AGENT_NAME = "claude-code"
DEFAULT_AGENT_MENTION = "@claude"


@dataclass
class DispatchProfile:
    agent_name: str
    mention: Optional[str]
    comment: Optional[str]
    labels: List[str]


class AgentDispatcher:
    """
    The Agent Dispatcher for Agent Hive.

    Responsibilities:
    - Find ready work using Cortex
    - Select highest priority project
    - Build rich context for agent assignment
    - Create GitHub issue with agent mention
    - Update AGENCY.md to claim ownership
    """

    def __init__(
        self,
        base_path: str = None,
        dry_run: bool = False,
        agent_name: str = DEFAULT_AGENT_NAME,
        agent_mention: Optional[str] = DEFAULT_AGENT_MENTION,
        extra_labels: Optional[List[str]] = None,
    ):
        """
        Initialize the Agent Dispatcher.

        Args:
            base_path: Base path for the hive (defaults to current directory)
            dry_run: If True, don't actually create issues or modify files
        """
        self.base_path = Path(base_path or os.getcwd())
        self.dry_run = dry_run
        self.agent_name = agent_name
        self.agent_mention = agent_mention
        self.extra_labels = extra_labels or []
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
            # Normalize all timestamps to naive UTC for consistent comparison
            try:
                if last_updated:
                    # Handle both datetime objects (from YAML parser) and strings
                    if isinstance(last_updated, datetime):
                        timestamp = last_updated
                    else:
                        # ISO format string timestamp
                        timestamp = datetime.fromisoformat(str(last_updated).replace("Z", "+00:00"))
                    # Normalize to naive UTC datetime for consistent comparison
                    # Convert to UTC first, then strip timezone info
                    if timestamp.tzinfo is not None:
                        timestamp = timestamp.astimezone(timezone.utc).replace(tzinfo=None)
                else:
                    timestamp = datetime.max.replace(tzinfo=None)
            except (ValueError, TypeError):
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

    def claim_project(self, project: Dict[str, Any], issue_url: str, agent_name: str) -> bool:
        """
        Claim a project by setting owner and adding issue link to AGENCY.md.

        Uses safe YAML loading to prevent deserialization attacks.

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

            # Use safe loading to prevent YAML deserialization attacks
            parsed = safe_load_agency_md(project_path)

            # Update metadata
            parsed.metadata["owner"] = agent_name
            parsed.metadata["last_updated"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            # Add agent note with issue link
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
            note = (
                f"\n- **{timestamp} - Agent Dispatcher**: "
                f"Assigned to {agent_name}. Issue: {issue_url}"
            )

            # Find or create Agent Notes section
            content = parsed.content
            if "## Agent Notes" in content:
                # Append to existing section
                content = content.replace("## Agent Notes", f"## Agent Notes{note}", 1)
            else:
                # Add new section at the end
                content += f"\n\n## Agent Notes{note}"

            # Write back using safe dump
            with open(project_path, "w", encoding="utf-8") as f:
                f.write(safe_dump_agency_md(parsed.metadata, content))

            return True

        except Exception as e:
            print(f"   ERROR claiming project: {e}")
            return False

    def create_github_issue(self, title: str, body: str, labels: List[str]) -> Optional[str]:
        """
        Create a GitHub issue using the gh CLI.

        Sanitizes title and body to prevent injection attacks via issue content.

        Args:
            title: Issue title
            body: Issue body (markdown)
            labels: List of labels to apply

        Returns:
            Issue URL on success, None on failure
        """
        # Sanitize title (truncate and strip dangerous patterns)
        safe_title = title[:200] if title else "Agent Hive Task"

        # Sanitize body to prevent injection attacks
        safe_body = sanitize_issue_body(body)

        if self.dry_run:
            print(f"   [DRY RUN] Would create issue: {safe_title}")
            print(f"   [DRY RUN] Labels: {', '.join(labels)}")
            return "https://github.com/example/repo/issues/999"

        try:
            # Build gh command with sanitized inputs
            cmd = ["gh", "issue", "create", "--title", safe_title, "--body", safe_body]

            # Add labels
            for label in labels:
                # Sanitize label names (alphanumeric, dashes, colons only)
                safe_label = "".join(c for c in label if c.isalnum() or c in "-:_")
                if safe_label:
                    cmd.extend(["--label", safe_label])

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
                    cmd = ["gh", "issue", "create", "--title", safe_title, "--body", safe_body]
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

    def add_agent_comment(self, issue_url: str, comment: Optional[str]) -> bool:
        """
        Add a comment to the issue to trigger the configured agent.

        GitHub API-created issues don't trigger notifications from @mentions
        in the initial body. A separate comment is needed to invoke the agent.

        Args:
            issue_url: URL of the GitHub issue

        Returns:
            True on success, False on failure
        """
        if not comment:
            return True

        if self.dry_run:
            print("   [DRY RUN] Would add agent comment to trigger assignment")
            return True

        try:
            # Extract issue number from URL
            # URL format: https://github.com/owner/repo/issues/123
            issue_number = issue_url.rstrip("/").split("/")[-1]

            cmd = ["gh", "issue", "comment", issue_number, "--body", comment]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            if result.returncode != 0:
                print(f"   Warning: Failed to add agent comment: {result.stderr}")
                return False

            return True

        except subprocess.TimeoutExpired:
            print("   Warning: gh comment command timed out")
            return False
        except Exception as e:
            print(f"   Warning: Failed to add agent comment: {e}")
            return False

    def resolve_dispatch_profile(self, project: Dict[str, Any]) -> DispatchProfile:
        metadata = project.get("metadata", {})
        dispatch = metadata.get("dispatch", {}) if isinstance(metadata.get("dispatch"), dict) else {}

        agent_name = dispatch.get("agent_name") or self.agent_name

        if "mention" in dispatch:
            mention = dispatch.get("mention")
        else:
            mention = self.agent_mention

        if mention:
            mention = mention.strip()
            if mention and not mention.startswith("@"):
                mention = f"@{mention}"
        else:
            mention = None

        comment = dispatch.get("comment")
        if comment:
            comment = comment.strip()
        elif mention:
            comment = f"{mention} Please work on this issue."
        else:
            comment = None

        labels = list(self.extra_labels)
        dispatch_labels = dispatch.get("labels", [])
        if isinstance(dispatch_labels, list):
            labels.extend([str(label) for label in dispatch_labels])
        elif isinstance(dispatch_labels, str):
            labels.append(dispatch_labels)

        return DispatchProfile(
            agent_name=agent_name,
            mention=mention,
            comment=comment,
            labels=labels,
        )

    def dispatch(self, project: Dict[str, Any]) -> bool:
        """
        Dispatch a single project to the configured agent.

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

        dispatch_profile = self.resolve_dispatch_profile(project)

        # Get the next task
        next_task = get_next_task(project.get("content", ""))

        # Build issue content
        title = build_issue_title(project_id, next_task)
        body = build_issue_body(
            project,
            self.base_path,
            next_task,
            agent_name=dispatch_profile.agent_name,
            agent_mention=dispatch_profile.mention,
        )
        labels = build_issue_labels(project, extra_labels=dispatch_profile.labels)

        print(f"   Title: {title}")
        print(f"   Next task: {next_task or 'none identified'}")

        # Create the issue
        print("   Creating GitHub issue...")
        issue_url = self.create_github_issue(title, body, labels)

        if not issue_url:
            print("   Failed to create issue")
            return False

        print(f"   Issue created: {issue_url}")

        # Add a comment to trigger agent assignment
        # GitHub doesn't trigger notifications from @mentions in the initial body
        if dispatch_profile.comment:
            print("   Adding agent comment to trigger assignment...")
            if not self.add_agent_comment(issue_url, dispatch_profile.comment):
                print("   Warning: Could not add agent comment, but issue was created")

        # Claim the project
        print("   Claiming project...")
        if not self.claim_project(project, issue_url, dispatch_profile.agent_name):
            print("   Failed to claim project (issue was created)")
            return False

        print(f"   Successfully dispatched {project_id}")
        return True

    def run_cycle(self, max_dispatches: int = 1) -> int:
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
        print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
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
            return 0  # No work is not an error, just nothing to do

        # Display candidates
        print("\n Candidates:")
        for proj in ready_projects:
            meta = proj.get("metadata", {})
            proj_id = meta.get("project_id", "unknown")
            priority = meta.get("priority", "medium")
            print(f"   - {proj_id} (priority: {priority})")

        # Dispatch projects
        dispatched = 0
        attempted_paths = set()  # Track projects already attempted in this run
        print(f"\n Dispatching (max {max_dispatches})...")

        for _ in range(max_dispatches):
            # Re-check ready work each iteration (in case state changed)
            if dispatched > 0:
                ready_projects = self.cortex.ready_work()

            # Filter out already-attempted projects
            available_projects = [p for p in ready_projects if p.get("path") not in attempted_paths]

            project = self.select_work(available_projects)
            if not project:
                print("   No more projects to dispatch")
                break

            # Mark as attempted before dispatching
            attempted_paths.add(project.get("path"))

            if self.dispatch(project):
                dispatched += 1

        # Summary
        print("\n" + "=" * 60)
        print(f" DISPATCH COMPLETE: {dispatched} project(s) dispatched")
        print("=" * 60)

        return dispatched

    def run(self, max_dispatches: int = 1) -> bool:
        """Run a single dispatcher cycle."""
        self.run_cycle(max_dispatches=max_dispatches)
        return True

    def run_loop(
        self,
        max_dispatches: int = 1,
        style: str = "loom",
        sleep_seconds: int = 30,
        max_sleep_seconds: int = 300,
        max_cycles: Optional[int] = None,
        heartbeat_path: Optional[Path] = None,
    ) -> bool:
        """Run dispatcher in a continuous YOLO loop."""
        print("=" * 60)
        print(" AGENT HIVE YOLO LOOP")
        print("=" * 60)
        print(f"Loop style: {style}")
        print(f"Base sleep: {sleep_seconds}s")
        if style == "loom":
            print(f"Max sleep: {max_sleep_seconds}s")
        if max_cycles:
            print(f"Max cycles: {max_cycles}")
        print()

        cycle = 0
        current_sleep = sleep_seconds

        while True:
            cycle += 1
            print(f"\n--- YOLO cycle {cycle} ---")
            dispatched = self.run_cycle(max_dispatches=max_dispatches)

            if heartbeat_path:
                heartbeat_payload = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "cycle": cycle,
                    "dispatched": dispatched,
                    "style": style,
                    "sleep_seconds": sleep_seconds,
                }
                try:
                    heartbeat_path.parent.mkdir(parents=True, exist_ok=True)
                    heartbeat_path.write_text(json.dumps(heartbeat_payload), encoding="utf-8")
                except OSError as exc:
                    print(f"Warning: Failed to write heartbeat file: {exc}")

            if max_cycles and cycle >= max_cycles:
                print("Reached max cycles. Exiting loop.")
                break

            if style == "loom":
                if dispatched == 0:
                    current_sleep = min(current_sleep * 2, max_sleep_seconds)
                else:
                    current_sleep = sleep_seconds
            else:
                current_sleep = sleep_seconds

            print(f"\nSleeping {current_sleep}s before next cycle...")
            time.sleep(current_sleep)

        return True


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Agent Hive Dispatcher - Assign work to configured agents",
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

  # Run a continuous YOLO loop (loom style)
  python -m src.agent_dispatcher --yolo-loop --yolo-style loom

  # Run an aggressive YOLO loop (ralph wiggum style)
  python -m src.agent_dispatcher --yolo-loop --yolo-style ralph-wiggum --loop-sleep 5
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

    parser.add_argument(
        "--agent-name",
        type=str,
        default=DEFAULT_AGENT_NAME,
        help="Agent name to claim projects with (default: claude-code)",
    )

    parser.add_argument(
        "--agent-mention",
        type=str,
        default=DEFAULT_AGENT_MENTION,
        help="GitHub mention to trigger agent notifications (default: @claude). Use 'none' to disable.",
    )

    parser.add_argument(
        "--extra-label",
        action="append",
        default=[],
        help="Extra label to add to dispatched issues (repeatable)",
    )

    parser.add_argument(
        "--yolo-loop",
        action="store_true",
        help="Run the dispatcher continuously in a YOLO loop (opt-in)",
    )

    parser.add_argument(
        "--yolo-style",
        choices=["loom", "ralph-wiggum"],
        default="loom",
        help="YOLO loop style: loom (backoff) or ralph-wiggum (aggressive)",
    )

    parser.add_argument(
        "--loop-sleep",
        type=int,
        default=None,
        help="Base sleep time between YOLO cycles in seconds",
    )

    parser.add_argument(
        "--loop-max-sleep",
        type=int,
        default=300,
        help="Maximum sleep time for loom backoff in seconds",
    )

    parser.add_argument(
        "--loop-max-cycles",
        type=int,
        default=None,
        help="Maximum number of YOLO cycles before exiting (default: infinite)",
    )

    parser.add_argument(
        "--loop-heartbeat",
        type=str,
        default=None,
        help="Optional path to write a heartbeat JSON file after each loop cycle",
    )

    return parser.parse_args()


def main():
    """CLI entry point for Agent Dispatcher."""
    args = parse_args()

    # Validate max_dispatches to prevent DoS via unbounded dispatch requests
    try:
        max_dispatches = validate_max_dispatches(args.max)
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    agent_mention = args.agent_mention
    if agent_mention and agent_mention.strip().lower() in {"none", "null", "off"}:
        agent_mention = None

    loop_sleep = args.loop_sleep
    if loop_sleep is None:
        loop_sleep = 5 if args.yolo_style == "ralph-wiggum" else 30

    if args.loop_max_cycles is not None and args.loop_max_cycles < 1:
        print("ERROR: loop-max-cycles must be >= 1")
        sys.exit(1)

    dispatcher = AgentDispatcher(
        base_path=args.path,
        dry_run=args.dry_run,
        agent_name=args.agent_name,
        agent_mention=agent_mention,
        extra_labels=args.extra_label,
    )

    if args.yolo_loop:
        heartbeat_path = Path(args.loop_heartbeat) if args.loop_heartbeat else None
        success = dispatcher.run_loop(
            max_dispatches=max_dispatches,
            style=args.yolo_style,
            sleep_seconds=loop_sleep,
            max_sleep_seconds=args.loop_max_sleep,
            max_cycles=args.loop_max_cycles,
            heartbeat_path=heartbeat_path,
        )
    else:
        success = dispatcher.run(max_dispatches=max_dispatches)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

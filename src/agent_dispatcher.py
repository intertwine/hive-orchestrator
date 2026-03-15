#!/usr/bin/env python3
"""
Agent Hive Agent Dispatcher

Optional manual compatibility command that turns canonical Hive v2 ready
tasks into GitHub issues for Claude Code.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

from src.hive.control import recommend_next_task
from src.context_assembler import (
    build_issue_body,
    build_issue_labels,
    build_issue_title,
)
from src.hive.projections.agency_md import sync_agency_md
from src.hive.projections.agents_md import sync_agents_md
from src.hive.projections.global_md import sync_global_md
from src.hive.scheduler.query import ready_tasks
from src.hive.store.cache import rebuild_cache
from src.hive.store.task_files import get_task, save_task
from src.security import sanitize_issue_body, validate_max_dispatches

load_dotenv()


class DispatcherError(Exception):
    """Base exception for Dispatcher-related errors."""


def _parse_timestamp(value: object) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return datetime.max.replace(tzinfo=None)
    return datetime.max.replace(tzinfo=None)


def _candidate_identifier(candidate: dict[str, Any]) -> str:
    metadata = candidate.get("metadata", {})
    return str(
        candidate.get("task_id")
        or candidate.get("id")
        or candidate.get("project_id")
        or metadata.get("project_id", "unknown")
    )


def _candidate_priority(candidate: dict[str, Any]) -> int:
    priority = candidate.get("priority", candidate.get("metadata", {}).get("priority", 2))
    if isinstance(priority, int):
        return priority
    mapping = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    if isinstance(priority, str):
        return mapping.get(priority.lower(), 2)
    return 2


def _candidate_timestamp(candidate: dict[str, Any]) -> datetime:
    metadata = candidate.get("metadata", {})
    for key in ("created_at", "updated_at", "last_updated"):
        if key in candidate:
            return _parse_timestamp(candidate[key])
        if key in metadata:
            return _parse_timestamp(metadata[key])
    return datetime.max.replace(tzinfo=None)


class AgentDispatcher:
    """
    Optional manual dispatcher for Agent Hive.

    Responsibilities:
    - Find ready canonical tasks
    - Select the highest priority task
    - Build rich v2 context for a GitHub issue
    - Claim the canonical task for Claude Code
    """

    AGENT_NAME = "claude-code"
    CLAIM_TTL_MINUTES = 120

    def __init__(self, base_path: str | None = None, dry_run: bool = False):
        self.base_path = Path(base_path or os.getcwd())
        self.dry_run = dry_run

    def validate_environment(self) -> bool:
        """Validate that required tools are available."""
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

    def ready_work(self) -> list[dict[str, Any]]:
        """Return canonical ready tasks."""
        return ready_tasks(self.base_path)

    def select_work(
        self, projects: Optional[list[dict[str, Any]]] = None
    ) -> Optional[dict[str, Any]]:
        """
        Select the highest priority ready task.

        Priority ordering:
        1. Priority level (critical > high > medium > low)
        2. Age (oldest created/updated timestamp first)
        3. Title / identifier for stable ordering
        """
        if projects is None:
            recommendation = recommend_next_task(self.base_path, emit_decision_event=False)
            return recommendation["task"] if recommendation else None
        candidates = projects if projects is not None else self.ready_work()
        if not candidates:
            return None

        return sorted(
            candidates,
            key=lambda item: (
                _candidate_priority(item),
                _candidate_timestamp(item),
                str(item.get("title", "")).lower(),
                _candidate_identifier(item),
            ),
        )[0]

    def is_already_assigned(self, project: dict[str, Any]) -> bool:
        """Check whether a task is actively assigned."""
        metadata = project.get("metadata", {})
        owner = project.get("owner", metadata.get("owner"))
        status = project.get("status", metadata.get("status"))
        claimed_until = project.get("claimed_until", metadata.get("claimed_until"))

        if status == "in_progress":
            return True
        if status == "claimed" and owner and claimed_until:
            try:
                expires_at = datetime.fromisoformat(claimed_until.replace("Z", "+00:00"))
            except ValueError:
                return bool(owner)
            return expires_at > datetime.now(timezone.utc)
        return False

    def _sync_views(self) -> None:
        sync_global_md(self.base_path)
        sync_agency_md(self.base_path)
        sync_agents_md(self.base_path)
        rebuild_cache(self.base_path)

    def claim_project(self, project: dict[str, Any], issue_url: str) -> bool:
        """
        Claim a canonical task and record the created GitHub issue URL.

        The method name is preserved for compatibility with existing callers.
        """
        if self.dry_run:
            print(f"   [DRY RUN] Would claim task and record issue link: {issue_url}")
            return True

        task_id = project.get("task_id") or project.get("id")
        if not task_id:
            print("   ERROR claiming task: no canonical task id available")
            return False

        try:
            task = get_task(self.base_path, str(task_id))
            if self.is_already_assigned(
                {
                    "owner": task.owner,
                    "status": task.status,
                    "claimed_until": task.claimed_until,
                }
            ):
                print(f"   Task already assigned: {task.id}")
                return False

            now = datetime.now(timezone.utc)
            expires_at = now + timedelta(minutes=self.CLAIM_TTL_MINUTES)
            task.owner = self.AGENT_NAME
            task.claimed_until = expires_at.isoformat().replace("+00:00", "Z")
            if task.status in {"proposed", "ready"}:
                task.status = "claimed"
            task.metadata["dispatch_issue_url"] = issue_url

            note = (
                f"- {now.strftime('%Y-%m-%d %H:%M')} - Agent Dispatcher: "
                f"Assigned to Claude Code. Issue: {issue_url}"
            )
            history = task.history_md.strip()
            task.history_md = f"{history}\n{note}".strip() if history else note

            save_task(self.base_path, task)

            try:
                self._sync_views()
            except Exception as exc:  # pragma: no cover - best-effort sync
                print(f"   Warning: task claimed but projection sync failed: {exc}")

            return True

        except Exception as exc:
            print(f"   ERROR claiming task: {exc}")
            return False

    def create_github_issue(self, title: str, body: str, labels: list[str]) -> Optional[str]:
        """Create a GitHub issue using the gh CLI."""
        safe_title = title[:200] if title else "Agent Hive Task"
        safe_body = sanitize_issue_body(body)

        if self.dry_run:
            print(f"   [DRY RUN] Would create issue: {safe_title}")
            print(f"   [DRY RUN] Labels: {', '.join(labels)}")
            return "https://github.com/example/repo/issues/999"

        try:
            cmd = ["gh", "issue", "create", "--title", safe_title, "--body", safe_body]
            for label in labels:
                safe_label = "".join(char for char in label if char.isalnum() or char in "-:_")
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
                if "label" in result.stderr.lower():
                    print("   Warning: Label issue, retrying without labels...")
                    result = subprocess.run(
                        ["gh", "issue", "create", "--title", safe_title, "--body", safe_body],
                        capture_output=True,
                        text=True,
                        timeout=60,
                        check=False,
                    )

                if result.returncode != 0:
                    print(f"   ERROR creating issue: {result.stderr}")
                    return None

            return result.stdout.strip()

        except subprocess.TimeoutExpired:
            print("   ERROR: gh command timed out")
            return None
        except Exception as exc:
            print(f"   ERROR creating issue: {exc}")
            return None

    def add_claude_comment(self, issue_url: str) -> bool:
        """Add a comment to trigger Claude Code."""
        if self.dry_run:
            print("   [DRY RUN] Would add @claude comment to trigger assignment")
            return True

        try:
            issue_number = issue_url.rstrip("/").split("/")[-1]
            result = subprocess.run(
                [
                    "gh",
                    "issue",
                    "comment",
                    issue_number,
                    "--body",
                    "@claude Please work on this issue.",
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if result.returncode != 0:
                print(f"   Warning: Failed to add Claude comment: {result.stderr}")
                return False
            return True
        except subprocess.TimeoutExpired:
            print("   Warning: gh comment command timed out")
            return False
        except Exception as exc:
            print(f"   Warning: Failed to add Claude comment: {exc}")
            return False

    def dispatch(self, project: dict[str, Any]) -> bool:
        """Dispatch a single canonical task to Claude Code."""
        project_id = project.get("project_id", "unknown")
        task_id = project.get("task_id") or project.get("id", "unknown")
        task_title = project.get("task_title") or project.get("title")

        print(f"\n   Dispatching: {project_id} / {task_id}")

        if self.is_already_assigned(project):
            print(f"   Skipping: already assigned to {project.get('owner')}")
            return False

        title = build_issue_title(project_id, task_title)
        body = build_issue_body(project, self.base_path, task_title)
        labels = build_issue_labels(project)

        print(f"   Title: {title}")
        print(f"   Task: {task_title or 'none identified'}")

        print("   Creating GitHub issue...")
        issue_url = self.create_github_issue(title, body, labels)
        if not issue_url:
            print("   Failed to create issue")
            return False

        print(f"   Issue created: {issue_url}")
        print("   Adding @claude comment to trigger assignment...")
        if not self.add_claude_comment(issue_url):
            print("   Warning: Could not add Claude comment, but issue was created")

        print("   Claiming task...")
        if not self.claim_project(project, issue_url):
            # TODO(hive-v2): If issue creation succeeds but the subsequent task claim fails,
            # the task can be re-dispatched on a later run and create a duplicate issue.
            # Fixing that race likely needs a durable "dispatch started" marker or
            # claim-before-issue flow rather than a local retry tweak.
            print("   Failed to claim task (issue was created)")
            return False

        print(f"   Successfully dispatched {project_id} / {task_id}")
        return True

    def run(self, max_dispatches: int = 1) -> bool:
        """Run the dispatcher."""
        print("=" * 60)
        print(" AGENT HIVE DISPATCHER")
        print("=" * 60)
        print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
        print(f"Base Path: {self.base_path}")
        print(f"Dry Run: {self.dry_run}")
        print(f"Max Dispatches: {max_dispatches}")
        print()

        print(" Validating environment...")
        if not self.dry_run and not self.validate_environment():
            print("   Environment validation failed")
            return False
        print("   Environment OK")

        print("\n Finding ready work...")
        ready = self.ready_work()
        print(f"   Found {len(ready)} task(s) ready for work")

        if not ready:
            print("\n No work available to dispatch")
            print("=" * 60)
            return True

        print("\n Candidates:")
        for candidate in ready:
            print(
                f"   - {candidate['project_id']} / {candidate['id']} "
                f"(p{candidate['priority']}: {candidate['title']})"
            )

        dispatched = 0
        attempted_ids: set[str] = set()
        print(f"\n Dispatching (max {max_dispatches})...")

        for _ in range(max_dispatches):
            available = [
                item
                for item in self.ready_work()
                if _candidate_identifier(item) not in attempted_ids
            ]
            project = self.select_work(available)
            if not project:
                print("   No more tasks to dispatch")
                break

            attempted_ids.add(_candidate_identifier(project))
            if self.dispatch(project):
                dispatched += 1

        print("\n" + "=" * 60)
        print(f" DISPATCH COMPLETE: {dispatched} task(s) dispatched")
        print("=" * 60)
        return True


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Agent Hive Dispatcher - Manually assign ready Hive v2 tasks to Claude Code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run dispatcher (dispatch 1 task)
  python -m src.agent_dispatcher

  # Dry run (no actual changes)
  python -m src.agent_dispatcher --dry-run

  # Dispatch up to 3 tasks
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
        help="Maximum number of tasks to dispatch (default: 1)",
    )
    parser.add_argument(
        "--path",
        "-p",
        type=str,
        default=None,
        help="Base path for the hive (default: current directory)",
    )
    return parser.parse_args()


def main() -> None:
    """CLI entry point for Agent Dispatcher."""
    args = parse_args()
    try:
        max_dispatches = validate_max_dispatches(args.max)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    dispatcher = AgentDispatcher(base_path=args.path, dry_run=args.dry_run)
    success = dispatcher.run(max_dispatches=max_dispatches)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

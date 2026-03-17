#!/usr/bin/env python3
"""Prune stale automation branches from the repository."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

MERGED_PREFIXES = ("claude/", "copilot/", "codex/")
STALE_PREFIXES = ("claude/", "copilot/")


@dataclass(frozen=True)
class BranchState:
    """Branch metadata used to decide whether a remote branch is safe to delete."""

    name: str
    protected: bool
    has_open_pr: bool
    merged_into_default: bool
    commit_date: datetime


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=True, text=True, capture_output=True)


def _run_json(args: list[str]) -> object:
    result = _run(args)
    return json.loads(result.stdout)


def _matches_prefix(name: str, prefixes: Iterable[str]) -> bool:
    return any(name.startswith(prefix) for prefix in prefixes)


def decide_branch_action(
    branch: BranchState,
    *,
    default_branch: str,
    now: datetime,
    stale_after: timedelta,
) -> str | None:
    """Return the cleanup reason for a branch, or None when it should be kept."""
    if branch.name == default_branch or branch.protected or branch.has_open_pr:
        return None
    if branch.merged_into_default and _matches_prefix(branch.name, MERGED_PREFIXES):
        return "merged"
    if _matches_prefix(branch.name, STALE_PREFIXES) and now - branch.commit_date >= stale_after:
        return "stale"
    return None


def _list_branches(repo: str) -> list[dict[str, object]]:
    payload = _run_json(["gh", "api", f"repos/{repo}/branches", "--paginate"])
    return list(payload)


def _list_open_pr_heads(repo: str) -> set[str]:
    payload = _run_json(["gh", "api", f"repos/{repo}/pulls?state=open&per_page=100", "--paginate"])
    heads: set[str] = set()
    for pr in payload:
        head = pr.get("head") or {}
        head_repo = head.get("repo") or {}
        if head_repo.get("full_name") == repo and head.get("ref"):
            heads.add(str(head["ref"]))
    return heads


def _fetch_remote_branches() -> None:
    _run(["git", "fetch", "origin", "+refs/heads/*:refs/remotes/origin/*", "--prune"])


def _is_merged(branch: str, default_branch: str) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", f"origin/{branch}", f"origin/{default_branch}"],
        check=False,
        text=True,
        capture_output=True,
    )
    return result.returncode == 0


def _commit_date(branch: str) -> datetime:
    result = _run(["git", "log", "-1", "--format=%cI", f"origin/{branch}"])
    return datetime.fromisoformat(result.stdout.strip())


def _delete_branch(branch: str) -> None:
    _run(["git", "push", "origin", "--delete", branch])


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line parser for branch hygiene runs."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        required=True,
        help="owner/name of the GitHub repository",
    )
    parser.add_argument(
        "--default-branch",
        default="main",
        help="default branch name",
    )
    parser.add_argument(
        "--stale-days",
        type=int,
        default=7,
        help="age threshold for stale bot branches",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report candidates without deleting them",
    )
    return parser


def main() -> int:
    """Run the branch hygiene flow and return a process exit code."""

    parser = build_parser()
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    stale_after = timedelta(days=args.stale_days)

    _fetch_remote_branches()
    branches = _list_branches(args.repo)
    open_pr_heads = _list_open_pr_heads(args.repo)

    deleted = 0
    kept = 0
    for raw_branch in branches:
        branch_name = str(raw_branch["name"])
        state = BranchState(
            name=branch_name,
            protected=bool(raw_branch.get("protected", False)),
            has_open_pr=branch_name in open_pr_heads,
            merged_into_default=_is_merged(branch_name, args.default_branch),
            commit_date=_commit_date(branch_name),
        )
        reason = decide_branch_action(
            state,
            default_branch=args.default_branch,
            now=now,
            stale_after=stale_after,
        )
        if reason is None:
            kept += 1
            continue

        age_days = (now - state.commit_date).days
        action = "DRY-RUN would delete" if args.dry_run else "Deleting"
        print(
            f"{action} {branch_name} "
            f"({reason}, age={age_days}d)"
        )
        if not args.dry_run:
            _delete_branch(branch_name)
        deleted += 1

    print(
        f"Branch hygiene complete: deleted={deleted}, kept={kept}, "
        f"dry_run={'true' if args.dry_run else 'false'}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

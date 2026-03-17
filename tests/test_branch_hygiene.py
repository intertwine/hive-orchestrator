"""Tests for the remote branch hygiene policy."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from scripts.prune_remote_branches import BranchState, decide_branch_action


def _branch(**overrides: object) -> BranchState:
    now = datetime(2026, 3, 17, tzinfo=timezone.utc)
    defaults = {
        "name": "claude/pr-1",
        "protected": False,
        "has_open_pr": False,
        "merged_into_default": False,
        "commit_date": now - timedelta(days=10),
    }
    defaults.update(overrides)
    return BranchState(**defaults)


def test_keep_default_branch() -> None:
    """The default branch should never be considered for deletion."""

    now = datetime(2026, 3, 17, tzinfo=timezone.utc)
    branch = _branch(name="main", merged_into_default=True)
    assert (
        decide_branch_action(
            branch,
            default_branch="main",
            now=now,
            stale_after=timedelta(days=7),
        )
        is None
    )


def test_keep_open_pull_request_branch() -> None:
    """Branches with an active pull request stay in place."""

    now = datetime(2026, 3, 17, tzinfo=timezone.utc)
    branch = _branch(has_open_pr=True, merged_into_default=True)
    assert (
        decide_branch_action(
            branch,
            default_branch="main",
            now=now,
            stale_after=timedelta(days=7),
        )
        is None
    )


def test_delete_merged_codex_branch() -> None:
    """Merged Codex work branches should be cleaned up automatically."""

    now = datetime(2026, 3, 17, tzinfo=timezone.utc)
    branch = _branch(
        name="codex/feature",
        merged_into_default=True,
        commit_date=now - timedelta(days=1),
    )
    assert (
        decide_branch_action(
            branch,
            default_branch="main",
            now=now,
            stale_after=timedelta(days=7),
        )
        == "merged"
    )


def test_delete_stale_claude_branch_without_pull_request() -> None:
    """Old Claude review branches with no open PR can be safely pruned."""

    now = datetime(2026, 3, 17, tzinfo=timezone.utc)
    branch = _branch(
        name="claude/pr-1",
        merged_into_default=False,
        commit_date=now - timedelta(days=8),
    )
    assert (
        decide_branch_action(
            branch,
            default_branch="main",
            now=now,
            stale_after=timedelta(days=7),
        )
        == "stale"
    )


def test_keep_recent_claude_branch() -> None:
    """Recent Claude branches should stay available for review follow-ups."""

    now = datetime(2026, 3, 17, tzinfo=timezone.utc)
    branch = _branch(
        name="claude/pr-1",
        merged_into_default=False,
        commit_date=now - timedelta(days=2),
    )
    assert (
        decide_branch_action(
            branch,
            default_branch="main",
            now=now,
            stale_after=timedelta(days=7),
        )
        is None
    )


def test_keep_unmerged_codex_branch_even_when_old() -> None:
    """Unmerged Codex branches should not be deleted just because they are old."""

    now = datetime(2026, 3, 17, tzinfo=timezone.utc)
    branch = _branch(
        name="codex/feature",
        merged_into_default=False,
        commit_date=now - timedelta(days=30),
    )
    assert (
        decide_branch_action(
            branch,
            default_branch="main",
            now=now,
            stale_after=timedelta(days=7),
        )
        is None
    )

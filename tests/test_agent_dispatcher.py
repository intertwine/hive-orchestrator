"""Tests for the Agent Dispatcher module."""

# pylint: disable=unused-argument,import-error,wrong-import-position

import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agent_dispatcher import AgentDispatcher
from src.hive.migrate import migrate_v1_to_v2
from src.hive.scheduler.query import ready_tasks
from src.hive.store.task_files import get_task


def _first_ready_task(base_path: str) -> dict:
    return ready_tasks(base_path, project_id="test-project", limit=1)[0]


class TestAgentDispatcherInitialization:
    """Tests for AgentDispatcher initialization."""

    def test_default_initialization(self):
        """Default initialization uses the current working directory."""
        dispatcher = AgentDispatcher()
        assert dispatcher.base_path == Path.cwd()
        assert dispatcher.dry_run is False

    def test_custom_path(self, temp_hive_dir):
        """Custom base paths are preserved."""
        dispatcher = AgentDispatcher(base_path=temp_hive_dir)
        assert dispatcher.base_path == Path(temp_hive_dir)

    def test_dry_run_mode(self, temp_hive_dir):
        """Dry run mode is stored on the instance."""
        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=True)
        assert dispatcher.dry_run is True


class TestReadyWorkAndSelection:
    """Tests for ready-work discovery and selection."""

    def test_ready_work_returns_canonical_queue(self, temp_hive_dir, temp_project):
        """ready_work() proxies the canonical Hive v2 ready-task queue."""
        migrate_v1_to_v2(temp_hive_dir)
        dispatcher = AgentDispatcher(base_path=temp_hive_dir)

        items = dispatcher.ready_work()

        assert items
        assert items[0]["project_id"] == "test-project"
        assert items[0]["id"].startswith("task_")

    def test_returns_none_when_no_projects(self, temp_hive_dir):
        """select_work returns None for an empty candidate list."""
        dispatcher = AgentDispatcher(base_path=temp_hive_dir)
        assert dispatcher.select_work([]) is None

    def test_selects_highest_priority_then_oldest(self, temp_hive_dir):
        """Selection prefers priority, then age, then stable ordering."""
        dispatcher = AgentDispatcher(base_path=temp_hive_dir)
        candidates = [
            {
                "id": "task_new_low",
                "project_id": "demo",
                "title": "Low priority",
                "priority": 3,
                "created_at": "2025-01-01T00:00:00Z",
            },
            {
                "id": "task_new_high",
                "project_id": "demo",
                "title": "New high",
                "priority": 1,
                "created_at": "2025-01-02T00:00:00Z",
            },
            {
                "id": "task_old_high",
                "project_id": "demo",
                "title": "Old high",
                "priority": 1,
                "created_at": "2025-01-01T00:00:00Z",
            },
        ]

        selected = dispatcher.select_work(candidates)

        assert selected["id"] == "task_old_high"


class TestAssignmentState:
    """Tests for active-claim detection."""

    def test_returns_true_when_active_claim_exists(self, temp_hive_dir):
        """Active claimed tasks are treated as already assigned."""
        dispatcher = AgentDispatcher(base_path=temp_hive_dir)
        candidate = {
            "owner": "some-agent",
            "status": "claimed",
            "claimed_until": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
        }

        assert dispatcher.is_already_assigned(candidate) is True

    def test_returns_false_when_claim_is_expired(self, temp_hive_dir):
        """Expired claims do not block dispatch."""
        dispatcher = AgentDispatcher(base_path=temp_hive_dir)
        candidate = {
            "owner": "some-agent",
            "status": "claimed",
            "claimed_until": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
        }

        assert dispatcher.is_already_assigned(candidate) is False

    def test_returns_true_for_in_progress(self, temp_hive_dir):
        """In-progress tasks are always treated as already assigned."""
        dispatcher = AgentDispatcher(base_path=temp_hive_dir)
        candidate = {"owner": "some-agent", "status": "in_progress"}

        assert dispatcher.is_already_assigned(candidate) is True


class TestClaimProject:
    """Tests for canonical task claiming."""

    def test_dry_run_does_not_modify_task(self, temp_hive_dir, temp_project):
        """Dry-run claims leave the canonical task untouched."""
        migrate_v1_to_v2(temp_hive_dir)
        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=True)
        candidate = _first_ready_task(temp_hive_dir)
        task_path = Path(temp_hive_dir) / ".hive" / "tasks" / f"{candidate['id']}.md"
        before = task_path.read_text(encoding="utf-8")

        result = dispatcher.claim_project(candidate, "https://github.com/test/issue/1")

        after = task_path.read_text(encoding="utf-8")
        assert result is True
        assert before == after

    def test_claims_task_and_records_issue_url(self, temp_hive_dir, temp_project):
        """Successful claims update the canonical task state and metadata."""
        migrate_v1_to_v2(temp_hive_dir)
        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=False)
        candidate = _first_ready_task(temp_hive_dir)

        with patch.object(dispatcher, "_sync_views"):
            result = dispatcher.claim_project(candidate, "https://github.com/test/issue/123")

        claimed = get_task(temp_hive_dir, candidate["id"])
        assert result is True
        assert claimed.owner == "claude-code"
        assert claimed.status == "claimed"
        assert claimed.metadata["dispatch_issue_url"] == "https://github.com/test/issue/123"
        assert "https://github.com/test/issue/123" in claimed.history_md

    def test_returns_false_when_task_is_already_claimed(self, temp_hive_dir, temp_project):
        """Concurrent active claims are rejected."""
        migrate_v1_to_v2(temp_hive_dir)
        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=False)
        candidate = _first_ready_task(temp_hive_dir)
        task = get_task(temp_hive_dir, candidate["id"])
        task.owner = "another-agent"
        task.status = "claimed"
        task.claimed_until = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
        from src.hive.store.task_files import (
            save_task,
        )  # local import to keep test dependency small

        save_task(temp_hive_dir, task)

        result = dispatcher.claim_project(candidate, "https://github.com/test/issue/1")

        assert result is False


class TestCreateGitHubIssue:
    """Tests for create_github_issue."""

    def test_dry_run_returns_fake_url(self, temp_hive_dir):
        """Dry-run issue creation returns a placeholder URL."""
        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=True)

        result = dispatcher.create_github_issue("Test Title", "Test Body", ["label1"])

        assert result is not None
        assert "github.com" in result

    @patch("subprocess.run")
    def test_calls_gh_cli(self, mock_run, temp_hive_dir):
        """Successful issue creation shells out to gh."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="https://github.com/owner/repo/issues/1",
            stderr="",
        )
        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=False)

        result = dispatcher.create_github_issue("Test Title", "Test Body", ["label1", "label2"])

        call_args = mock_run.call_args[0][0]
        assert "gh" in call_args
        assert "issue" in call_args
        assert "create" in call_args
        assert result == "https://github.com/owner/repo/issues/1"

    @patch("subprocess.run")
    def test_retries_without_labels_on_label_error(self, mock_run, temp_hive_dir):
        """Missing labels trigger a retry without labels."""
        mock_run.side_effect = [
            MagicMock(returncode=1, stdout="", stderr="label missing"),
            MagicMock(
                returncode=0,
                stdout="https://github.com/owner/repo/issues/1",
                stderr="",
            ),
        ]
        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=False)

        result = dispatcher.create_github_issue("Test Title", "Test Body", ["missing-label"])

        assert mock_run.call_count == 2
        second_call_args = mock_run.call_args_list[1][0][0]
        assert "--label" not in second_call_args
        assert result == "https://github.com/owner/repo/issues/1"


class TestAddClaudeComment:
    """Tests for add_claude_comment."""

    def test_dry_run_returns_true(self, temp_hive_dir):
        """Dry-run comments short-circuit cleanly."""
        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=True)

        assert dispatcher.add_claude_comment("https://github.com/owner/repo/issues/123") is True

    @patch("subprocess.run")
    def test_successful_comment_addition(self, mock_run, temp_hive_dir):
        """Successful comment creation shells out to gh with the issue number."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=False)

        result = dispatcher.add_claude_comment("https://github.com/owner/repo/issues/42")

        call_args = mock_run.call_args[0][0]
        assert result is True
        assert "42" in call_args
        assert "@claude" in call_args[call_args.index("--body") + 1]

    @patch("subprocess.run")
    def test_handles_gh_cli_failure(self, mock_run, temp_hive_dir):
        """Comment failures are surfaced as False."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="permission denied")
        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=False)

        assert dispatcher.add_claude_comment("https://github.com/owner/repo/issues/123") is False


class TestDispatch:
    """Tests for dispatch."""

    def test_skips_already_assigned_tasks(self, temp_hive_dir):
        """Already-claimed tasks are skipped before issue creation."""
        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=True)
        candidate = {
            "id": "task_123",
            "project_id": "test-project",
            "title": "Task 1",
            "owner": "another-agent",
            "status": "claimed",
            "claimed_until": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
        }

        assert dispatcher.dispatch(candidate) is False

    @patch.object(AgentDispatcher, "claim_project")
    @patch.object(AgentDispatcher, "add_claude_comment")
    @patch.object(AgentDispatcher, "create_github_issue")
    def test_creates_issue_for_ready_task(
        self,
        mock_create_issue,
        mock_add_comment,
        mock_claim_task,
        temp_hive_dir,
        temp_project,
    ):
        """Dispatch creates an issue and then claims the task."""
        migrate_v1_to_v2(temp_hive_dir)
        candidate = _first_ready_task(temp_hive_dir)
        mock_create_issue.return_value = "https://github.com/test/issue/1"
        mock_add_comment.return_value = True
        mock_claim_task.return_value = True
        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=False)

        result = dispatcher.dispatch(candidate)

        assert result is True
        mock_create_issue.assert_called_once()
        mock_claim_task.assert_called_once_with(candidate, "https://github.com/test/issue/1")

    @patch.object(AgentDispatcher, "claim_project")
    @patch.object(AgentDispatcher, "create_github_issue")
    def test_returns_false_when_claim_fails(
        self,
        mock_create_issue,
        mock_claim_task,
        temp_hive_dir,
        temp_project,
    ):
        """Issue creation without a matching claim reports failure."""
        migrate_v1_to_v2(temp_hive_dir)
        candidate = _first_ready_task(temp_hive_dir)
        mock_create_issue.return_value = "https://github.com/test/issue/1"
        mock_claim_task.return_value = False
        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=False)

        result = dispatcher.dispatch(candidate)

        assert result is False
        mock_create_issue.assert_called_once()
        mock_claim_task.assert_called_once()


class TestValidateEnvironment:
    """Tests for validate_environment."""

    @patch("subprocess.run")
    def test_validates_gh_installed_and_authenticated(self, mock_run, temp_hive_dir):
        """Both gh version and auth checks must pass."""
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        dispatcher = AgentDispatcher(base_path=temp_hive_dir)

        assert dispatcher.validate_environment() is True

    @patch("subprocess.run")
    def test_returns_false_when_auth_fails(self, mock_run, temp_hive_dir):
        """Authentication failures invalidate the environment."""

        def side_effect(cmd, **kwargs):
            if "--version" in cmd:
                return MagicMock(returncode=0, stdout="gh version", stderr="")
            return MagicMock(returncode=1, stdout="", stderr="not logged in")

        mock_run.side_effect = side_effect
        dispatcher = AgentDispatcher(base_path=temp_hive_dir)

        assert dispatcher.validate_environment() is False


class TestRun:
    """Tests for run."""

    @patch.object(AgentDispatcher, "validate_environment")
    @patch.object(AgentDispatcher, "dispatch")
    def test_finds_and_dispatches_work(self, mock_dispatch, mock_validate, temp_hive_dir):
        """run() dispatches ready tasks up to the requested limit."""
        mock_validate.return_value = True
        mock_dispatch.return_value = True
        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=False)
        candidates = [
            {"id": "task_1", "project_id": "demo", "title": "Task 1", "priority": 1},
            {"id": "task_2", "project_id": "demo", "title": "Task 2", "priority": 2},
        ]

        with patch.object(
            dispatcher,
            "ready_work",
            side_effect=[candidates, candidates, candidates[1:], []],
        ):
            result = dispatcher.run(max_dispatches=2)

        assert result is True
        assert mock_dispatch.call_count == 2

    @patch.object(AgentDispatcher, "validate_environment")
    def test_returns_true_when_no_work_available(self, mock_validate, temp_hive_dir):
        """No work is a clean no-op, not an error."""
        mock_validate.return_value = True
        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=False)

        with patch.object(dispatcher, "ready_work", return_value=[]):
            result = dispatcher.run(max_dispatches=1)

        assert result is True

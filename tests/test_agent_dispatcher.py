"""Tests for the Agent Dispatcher module."""

# pylint: disable=unused-argument,import-error,wrong-import-position

import sys
import os
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
import frontmatter

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agent_dispatcher import AgentDispatcher


class TestAgentDispatcherInitialization:
    """Tests for AgentDispatcher initialization."""

    def test_default_initialization(self):
        """Test default initialization."""
        dispatcher = AgentDispatcher()
        assert dispatcher.base_path == Path.cwd()
        assert dispatcher.dry_run is False

    def test_custom_path(self, temp_hive_dir):
        """Test initialization with custom path."""
        dispatcher = AgentDispatcher(base_path=temp_hive_dir)
        assert dispatcher.base_path == Path(temp_hive_dir)

    def test_dry_run_mode(self, temp_hive_dir):
        """Test dry run mode initialization."""
        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=True)
        assert dispatcher.dry_run is True


class TestSelectWork:
    """Tests for select_work method."""

    def test_returns_none_when_no_projects(self, temp_hive_dir):
        """Test returns None when no ready projects."""
        dispatcher = AgentDispatcher(base_path=temp_hive_dir)
        result = dispatcher.select_work([])
        assert result is None

    def test_selects_highest_priority(self, temp_hive_dir):
        """Test selects highest priority project."""
        dispatcher = AgentDispatcher(base_path=temp_hive_dir)

        projects = [
            {
                "project_id": "low",
                "metadata": {"priority": "low", "last_updated": "2025-01-01T00:00:00Z"},
            },
            {
                "project_id": "high",
                "metadata": {"priority": "high", "last_updated": "2025-01-01T00:00:00Z"},
            },
            {
                "project_id": "critical",
                "metadata": {"priority": "critical", "last_updated": "2025-01-01T00:00:00Z"},
            },
        ]

        result = dispatcher.select_work(projects)
        assert result["project_id"] == "critical"

    def test_selects_older_when_same_priority(self, temp_hive_dir):
        """Test selects older project when same priority."""
        dispatcher = AgentDispatcher(base_path=temp_hive_dir)

        projects = [
            {
                "project_id": "newer",
                "metadata": {"priority": "high", "last_updated": "2025-01-15T00:00:00Z"},
            },
            {
                "project_id": "older",
                "metadata": {"priority": "high", "last_updated": "2025-01-01T00:00:00Z"},
            },
        ]

        result = dispatcher.select_work(projects)
        assert result["project_id"] == "older"

    def test_handles_missing_priority(self, temp_hive_dir):
        """Test handles project with missing priority."""
        dispatcher = AgentDispatcher(base_path=temp_hive_dir)

        projects = [
            {
                "project_id": "no-priority",
                "metadata": {"last_updated": "2025-01-01T00:00:00Z"},
            },
        ]

        result = dispatcher.select_work(projects)
        assert result["project_id"] == "no-priority"

    def test_handles_datetime_object_in_last_updated(self, temp_hive_dir):
        """Test handles datetime objects in last_updated (from YAML parser).

        When YAML files are loaded, ISO timestamps are automatically parsed
        into datetime objects. The sort_key function must handle both strings
        and datetime objects.
        """
        dispatcher = AgentDispatcher(base_path=temp_hive_dir)

        # YAML parser often converts timestamps to datetime objects
        projects = [
            {
                "project_id": "newer-datetime",
                "metadata": {
                    "priority": "high",
                    "last_updated": datetime(2025, 1, 15, 0, 0, 0),
                },
            },
            {
                "project_id": "older-datetime",
                "metadata": {
                    "priority": "high",
                    "last_updated": datetime(2025, 1, 1, 0, 0, 0),
                },
            },
        ]

        result = dispatcher.select_work(projects)
        # Should select older project
        assert result["project_id"] == "older-datetime"

    def test_handles_mixed_string_and_datetime(self, temp_hive_dir):
        """Test handles mix of string and datetime last_updated values."""
        dispatcher = AgentDispatcher(base_path=temp_hive_dir)

        projects = [
            {
                "project_id": "string-timestamp",
                "metadata": {
                    "priority": "high",
                    "last_updated": "2025-01-15T00:00:00Z",
                },
            },
            {
                "project_id": "datetime-timestamp",
                "metadata": {
                    "priority": "high",
                    "last_updated": datetime(2025, 1, 1, 0, 0, 0),
                },
            },
        ]

        result = dispatcher.select_work(projects)
        # Should select older (datetime) project
        assert result["project_id"] == "datetime-timestamp"

    def test_handles_timezone_aware_datetime(self, temp_hive_dir):
        """Test handles timezone-aware datetime objects correctly.

        YAML parsers can produce timezone-aware datetime objects. The sort_key
        function must convert these to UTC before comparing to avoid incorrect
        ordering when mixing timezones.
        """
        dispatcher = AgentDispatcher(base_path=temp_hive_dir)

        # Create timezone offsets
        utc_plus_5 = timezone(timedelta(hours=5))

        # Project with UTC+5 timezone: 2025-01-15T05:00:00+05:00 = 2025-01-15T00:00:00Z
        # Project with UTC timezone: 2025-01-01T00:00:00Z
        # The UTC+5 project is actually the same UTC time as Jan 15 midnight UTC
        projects = [
            {
                "project_id": "utc-plus-5",
                "metadata": {
                    "priority": "high",
                    # This is 2025-01-15 05:00 in UTC+5, which is 2025-01-15 00:00 UTC
                    "last_updated": datetime(2025, 1, 15, 5, 0, 0, tzinfo=utc_plus_5),
                },
            },
            {
                "project_id": "utc-older",
                "metadata": {
                    "priority": "high",
                    # This is 2025-01-01 00:00 UTC - clearly older
                    "last_updated": datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                },
            },
        ]

        result = dispatcher.select_work(projects)
        # Should select older project (utc-older is Jan 1, utc-plus-5 is Jan 15 in UTC)
        assert result["project_id"] == "utc-older"


class TestIsAlreadyAssigned:
    """Tests for is_already_assigned method."""

    def test_returns_true_when_owner_set(self, temp_hive_dir):
        """Test returns True when owner is set."""
        dispatcher = AgentDispatcher(base_path=temp_hive_dir)

        project = {
            "metadata": {"owner": "some-agent"},
        }

        assert dispatcher.is_already_assigned(project) is True

    def test_returns_false_when_no_owner(self, temp_hive_dir):
        """Test returns False when no owner."""
        dispatcher = AgentDispatcher(base_path=temp_hive_dir)

        project = {
            "metadata": {"owner": None},
        }

        assert dispatcher.is_already_assigned(project) is False

    def test_returns_false_when_owner_missing(self, temp_hive_dir):
        """Test returns False when owner field is missing."""
        dispatcher = AgentDispatcher(base_path=temp_hive_dir)

        project = {
            "metadata": {},
        }

        assert dispatcher.is_already_assigned(project) is False


class TestClaimProject:
    """Tests for claim_project method."""

    def test_dry_run_does_not_modify(self, temp_hive_dir, temp_project):
        """Test dry run mode doesn't modify files."""
        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=True)

        # Read original content
        with open(temp_project, "r", encoding="utf-8") as f:
            original = f.read()

        project = {
            "path": temp_project,
            "metadata": {"owner": None},
        }

        result = dispatcher.claim_project(project, "https://github.com/test/issue/1")
        assert result is True

        # Verify file wasn't modified
        with open(temp_project, "r", encoding="utf-8") as f:
            after = f.read()
        assert original == after

    def test_sets_owner(self, temp_hive_dir, temp_project):
        """Test that claiming sets owner field."""
        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=False)

        project = {
            "path": temp_project,
            "metadata": {"owner": None},
        }

        result = dispatcher.claim_project(project, "https://github.com/test/issue/1")
        assert result is True

        # Verify owner was set
        with open(temp_project, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)
        assert post.metadata["owner"] == "claude-code"

    def test_adds_issue_link(self, temp_hive_dir, temp_project):
        """Test that claiming adds issue link to agent notes."""
        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=False)

        project = {
            "path": temp_project,
            "metadata": {"owner": None},
        }

        issue_url = "https://github.com/test/issue/123"
        result = dispatcher.claim_project(project, issue_url)
        assert result is True

        # Verify issue link was added
        with open(temp_project, "r", encoding="utf-8") as f:
            content = f.read()
        assert issue_url in content

    def test_updates_last_updated(self, temp_hive_dir, temp_project):
        """Test that claiming updates last_updated timestamp."""
        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=False)

        project = {
            "path": temp_project,
            "metadata": {"owner": None, "last_updated": "2020-01-01T00:00:00Z"},
        }

        result = dispatcher.claim_project(project, "https://github.com/test/issue/1")
        assert result is True

        # Verify timestamp was updated
        with open(temp_project, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)

        # Should be recent (within last minute)
        updated = datetime.fromisoformat(post.metadata["last_updated"].replace("Z", "+00:00"))
        now = datetime.utcnow()
        diff = abs((now - updated.replace(tzinfo=None)).total_seconds())
        assert diff < 60


class TestCreateGitHubIssue:
    """Tests for create_github_issue method."""

    def test_dry_run_returns_fake_url(self, temp_hive_dir):
        """Test dry run returns fake URL."""
        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=True)

        result = dispatcher.create_github_issue(
            "Test Title", "Test Body", ["label1"]
        )

        assert result is not None
        assert "github.com" in result

    @patch("subprocess.run")
    def test_calls_gh_cli(self, mock_run, temp_hive_dir):
        """Test that gh CLI is called correctly."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="https://github.com/owner/repo/issues/1",
            stderr="",
        )

        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=False)
        result = dispatcher.create_github_issue(
            "Test Title", "Test Body", ["label1", "label2"]
        )

        # Verify gh was called
        mock_run.assert_called()
        call_args = mock_run.call_args[0][0]
        assert "gh" in call_args
        assert "issue" in call_args
        assert "create" in call_args
        assert "Test Title" in call_args
        assert "Test Body" in call_args

        # Verify URL returned
        assert result == "https://github.com/owner/repo/issues/1"

    @patch("subprocess.run")
    def test_handles_gh_failure(self, mock_run, temp_hive_dir):
        """Test handling of gh CLI failure."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error creating issue",
        )

        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=False)
        result = dispatcher.create_github_issue(
            "Test Title", "Test Body", []
        )

        assert result is None


class TestAddClaudeComment:
    """Tests for add_claude_comment method."""

    def test_dry_run_returns_true(self, temp_hive_dir):
        """Test dry run mode returns True without calling gh."""
        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=True)

        result = dispatcher.add_claude_comment(
            "https://github.com/owner/repo/issues/123"
        )

        assert result is True

    @patch("subprocess.run")
    def test_successful_comment_addition(self, mock_run, temp_hive_dir):
        """Test successful comment addition."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr="",
        )

        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=False)
        result = dispatcher.add_claude_comment(
            "https://github.com/owner/repo/issues/42"
        )

        assert result is True
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "gh" in call_args
        assert "issue" in call_args
        assert "comment" in call_args
        assert "42" in call_args
        assert "@claude" in call_args[call_args.index("--body") + 1]

    @patch("subprocess.run")
    def test_handles_trailing_slash_in_url(self, mock_run, temp_hive_dir):
        """Test URL parsing handles trailing slashes."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr="",
        )

        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=False)
        result = dispatcher.add_claude_comment(
            "https://github.com/owner/repo/issues/99/"
        )

        assert result is True
        call_args = mock_run.call_args[0][0]
        assert "99" in call_args

    @patch("subprocess.run")
    def test_handles_gh_cli_failure(self, mock_run, temp_hive_dir):
        """Test handling of gh CLI failure."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: permission denied",
        )

        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=False)
        result = dispatcher.add_claude_comment(
            "https://github.com/owner/repo/issues/123"
        )

        assert result is False

    @patch("subprocess.run")
    def test_handles_timeout(self, mock_run, temp_hive_dir):
        """Test handling of subprocess timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("gh", 30)

        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=False)
        result = dispatcher.add_claude_comment(
            "https://github.com/owner/repo/issues/123"
        )

        assert result is False

    @patch("subprocess.run")
    def test_handles_general_exception(self, mock_run, temp_hive_dir):
        """Test handling of general exceptions."""
        mock_run.side_effect = OSError("Network error")

        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=False)
        result = dispatcher.add_claude_comment(
            "https://github.com/owner/repo/issues/123"
        )

        assert result is False


class TestDispatch:
    """Tests for dispatch method."""

    def test_skips_already_assigned(self, temp_hive_dir, temp_project):
        """Test that already assigned projects are skipped."""
        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=True)

        project = {
            "path": temp_project,
            "project_id": "test",
            "metadata": {"owner": "another-agent", "project_id": "test"},
            "content": "# Test",
        }

        result = dispatcher.dispatch(project)
        assert result is False

    @patch.object(AgentDispatcher, "create_github_issue")
    def test_creates_issue_for_ready_project(
        self, mock_create_issue, temp_hive_dir, temp_project
    ):
        """Test that issues are created for ready projects."""
        mock_create_issue.return_value = "https://github.com/test/issue/1"

        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=False)

        project = {
            "path": temp_project,
            "project_id": "test-project",
            "metadata": {
                "owner": None,
                "project_id": "test-project",
                "priority": "high",
                "tags": ["test"],
            },
            "content": "# Test\n\n- [ ] Task 1",
        }

        result = dispatcher.dispatch(project)

        assert result is True
        mock_create_issue.assert_called_once()

    @patch.object(AgentDispatcher, "claim_project")
    @patch.object(AgentDispatcher, "create_github_issue")
    def test_returns_false_when_claim_fails(
        self, mock_create_issue, mock_claim_project, temp_hive_dir, temp_project
    ):
        """Test that dispatch returns False when claim_project fails after issue creation.

        This is a critical error path - if issue is created but claim fails,
        we could end up with duplicate issues on retry.
        """
        mock_create_issue.return_value = "https://github.com/test/issue/1"
        mock_claim_project.return_value = False  # Simulate claim failure

        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=False)

        project = {
            "path": temp_project,
            "project_id": "test-project",
            "metadata": {
                "owner": None,
                "project_id": "test-project",
                "priority": "high",
                "tags": ["test"],
            },
            "content": "# Test\n\n- [ ] Task 1",
        }

        result = dispatcher.dispatch(project)

        # Should return False because claim failed
        assert result is False
        # Issue was created
        mock_create_issue.assert_called_once()
        # Claim was attempted
        mock_claim_project.assert_called_once()


class TestValidateEnvironment:
    """Tests for validate_environment method."""

    @patch("subprocess.run")
    def test_validates_gh_installed(self, mock_run, temp_hive_dir):
        """Test validation checks gh is installed."""
        # Mock gh --version success, but auth failure
        def side_effect(cmd, **kwargs):
            if "--version" in cmd:
                return MagicMock(returncode=0, stdout="gh version 2.0.0", stderr="")
            if "auth" in cmd:
                return MagicMock(returncode=1, stdout="", stderr="not logged in")
            return MagicMock(returncode=0)

        mock_run.side_effect = side_effect

        dispatcher = AgentDispatcher(base_path=temp_hive_dir)
        result = dispatcher.validate_environment()

        # Should fail because auth check fails
        assert result is False

    @patch("subprocess.run")
    def test_validates_gh_authenticated(self, mock_run, temp_hive_dir):
        """Test validation checks gh is authenticated."""
        # Mock both commands succeeding
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

        dispatcher = AgentDispatcher(base_path=temp_hive_dir)
        result = dispatcher.validate_environment()

        assert result is True


class TestRun:
    """Tests for run method."""

    @patch.object(AgentDispatcher, "validate_environment")
    @patch.object(AgentDispatcher, "dispatch")
    def test_finds_and_dispatches_work(
        self, mock_dispatch, mock_validate, temp_hive_dir, temp_project
    ):
        """Test that run finds and dispatches ready work."""
        mock_validate.return_value = True
        mock_dispatch.return_value = True

        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=False)
        result = dispatcher.run(max_dispatches=1)

        assert result is True
        mock_dispatch.assert_called_once()

    @patch.object(AgentDispatcher, "validate_environment")
    def test_returns_true_when_no_work(self, mock_validate, temp_hive_dir):
        """Test returns True when no work available (no work is not an error)."""
        mock_validate.return_value = True

        # No projects in temp_hive_dir initially
        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=False)
        result = dispatcher.run()

        assert result is True  # No work is success, not failure

    def test_dry_run_skips_validation(self, temp_hive_dir):
        """Test dry run skips environment validation."""
        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=True)

        # Should not fail even without gh installed
        result = dispatcher.run()

        # Returns True - no work is success, validation was skipped
        assert result is True

    @patch.object(AgentDispatcher, "validate_environment")
    def test_respects_max_dispatches(self, mock_validate, temp_hive_dir):
        """Test that max_dispatches limit is respected."""
        mock_validate.return_value = True

        # Create multiple projects
        projects_dir = Path(temp_hive_dir) / "projects"
        for i in range(3):
            project_dir = projects_dir / f"project-{i}"
            project_dir.mkdir(parents=True)

            post = frontmatter.Post(
                f"# Project {i}\n\n- [ ] Task",
                project_id=f"project-{i}",
                status="active",
                owner=None,
                blocked=False,
                priority="high",
            )

            with open(project_dir / "AGENCY.md", "w", encoding="utf-8") as f:
                f.write(frontmatter.dumps(post))

        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=True)
        result = dispatcher.run(max_dispatches=2)

        # Should succeed (dry run, so issues aren't actually created)
        assert result is True

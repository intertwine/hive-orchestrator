"""Tests for the Context Assembler module."""

# pylint: disable=unused-argument,import-error,wrong-import-position

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import frontmatter
import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from context_assembler import (
    build_issue_body,
    build_issue_labels,
    build_issue_title,
    cleanup_external_repo,
    clone_external_repo,
    generate_file_tree,
    get_external_repo_context,
    get_next_task,
    get_relevant_files_content,
)
from src.hive.migrate import migrate_v1_to_v2
from src.hive.scheduler.query import ready_tasks


class TestGenerateFileTree:
    """Tests for generate_file_tree."""

    def test_empty_directory(self):
        """Empty directories render as an empty string."""
        with tempfile.TemporaryDirectory() as temp_dir:
            assert generate_file_tree(Path(temp_dir)) == ""

    def test_nested_directories(self):
        """Nested files and directories are included up to max depth."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "src").mkdir()
            (temp_path / "src" / "main.py").write_text("print('hi')", encoding="utf-8")

            tree = generate_file_tree(temp_path, max_depth=3)

            assert "src" in tree
            assert "main.py" in tree

    def test_excludes_hidden_files(self):
        """Hidden files and __pycache__ are skipped."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / ".hidden").write_text("secret", encoding="utf-8")
            (temp_path / "__pycache__").mkdir()
            (temp_path / "visible.txt").write_text("hello", encoding="utf-8")

            tree = generate_file_tree(temp_path)

            assert ".hidden" not in tree
            assert "__pycache__" not in tree
            assert "visible.txt" in tree


class TestRelevantFiles:
    """Tests for get_relevant_files_content."""

    def test_reads_existing_file(self):
        """Existing files are included in the rendered context."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            project_dir = temp_path / "project"
            project_dir.mkdir()
            (project_dir / "file.py").write_text("print('hello')", encoding="utf-8")

            content = get_relevant_files_content(project_dir, ["file.py"], temp_path)

            assert "print('hello')" in content
            assert "file.py" in content

    def test_handles_missing_file(self):
        """Missing files are called out instead of raising."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            project_dir = temp_path / "project"
            project_dir.mkdir()

            content = get_relevant_files_content(project_dir, ["missing.py"], temp_path)

            assert "File not found" in content

    def test_truncates_large_files(self):
        """Large files are truncated for issue body safety."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            project_dir = temp_path / "project"
            project_dir.mkdir()
            (project_dir / "large.txt").write_text("x" * 15000, encoding="utf-8")

            content = get_relevant_files_content(project_dir, ["large.txt"], temp_path)

            assert "truncated" in content


class TestLegacyHelpers:
    """Compatibility helpers kept for legacy-shaped inputs."""

    def test_get_next_task_finds_first_open_checkbox(self):
        """The compatibility parser still finds the first open checkbox task."""
        content = """# Project

## Tasks
- [x] Done
- [ ] First open task
- [ ] Second open task
"""

        assert get_next_task(content) == "First open task"

    def test_get_next_task_returns_none_when_complete(self):
        """All-done lists return no task."""
        content = """# Project

## Tasks
- [x] Done
"""

        assert get_next_task(content) is None

    def test_build_issue_title_with_task(self):
        """Issue titles include the task preview when present."""
        title = build_issue_title("my-project", "Implement feature X")
        assert "[Agent Hive]" in title
        assert "my-project" in title
        assert "Implement feature X" in title

    def test_build_issue_title_without_task(self):
        """Issue titles fall back to project-only phrasing."""
        title = build_issue_title("my-project", None)
        assert "[Agent Hive]" in title
        assert "Work on my-project" in title


class TestBuildIssueBodyV2:
    """Tests for v2 canonical issue assembly."""

    def test_builds_issue_body_from_canonical_task(self, temp_hive_dir, temp_project):
        """Canonical task issue bodies include v2 context and handoff details."""
        migrate_v1_to_v2(temp_hive_dir)
        task = ready_tasks(temp_hive_dir, project_id="test-project", limit=1)[0]

        body = build_issue_body(task, Path(temp_hive_dir), task["title"])

        assert "@claude" in body
        assert "Canonical Task" in body
        assert task["id"] in body
        assert "AGENCY.md Projection" in body
        assert "Hive Context" in body
        assert ".hive/tasks/" in body
        assert "hive sync projections" in body

    def test_includes_task_label_for_canonical_candidate(self, temp_hive_dir, temp_project):
        """Canonical candidates get task-scoped labels."""
        migrate_v1_to_v2(temp_hive_dir)
        task = ready_tasks(temp_hive_dir, project_id="test-project", limit=1)[0]

        labels = build_issue_labels(task)

        assert "agent-hive" in labels
        assert f"project:{task['project_id']}" in labels
        assert f"task:{task['id']}" in labels

    def test_external_repo_section_uses_target_repo_metadata(self, temp_hive_dir):
        """External target repo metadata is included when present on the project."""
        project_dir = Path(temp_hive_dir) / "projects" / "external"
        project_dir.mkdir(parents=True)
        agency = frontmatter.Post(
            """# External Project

## Tasks
- [ ] Analyze repository
""",
            project_id="external-project",
            status="active",
            priority="high",
            target_repo={
                "url": "https://github.com/example/repo",
                "branch": "main",
            },
        )
        (project_dir / "AGENCY.md").write_text(frontmatter.dumps(agency), encoding="utf-8")

        migrate_v1_to_v2(temp_hive_dir)
        task = ready_tasks(temp_hive_dir, project_id="external-project", limit=1)[0]

        with tempfile.TemporaryDirectory() as clone_dir:
            clone_path = Path(clone_dir)
            with patch("context_assembler.clone_external_repo", return_value=clone_path):
                with patch(
                    "context_assembler.get_external_repo_context",
                    return_value=("├── src\n", "### `README.md`\n\n```markdown\n# Repo\n```"),
                ):
                    body = build_issue_body(task, Path(temp_hive_dir), task["title"])

        assert "Target Repository" in body
        assert "https://github.com/example/repo" in body
        assert "Click to expand repository structure" in body

    def test_missing_scheduler_task_file_falls_back_to_legacy_project_shape(
        self, temp_hive_dir, temp_project
    ):
        """A missing task file from the scheduler path should not raise."""
        project = {
            "path": temp_project,
            "project_id": "test-project",
            "metadata": {"project_id": "test-project", "priority": "high"},
            "content": "# Test Project\n\n## Tasks\n- [ ] Task 1\n",
        }

        with patch(
            "context_assembler.scheduler_ready_tasks",
            return_value=[
                {"id": "task_missing", "project_id": "test-project", "title": "Ghost task"}
            ],
        ):
            with patch("context_assembler.get_task", side_effect=FileNotFoundError):
                body = build_issue_body(project, Path(temp_hive_dir))

        assert "AGENCY.md Projection" in body
        assert "test-project" in body


class TestExternalRepoHelpers:
    """Tests for external repository helper functions."""

    def test_get_external_repo_context_generates_tree(self):
        """The helper renders a filtered repository tree and key files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "src").mkdir()
            (temp_path / "src" / "index.ts").write_text(
                "export const main = () => {};", encoding="utf-8"
            )
            (temp_path / "package.json").write_text('{"name": "test"}', encoding="utf-8")

            tree, files_content = get_external_repo_context(temp_path)

            assert "src" in tree
            assert "index.ts" in tree
            assert "package.json" in files_content

    def test_get_external_repo_context_with_custom_files(self):
        """Custom file selection overrides defaults."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "custom.txt").write_text("custom content", encoding="utf-8")
            (temp_path / "package.json").write_text('{"name": "default"}', encoding="utf-8")

            _, files_content = get_external_repo_context(temp_path, key_files=["custom.txt"])

            assert "custom content" in files_content
            assert "default" not in files_content

    def test_cleanup_external_repo(self):
        """cleanup_external_repo removes existing temporary clones."""
        temp_dir = tempfile.mkdtemp(prefix="test_cleanup_")
        temp_path = Path(temp_dir)
        (temp_path / "file.txt").write_text("test", encoding="utf-8")

        cleanup_external_repo(temp_path)

        assert not temp_path.exists()

    def test_rejects_non_https_clone_urls(self):
        """Only HTTPS clone targets are allowed."""
        assert clone_external_repo("http://github.com/user/repo") is None
        assert clone_external_repo("git@github.com:user/repo.git") is None
        assert clone_external_repo("file:///tmp/repo") is None

    @patch("context_assembler.subprocess.run")
    @patch("context_assembler.tempfile.mkdtemp")
    def test_successful_clone(self, mock_mkdtemp, mock_run):
        """Successful clones return the temp directory path."""
        mock_mkdtemp.return_value = "/tmp/hive_external_test"
        mock_run.return_value = MagicMock(returncode=0)

        result = clone_external_repo("https://github.com/user/repo")

        assert result == Path("/tmp/hive_external_test")
        assert "git" in mock_run.call_args[0][0]

    @patch("context_assembler.subprocess.run")
    @patch("context_assembler.tempfile.mkdtemp")
    @patch("context_assembler.shutil.rmtree")
    def test_clone_failure_cleans_up(self, mock_rmtree, mock_mkdtemp, mock_run):
        """Failed clones clean up their temp directory."""
        mock_mkdtemp.return_value = "/tmp/hive_external_test"
        mock_run.return_value = MagicMock(returncode=1, stderr="clone failed")

        result = clone_external_repo("https://github.com/user/repo")

        assert result is None
        mock_rmtree.assert_called_once_with("/tmp/hive_external_test", ignore_errors=True)

    @patch("context_assembler.subprocess.run")
    @patch("context_assembler.tempfile.mkdtemp")
    @patch("context_assembler.shutil.rmtree")
    def test_timeout_cleans_up(self, mock_rmtree, mock_mkdtemp, mock_run):
        """Clone timeouts also clean up their temp directory."""
        mock_mkdtemp.return_value = "/tmp/hive_external_test"
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=120)

        result = clone_external_repo("https://github.com/user/repo")

        assert result is None
        mock_rmtree.assert_called_once_with("/tmp/hive_external_test", ignore_errors=True)


class TestExternalRepoCleanup:
    """Regression coverage for external repo cleanup."""

    def test_build_issue_body_cleans_up_external_repo_on_exception(self):
        """Temporary clone directories are cleaned up if context extraction fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            project_dir = temp_path / "projects" / "test"
            project_dir.mkdir(parents=True)

            content = """# Test Project

## Tasks
- [ ] First task
"""
            post = frontmatter.Post(
                content,
                project_id="test-project",
                status="active",
                priority="high",
                target_repo={
                    "url": "https://github.com/example/repo",
                    "branch": "main",
                },
            )
            agency_file = project_dir / "AGENCY.md"
            agency_file.write_text(frontmatter.dumps(post), encoding="utf-8")

            project = {
                "path": str(agency_file),
                "project_id": "test-project",
                "metadata": post.metadata,
                "content": content,
            }

            cloned_path = None
            cleanup_called = False

            def mock_clone(url, branch):
                nonlocal cloned_path
                cloned_path = Path(tempfile.mkdtemp(prefix="hive_external_"))
                return cloned_path

            def mock_get_context(repo_path, key_files=None):
                raise RuntimeError("Simulated error during context extraction")

            def mock_cleanup(repo_path):
                nonlocal cleanup_called
                cleanup_called = True
                if repo_path and repo_path.exists():
                    import shutil

                    shutil.rmtree(repo_path, ignore_errors=True)

            with patch("context_assembler.clone_external_repo", side_effect=mock_clone):
                with patch(
                    "context_assembler.get_external_repo_context",
                    side_effect=mock_get_context,
                ):
                    with patch(
                        "context_assembler.cleanup_external_repo",
                        side_effect=mock_cleanup,
                    ):
                        with pytest.raises(RuntimeError, match="Simulated error"):
                            build_issue_body(project, temp_path)

            assert cleanup_called
            if cloned_path:
                assert not cloned_path.exists()

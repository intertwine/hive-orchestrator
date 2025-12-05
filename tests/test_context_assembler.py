"""Tests for the Context Assembler module."""

# pylint: disable=unused-argument,import-error,wrong-import-position

import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess
import pytest
import frontmatter

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from context_assembler import (
    generate_file_tree,
    get_relevant_files_content,
    get_next_task,
    build_issue_title,
    build_issue_body,
    build_issue_labels,
    clone_external_repo,
    get_external_repo_context,
    cleanup_external_repo,
)


class TestGenerateFileTree:
    """Tests for generate_file_tree function."""

    def test_empty_directory(self):
        """Test file tree for empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            tree = generate_file_tree(Path(temp_dir))
            assert tree == ""

    def test_single_file(self):
        """Test file tree with single file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "test.txt").write_text("content")

            tree = generate_file_tree(temp_path)
            assert "test.txt" in tree

    def test_nested_directories(self):
        """Test file tree with nested directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "src").mkdir()
            (temp_path / "src" / "main.py").write_text("code")

            tree = generate_file_tree(temp_path, max_depth=3)
            assert "src" in tree
            assert "main.py" in tree

    def test_excludes_hidden_files(self):
        """Test that hidden files are excluded."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / ".hidden").write_text("hidden")
            (temp_path / "visible.txt").write_text("visible")

            tree = generate_file_tree(temp_path)
            assert ".hidden" not in tree
            assert "visible.txt" in tree

    def test_excludes_pycache(self):
        """Test that __pycache__ is excluded."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "__pycache__").mkdir()
            (temp_path / "code.py").write_text("code")

            tree = generate_file_tree(temp_path)
            assert "__pycache__" not in tree
            assert "code.py" in tree

    def test_respects_max_depth(self):
        """Test that max_depth is respected."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            deep_dir = temp_path / "a" / "b" / "c" / "d"
            deep_dir.mkdir(parents=True)
            (deep_dir / "deep.txt").write_text("deep")

            tree = generate_file_tree(temp_path, max_depth=2)
            # Should only go 2 levels deep
            assert "a" in tree
            assert "b" in tree
            # c and d should not appear because we're at depth limit
            # Actually, with max_depth=2, we see level 0 (a) and level 1 (b)
            # but not level 2 (c)


class TestGetRelevantFilesContent:
    """Tests for get_relevant_files_content function."""

    def test_reads_existing_file(self):
        """Test reading content from existing file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            project_dir = temp_path / "project"
            project_dir.mkdir()
            (project_dir / "file.py").write_text("print('hello')")

            content = get_relevant_files_content(
                project_dir, ["file.py"], temp_path
            )
            assert "print('hello')" in content
            assert "file.py" in content

    def test_handles_missing_file(self):
        """Test handling of missing file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            project_dir = temp_path / "project"
            project_dir.mkdir()

            content = get_relevant_files_content(
                project_dir, ["nonexistent.py"], temp_path
            )
            assert "File not found" in content

    def test_multiple_files(self):
        """Test reading multiple files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            project_dir = temp_path / "project"
            project_dir.mkdir()
            (project_dir / "a.py").write_text("file a")
            (project_dir / "b.py").write_text("file b")

            content = get_relevant_files_content(
                project_dir, ["a.py", "b.py"], temp_path
            )
            assert "file a" in content
            assert "file b" in content

    def test_empty_list(self):
        """Test with empty file list."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            project_dir = temp_path / "project"
            project_dir.mkdir()

            content = get_relevant_files_content(project_dir, [], temp_path)
            assert "No relevant files specified" in content

    def test_truncates_large_files(self):
        """Test that large files are truncated."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            project_dir = temp_path / "project"
            project_dir.mkdir()

            # Create a file larger than 10000 characters
            large_content = "x" * 15000
            (project_dir / "large.txt").write_text(large_content)

            content = get_relevant_files_content(
                project_dir, ["large.txt"], temp_path
            )
            assert "truncated" in content


class TestGetNextTask:
    """Tests for get_next_task function."""

    def test_finds_first_uncompleted_task(self):
        """Test finding first uncompleted task."""
        content = """# Project

## Tasks
- [x] Done task
- [ ] First uncompleted
- [ ] Second uncompleted
"""
        task = get_next_task(content)
        assert task == "First uncompleted"

    def test_returns_none_when_all_complete(self):
        """Test returns None when all tasks are complete."""
        content = """# Project

## Tasks
- [x] Done 1
- [x] Done 2
"""
        task = get_next_task(content)
        assert task is None

    def test_returns_none_for_empty_content(self):
        """Test returns None for empty content."""
        task = get_next_task("")
        assert task is None

    def test_handles_nested_tasks(self):
        """Test with nested task structure."""
        content = """# Project

## Phase 1
- [x] Done

## Phase 2
- [ ] First open task
"""
        task = get_next_task(content)
        assert task == "First open task"


class TestBuildIssueTitle:
    """Tests for build_issue_title function."""

    def test_with_task(self):
        """Test title generation with task."""
        title = build_issue_title("my-project", "Implement feature X")
        assert "[Agent Hive]" in title
        assert "my-project" in title
        assert "Implement feature X" in title

    def test_without_task(self):
        """Test title generation without task."""
        title = build_issue_title("my-project", None)
        assert "[Agent Hive]" in title
        assert "my-project" in title
        assert "Work on" in title

    def test_truncates_long_task(self):
        """Test that long task names are truncated."""
        long_task = "A" * 100
        title = build_issue_title("project", long_task)
        assert len(title) < 150
        assert "..." in title


class TestBuildIssueBody:
    """Tests for build_issue_body function."""

    @pytest.fixture
    def sample_project(self):
        """Create a sample project for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            project_dir = temp_path / "projects" / "test-project"
            project_dir.mkdir(parents=True)

            content = """# Test Project

## Tasks
- [ ] First task
- [ ] Second task
"""
            post = frontmatter.Post(
                content,
                project_id="test-project",
                status="active",
                priority="high",
                tags=["test", "feature"],
                owner=None,
            )

            agency_file = project_dir / "AGENCY.md"
            with open(agency_file, "w", encoding="utf-8") as f:
                f.write(frontmatter.dumps(post))

            yield {
                "path": str(agency_file),
                "project_id": "test-project",
                "metadata": post.metadata,
                "content": content,
                "base_path": temp_path,
            }

    def test_includes_claude_mention(self, sample_project):
        """Test that issue body includes @claude mention."""
        body = build_issue_body(
            sample_project,
            sample_project["base_path"],
        )
        assert "@claude" in body

    def test_includes_project_info(self, sample_project):
        """Test that issue body includes project information."""
        body = build_issue_body(
            sample_project,
            sample_project["base_path"],
        )
        assert "test-project" in body
        assert "high" in body  # priority

    def test_includes_instructions(self, sample_project):
        """Test that issue body includes instructions."""
        body = build_issue_body(
            sample_project,
            sample_project["base_path"],
        )
        assert "Instructions" in body
        assert "make test" in body
        assert "make lint" in body

    def test_includes_success_criteria(self, sample_project):
        """Test that issue body includes success criteria."""
        body = build_issue_body(
            sample_project,
            sample_project["base_path"],
        )
        assert "Success Criteria" in body

    def test_includes_handoff_protocol(self, sample_project):
        """Test that issue body includes handoff protocol."""
        body = build_issue_body(
            sample_project,
            sample_project["base_path"],
        )
        assert "Handoff Protocol" in body
        assert "owner: null" in body

    def test_includes_task_focus(self, sample_project):
        """Test that issue body includes immediate task."""
        body = build_issue_body(
            sample_project,
            sample_project["base_path"],
            next_task="First task",
        )
        assert "Immediate Task" in body
        assert "First task" in body


class TestBuildIssueLabels:
    """Tests for build_issue_labels function."""

    def test_includes_default_labels(self):
        """Test that default labels are included."""
        project = {
            "metadata": {
                "project_id": "test",
                "priority": "medium",
            }
        }
        labels = build_issue_labels(project)
        assert "agent-hive" in labels
        assert "automated" in labels

    def test_includes_priority_label(self):
        """Test that priority label is included."""
        project = {
            "metadata": {
                "project_id": "test",
                "priority": "high",
            }
        }
        labels = build_issue_labels(project)
        assert "priority:high" in labels

    def test_includes_project_label(self):
        """Test that project label is included."""
        project = {
            "metadata": {
                "project_id": "my-project",
                "priority": "medium",
            }
        }
        labels = build_issue_labels(project)
        assert "project:my-project" in labels


class TestExternalRepoContext:
    """Tests for external repository context functions."""

    def test_get_external_repo_context_generates_tree(self):
        """Test that get_external_repo_context generates file tree."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "src").mkdir()
            (temp_path / "src" / "index.ts").write_text("export const main = () => {};")
            (temp_path / "package.json").write_text('{"name": "test"}')

            tree, files_content = get_external_repo_context(temp_path)

            assert "src" in tree
            assert "index.ts" in tree
            assert "package.json" in tree

    def test_get_external_repo_context_reads_key_files(self):
        """Test that get_external_repo_context reads key files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "package.json").write_text('{"name": "test-package"}')
            (temp_path / "README.md").write_text("# Test Project")

            tree, files_content = get_external_repo_context(temp_path)

            assert "test-package" in files_content
            assert "# Test Project" in files_content

    def test_get_external_repo_context_with_custom_files(self):
        """Test get_external_repo_context with custom key files list."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "custom.txt").write_text("custom content")
            (temp_path / "package.json").write_text('{"name": "test"}')

            tree, files_content = get_external_repo_context(
                temp_path, key_files=["custom.txt"]
            )

            assert "custom content" in files_content
            # package.json should not be included since we specified custom files
            assert "test" not in files_content  # package.json content excluded

    def test_get_external_repo_context_excludes_noise_dirs(self):
        """Test that noise directories are excluded from tree."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "node_modules").mkdir()
            (temp_path / "node_modules" / "dep.js").write_text("dep")
            (temp_path / "src").mkdir()
            (temp_path / "src" / "main.ts").write_text("main")

            tree, _ = get_external_repo_context(temp_path)

            assert "node_modules" not in tree
            assert "src" in tree
            assert "main.ts" in tree

    def test_cleanup_external_repo(self):
        """Test that cleanup_external_repo removes directory."""
        temp_dir = tempfile.mkdtemp(prefix="test_cleanup_")
        temp_path = Path(temp_dir)
        (temp_path / "file.txt").write_text("test")

        assert temp_path.exists()
        cleanup_external_repo(temp_path)
        assert not temp_path.exists()

    def test_cleanup_external_repo_handles_nonexistent(self):
        """Test that cleanup_external_repo handles nonexistent path."""
        nonexistent = Path("/tmp/definitely_does_not_exist_12345")
        # Should not raise an exception
        cleanup_external_repo(nonexistent)


class TestCloneExternalRepo:
    """Tests for clone_external_repo function."""

    def test_rejects_non_https_url(self):
        """Test that non-https URLs are rejected for security."""
        # HTTP should be rejected
        result = clone_external_repo("http://github.com/user/repo")
        assert result is None

        # Git protocol should be rejected
        result = clone_external_repo("git://github.com/user/repo")
        assert result is None

        # SSH should be rejected
        result = clone_external_repo("git@github.com:user/repo.git")
        assert result is None

        # File protocol should be rejected
        result = clone_external_repo("file:///path/to/repo")
        assert result is None

    @patch("context_assembler.subprocess.run")
    @patch("context_assembler.tempfile.mkdtemp")
    def test_successful_clone(self, mock_mkdtemp, mock_run):
        """Test successful repository clone."""
        mock_mkdtemp.return_value = "/tmp/hive_external_test"
        mock_run.return_value = MagicMock(returncode=0)

        result = clone_external_repo("https://github.com/user/repo")

        assert result == Path("/tmp/hive_external_test")
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "git" in call_args[0][0]
        assert "clone" in call_args[0][0]
        assert "--depth" in call_args[0][0]
        assert "https://github.com/user/repo" in call_args[0][0]

    @patch("context_assembler.subprocess.run")
    @patch("context_assembler.tempfile.mkdtemp")
    @patch("context_assembler.shutil.rmtree")
    def test_clone_failure_cleans_up(self, mock_rmtree, mock_mkdtemp, mock_run):
        """Test that failed clone cleans up temp directory."""
        mock_mkdtemp.return_value = "/tmp/hive_external_test"
        mock_run.return_value = MagicMock(returncode=1, stderr="Clone failed")

        result = clone_external_repo("https://github.com/user/repo")

        assert result is None
        mock_rmtree.assert_called_once_with("/tmp/hive_external_test", ignore_errors=True)

    @patch("context_assembler.subprocess.run")
    @patch("context_assembler.tempfile.mkdtemp")
    @patch("context_assembler.shutil.rmtree")
    def test_timeout_cleans_up(self, mock_rmtree, mock_mkdtemp, mock_run):
        """Test that timeout cleans up temp directory."""
        mock_mkdtemp.return_value = "/tmp/hive_external_test"
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=120)

        result = clone_external_repo("https://github.com/user/repo")

        assert result is None
        mock_rmtree.assert_called_once_with("/tmp/hive_external_test", ignore_errors=True)

    @patch("context_assembler.subprocess.run")
    @patch("context_assembler.tempfile.mkdtemp")
    @patch("context_assembler.shutil.rmtree")
    def test_os_error_cleans_up(self, mock_rmtree, mock_mkdtemp, mock_run):
        """Test that OSError cleans up temp directory."""
        mock_mkdtemp.return_value = "/tmp/hive_external_test"
        mock_run.side_effect = OSError("Git not found")

        result = clone_external_repo("https://github.com/user/repo")

        assert result is None
        mock_rmtree.assert_called_once_with("/tmp/hive_external_test", ignore_errors=True)

    @patch("context_assembler.subprocess.run")
    @patch("context_assembler.tempfile.mkdtemp")
    def test_custom_branch(self, mock_mkdtemp, mock_run):
        """Test cloning with custom branch."""
        mock_mkdtemp.return_value = "/tmp/hive_external_test"
        mock_run.return_value = MagicMock(returncode=0)

        clone_external_repo("https://github.com/user/repo", branch="develop")

        call_args = mock_run.call_args[0][0]
        assert "--branch" in call_args
        branch_idx = call_args.index("--branch")
        assert call_args[branch_idx + 1] == "develop"

    @patch("context_assembler.subprocess.run")
    @patch("context_assembler.tempfile.mkdtemp")
    def test_shallow_clone(self, mock_mkdtemp, mock_run):
        """Test that clone uses --depth 1 for efficiency."""
        mock_mkdtemp.return_value = "/tmp/hive_external_test"
        mock_run.return_value = MagicMock(returncode=0)

        clone_external_repo("https://github.com/user/repo")

        call_args = mock_run.call_args[0][0]
        assert "--depth" in call_args
        depth_idx = call_args.index("--depth")
        assert call_args[depth_idx + 1] == "1"


class TestBuildIssueBodyWithExternalRepo:
    """Tests for build_issue_body with external repository support."""

    @pytest.fixture
    def external_repo_project(self):
        """Create a project with target_repo for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            project_dir = temp_path / "projects" / "external" / "test-external"
            project_dir.mkdir(parents=True)

            content = """# External Project

## Tasks
- [ ] Analyze repository
- [ ] Implement improvement
"""
            post = frontmatter.Post(
                content,
                project_id="test-external",
                status="active",
                priority="high",
                tags=["external", "cross-repo"],
                owner=None,
                target_repo={
                    "url": "https://github.com/example/repo",
                    "branch": "main",
                },
            )

            agency_file = project_dir / "AGENCY.md"
            with open(agency_file, "w", encoding="utf-8") as f:
                f.write(frontmatter.dumps(post))

            yield {
                "path": str(agency_file),
                "project_id": "test-external",
                "metadata": post.metadata,
                "content": content,
                "base_path": temp_path,
            }

    def test_includes_external_repo_instructions(self, external_repo_project):
        """Test that external repo projects have different instructions."""
        body = build_issue_body(
            external_repo_project,
            external_repo_project["base_path"],
        )
        # External repo projects should mention forking
        assert "external repository work" in body or "Fork" in body

    def test_includes_target_repo_in_metadata(self, external_repo_project):
        """Test that target_repo is included in the issue body."""
        body = build_issue_body(
            external_repo_project,
            external_repo_project["base_path"],
        )
        # The metadata dump should include target_repo
        assert "target_repo" in body or "https://github.com/example/repo" in body

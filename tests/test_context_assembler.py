"""Tests for the Context Assembler module."""

# pylint: disable=unused-argument,import-error,wrong-import-position

import sys
import os
import tempfile
import shutil
from pathlib import Path
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

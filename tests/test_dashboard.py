"""Tests for the Dashboard UI functions."""

# pylint: disable=unused-argument,unused-import,import-error,wrong-import-position

import sys
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dashboard import (
    load_project,
    discover_projects,
    generate_file_tree,
    generate_deep_work_context,
)


class TestLoadProject:
    """Test loading project AGENCY.md files."""

    def test_load_project_success(self, temp_project):
        """Test successfully loading a project."""
        project_data = load_project(temp_project)

        assert project_data is not None
        assert "path" in project_data
        assert "metadata" in project_data
        assert "content" in project_data
        assert "raw" in project_data
        assert project_data["metadata"]["project_id"] == "test-project"
        assert project_data["metadata"]["status"] == "active"

    def test_load_project_nonexistent(self):
        """Test loading a non-existent project."""
        with patch("streamlit.error"):
            project_data = load_project("/nonexistent/path/AGENCY.md")
            assert project_data is None

    def test_load_project_malformed(self, temp_hive_dir):
        """Test loading a malformed AGENCY.md."""
        # Create malformed file (frontmatter is lenient and will parse this)
        project_dir = Path(temp_hive_dir) / "projects" / "malformed"
        project_dir.mkdir(parents=True)
        agency_file = project_dir / "AGENCY.md"
        agency_file.write_text("This is not valid frontmatter")

        with patch("streamlit.error"):
            project_data = load_project(str(agency_file))
            # frontmatter library is lenient - files without --- delimiters parse successfully
            assert project_data is not None

    def test_load_project_contains_raw_content(self, temp_project):
        """Test that loaded project contains raw frontmatter."""
        project_data = load_project(temp_project)

        assert project_data is not None
        assert "---" in project_data["raw"]
        assert "project_id: test-project" in project_data["raw"]


class TestDiscoverProjects:
    """Test discovering projects in the projects directory."""

    def test_discover_single_project(self, temp_hive_dir, temp_project):
        """Test discovering a single project."""
        base_path = Path(temp_hive_dir)

        with patch("streamlit.error"):
            projects = discover_projects(base_path)

            assert len(projects) == 1
            assert projects[0]["metadata"]["project_id"] == "test-project"

    def test_discover_multiple_projects(self, temp_hive_dir, temp_project, temp_blocked_project):
        """Test discovering multiple projects."""
        base_path = Path(temp_hive_dir)

        with patch("streamlit.error"):
            projects = discover_projects(base_path)

            assert len(projects) == 2
            project_ids = [p["metadata"]["project_id"] for p in projects]
            assert "test-project" in project_ids
            assert "blocked-project" in project_ids

    def test_discover_projects_sorted(self, temp_hive_dir, temp_project, temp_blocked_project):
        """Test that projects are sorted by project_id."""
        base_path = Path(temp_hive_dir)

        with patch("streamlit.error"):
            projects = discover_projects(base_path)

            assert len(projects) == 2
            # Should be sorted: blocked-project comes before test-project
            assert projects[0]["metadata"]["project_id"] == "blocked-project"
            assert projects[1]["metadata"]["project_id"] == "test-project"

    def test_discover_no_projects_dir(self, temp_hive_dir):
        """Test discovering projects when directory doesn't exist."""
        base_path = Path(temp_hive_dir)
        # Remove projects directory
        projects_dir = base_path / "projects"
        shutil.rmtree(projects_dir)

        with patch("streamlit.error"):
            projects = discover_projects(base_path)

            assert len(projects) == 0

    def test_discover_empty_projects_dir(self, temp_hive_dir):
        """Test discovering projects in an empty directory."""
        base_path = Path(temp_hive_dir)

        with patch("streamlit.error"):
            projects = discover_projects(base_path)

            # No projects created yet
            assert len(projects) == 0


class TestGenerateFileTree:
    """Test file tree generation."""

    def test_generate_file_tree_simple(self, temp_hive_dir, temp_project):
        """Test generating a file tree for a simple project."""
        project_dir = Path(temp_project).parent

        tree = generate_file_tree(project_dir)

        assert tree is not None
        assert "AGENCY.md" in tree
        assert "sample.py" in tree
        assert "├──" in tree or "└──" in tree

    def test_generate_file_tree_with_depth(self, temp_hive_dir):
        """Test file tree respects max depth."""
        # Create nested directory structure
        deep_dir = Path(temp_hive_dir) / "level1" / "level2" / "level3" / "level4"
        deep_dir.mkdir(parents=True)
        (deep_dir / "deep_file.txt").write_text("deep content")

        tree = generate_file_tree(Path(temp_hive_dir), max_depth=2)

        assert "level1" in tree
        # Should not go beyond max_depth
        assert "level4" not in tree

    def test_generate_file_tree_ignores_hidden_files(self, temp_hive_dir):
        """Test that hidden files and __pycache__ are ignored."""
        test_dir = Path(temp_hive_dir) / "test"
        test_dir.mkdir()

        # Create hidden file and __pycache__
        (test_dir / ".hidden").write_text("hidden")
        (test_dir / "__pycache__").mkdir()
        (test_dir / "visible.py").write_text("visible")

        tree = generate_file_tree(test_dir)

        assert "visible.py" in tree
        assert ".hidden" not in tree
        assert "__pycache__" not in tree

    def test_generate_file_tree_empty_directory(self, temp_hive_dir):
        """Test file tree for empty directory."""
        empty_dir = Path(temp_hive_dir) / "empty"
        empty_dir.mkdir()

        tree = generate_file_tree(empty_dir)

        # Should return empty string for empty directory
        assert tree == ""

    def test_generate_file_tree_sorts_directories_first(self, temp_hive_dir):
        """Test that directories appear before files."""
        test_dir = Path(temp_hive_dir) / "test"
        test_dir.mkdir()

        # Create files and directories
        (test_dir / "z_file.txt").write_text("file")
        (test_dir / "a_dir").mkdir()
        (test_dir / "m_file.txt").write_text("file")

        tree = generate_file_tree(test_dir)

        # Directories should come before files
        dir_index = tree.find("a_dir")
        file_index = tree.find("m_file.txt")
        assert dir_index < file_index


class TestGenerateDeepWorkContext:
    """Test Deep Work context generation."""

    def test_generate_context_success(self, temp_hive_dir, temp_project):
        """Test successfully generating Deep Work context."""
        base_path = Path(temp_hive_dir)

        context = generate_deep_work_context(temp_project, base_path)

        assert context is not None
        assert "DEEP WORK SESSION CONTEXT" in context
        assert "test-project" in context
        assert "YOUR ROLE" in context
        assert "AGENCY.md CONTENT" in context
        assert "PROJECT FILE STRUCTURE" in context
        assert "HANDOFF PROTOCOL" in context

    def test_generate_context_includes_metadata(self, temp_hive_dir, temp_project):
        """Test that context includes project metadata."""
        base_path = Path(temp_hive_dir)

        context = generate_deep_work_context(temp_project, base_path)

        assert "project_id: test-project" in context
        assert "status: active" in context
        assert "priority: high" in context

    def test_generate_context_includes_tasks(self, temp_hive_dir, temp_project):
        """Test that context includes task list."""
        base_path = Path(temp_hive_dir)

        context = generate_deep_work_context(temp_project, base_path)

        assert "Task 1" in context
        assert "Task 2" in context
        assert "Completed task" in context

    def test_generate_context_includes_file_tree(self, temp_hive_dir, temp_project):
        """Test that context includes file tree."""
        base_path = Path(temp_hive_dir)

        context = generate_deep_work_context(temp_project, base_path)

        assert "AGENCY.md" in context
        assert "sample.py" in context

    def test_generate_context_includes_handoff_protocol(self, temp_hive_dir, temp_project):
        """Test that context includes handoff protocol."""
        base_path = Path(temp_hive_dir)

        context = generate_deep_work_context(temp_project, base_path)

        assert "HANDOFF PROTOCOL" in context
        assert "Update all completed tasks" in context
        assert "last_updated" in context
        assert "owner: null" in context

    def test_generate_context_includes_timestamp(self, temp_hive_dir, temp_project):
        """Test that context includes generation timestamp."""
        base_path = Path(temp_hive_dir)

        context = generate_deep_work_context(temp_project, base_path)

        assert "Generated:" in context
        # Check for ISO timestamp format (YYYY-MM-DDTHH:MM:SS)
        iso_pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
        assert re.search(iso_pattern, context), "Should contain ISO format timestamp"

    def test_generate_context_nonexistent_project(self, temp_hive_dir):
        """Test generating context for non-existent project."""
        base_path = Path(temp_hive_dir)

        with patch("streamlit.error"):
            context = generate_deep_work_context(
                str(base_path / "nonexistent" / "AGENCY.md"), base_path
            )

            assert context is None

    def test_generate_context_includes_responsibilities(self, temp_hive_dir, temp_project):
        """Test that context includes agent responsibilities."""
        base_path = Path(temp_hive_dir)

        context = generate_deep_work_context(temp_project, base_path)

        assert "YOUR ROLE" in context
        assert "responsibilities:" in context.lower()
        assert "Read and understand" in context
        assert "Work on the assigned tasks" in context
        assert "blocked: true" in context


class TestDashboardIntegration:
    """Integration tests for dashboard functionality."""

    def test_full_workflow(self, temp_hive_dir, temp_project):
        """Test complete workflow: discover -> load -> generate context."""
        base_path = Path(temp_hive_dir)

        with patch("streamlit.error"):
            # 1. Discover projects
            projects = discover_projects(base_path)
            assert len(projects) == 1

            # 2. Load the project
            project_path = projects[0]["path"]
            project_data = load_project(project_path)
            assert project_data is not None

            # 3. Generate Deep Work context
            context = generate_deep_work_context(project_path, base_path)
            assert context is not None
            assert "test-project" in context

    def test_multiple_projects_workflow(self, temp_hive_dir, temp_project, temp_blocked_project):
        """Test workflow with multiple projects."""
        base_path = Path(temp_hive_dir)

        with patch("streamlit.error"):
            # Discover all projects
            projects = discover_projects(base_path)
            assert len(projects) == 2

            # Generate context for each
            for project in projects:
                context = generate_deep_work_context(project["path"], base_path)
                assert context is not None
                assert project["metadata"]["project_id"] in context

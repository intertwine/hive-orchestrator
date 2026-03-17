"""Tests for the Dashboard UI functions."""

# pylint: disable=unused-argument,unused-import,import-error,wrong-import-position

import sys
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import dashboard as dashboard_module

from dashboard import (
    build_home_view,
    build_inbox,
    discover_projects,
    generate_deep_work_context,
    generate_file_tree,
    generate_hive_context,
    list_project_ready_tasks,
    list_runs,
    load_project,
    load_run_detail,
    load_run_timeline,
    main as dashboard_main,
)
from hive.cli.main import main as hive_main
from src.hive.migrate import migrate_v1_to_v2
from src.hive.runs.engine import eval_run, start_run
from src.hive.scheduler.query import ready_tasks
from src.hive.store.task_files import create_task
from tests.conftest import init_git_repo, write_safe_program


def _invoke_cli(capsys, argv: list[str]) -> None:
    exit_code = hive_main(argv)
    captured = capsys.readouterr()
    assert exit_code == 0, captured.err


def _bootstrap_observe_workspace(temp_hive_dir: str, capsys) -> tuple[object, object]:
    """Create one awaiting-input run and one reviewable run for dashboard shim tests."""
    init_git_repo(temp_hive_dir)
    _invoke_cli(
        capsys,
        ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
    )
    write_safe_program(temp_hive_dir, "demo")
    create_task(temp_hive_dir, "demo", "Review-ready slice", status="ready", priority=1)
    subprocess.run(["git", "add", "-A"], cwd=temp_hive_dir, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Bootstrap workspace"],
        cwd=temp_hive_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
    waiting_run = start_run(temp_hive_dir, task_id, driver_name="codex")
    review_task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
    review_run = start_run(temp_hive_dir, review_task_id, driver_name="local")
    eval_run(temp_hive_dir, review_run.id)
    return waiting_run, review_run


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
        project_data = load_project("/nonexistent/path/AGENCY.md")
        assert project_data is None

    def test_load_project_malformed(self, temp_hive_dir):
        """Test loading a malformed AGENCY.md."""
        # Create malformed file (frontmatter is lenient and will parse this)
        project_dir = Path(temp_hive_dir) / "projects" / "malformed"
        project_dir.mkdir(parents=True)
        agency_file = project_dir / "AGENCY.md"
        agency_file.write_text("This is not valid frontmatter")

        project_data = load_project(str(agency_file))
        # frontmatter library is lenient - files without --- delimiters parse successfully
        assert project_data is not None

    def test_load_project_contains_raw_content(self, temp_project):
        """Test that loaded project contains raw frontmatter."""
        project_data = load_project(temp_project)

        assert project_data is not None
        assert "---" in project_data["raw"]
        assert "project_id: test-project" in project_data["raw"]

    def test_load_project_propagates_unexpected_errors(self):
        """Unexpected loader failures should surface instead of being silently swallowed."""
        with patch.object(dashboard_module, "safe_load_agency_md", side_effect=RuntimeError("boom")):
            with pytest.raises(RuntimeError, match="boom"):
                load_project("/tmp/example/AGENCY.md")


class TestDiscoverProjects:
    """Test discovering projects in the projects directory."""

    def test_discover_single_project(self, temp_hive_dir, temp_project):
        """Test discovering a single project."""
        base_path = Path(temp_hive_dir)

        projects = discover_projects(base_path)

        assert len(projects) == 1
        assert projects[0]["metadata"]["project_id"] == "test-project"

    def test_discover_multiple_projects(self, temp_hive_dir, temp_project, temp_blocked_project):
        """Test discovering multiple projects."""
        base_path = Path(temp_hive_dir)

        projects = discover_projects(base_path)

        assert len(projects) == 2
        project_ids = [p["metadata"]["project_id"] for p in projects]
        assert "test-project" in project_ids
        assert "blocked-project" in project_ids

    def test_discover_projects_sorted(self, temp_hive_dir, temp_project, temp_blocked_project):
        """Test that projects are sorted by project_id."""
        base_path = Path(temp_hive_dir)

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

        projects = discover_projects(base_path)

        assert len(projects) == 0

    def test_discover_empty_projects_dir(self, temp_hive_dir):
        """Test discovering projects in an empty directory."""
        base_path = Path(temp_hive_dir)

        projects = discover_projects(base_path)

        # No projects created yet
        assert len(projects) == 0

    def test_discover_nested_projects(self, temp_hive_dir):
        """Test discovering projects in nested directories (e.g., projects/external/foo)."""
        base_path = Path(temp_hive_dir)
        projects_dir = base_path / "projects"

        # Create a nested project at projects/external/nested-project/AGENCY.md
        nested_dir = projects_dir / "external" / "nested-project"
        nested_dir.mkdir(parents=True)
        nested_agency = nested_dir / "AGENCY.md"
        nested_agency.write_text(
            """---
project_id: nested-project
status: active
owner: null
priority: high
tags:
  - external
---

# Nested Project

A project in a nested directory.
"""
        )

        # Also create a regular project
        regular_dir = projects_dir / "regular-project"
        regular_dir.mkdir(parents=True)
        regular_agency = regular_dir / "AGENCY.md"
        regular_agency.write_text(
            """---
project_id: regular-project
status: active
owner: null
priority: medium
---

# Regular Project
"""
        )

        projects = discover_projects(base_path)

        # Should find both projects
        assert len(projects) == 2
        project_ids = [p["metadata"]["project_id"] for p in projects]
        assert "nested-project" in project_ids
        assert "regular-project" in project_ids


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
        migrate_v1_to_v2(temp_hive_dir)

        context = generate_deep_work_context(temp_project, base_path)

        assert context is not None
        assert "HIVE STARTUP CONTEXT" in context
        assert "test-project" in context
        assert "YOUR ROLE" in context
        assert "READY TASKS" in context
        assert "AGENCY.md" in context
        assert "HIVE CONTEXT" in context
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
        migrate_v1_to_v2(temp_hive_dir)

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
        assert ".hive/tasks/" in context
        assert "hive sync projections" in context

    def test_generate_context_includes_timestamp(self, temp_hive_dir, temp_project):
        """Test that context includes generation timestamp with Z suffix."""
        base_path = Path(temp_hive_dir)

        context = generate_deep_work_context(temp_project, base_path)

        assert "Generated:" in context
        # Check for ISO timestamp format (YYYY-MM-DDTHH:MM:SS) with Z suffix for UTC
        iso_pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.*Z"
        assert re.search(iso_pattern, context), "Should contain ISO format timestamp with Z suffix"

        # Extract the timestamp line and verify it ends with Z
        lines = context.split("\n")
        generated_line = [line for line in lines if line.startswith("# Generated:")][0]
        timestamp_str = generated_line.replace("# Generated:", "").strip()
        assert timestamp_str.endswith(
            "Z"
        ), f"Timestamp should end with 'Z' for UTC. Got: {timestamp_str}"

    def test_generate_context_nonexistent_project(self, temp_hive_dir):
        """Test generating context for non-existent project."""
        base_path = Path(temp_hive_dir)

        context = generate_deep_work_context(str(base_path / "nonexistent" / "AGENCY.md"), base_path)

        assert context is None

    def test_generate_context_includes_responsibilities(self, temp_hive_dir, temp_project):
        """Test that context includes agent responsibilities."""
        base_path = Path(temp_hive_dir)

        context = generate_deep_work_context(temp_project, base_path)

        assert "YOUR ROLE" in context
        assert "canonical tasks" in context
        assert "source of truth" in context

    def test_generate_handoff_context(self, temp_hive_dir, temp_project):
        """Test generating the explicit handoff context variant."""
        base_path = Path(temp_hive_dir)
        migrate_v1_to_v2(temp_hive_dir)

        context = generate_hive_context(temp_project, base_path, mode="handoff", profile="light")

        assert context is not None
        assert "HIVE HANDOFF CONTEXT" in context

    def test_list_project_ready_tasks_returns_canonical_queue(self, temp_hive_dir, temp_project):
        """Ready task helper should read the canonical `.hive/tasks` queue."""
        migrate_v1_to_v2(temp_hive_dir)

        tasks = list_project_ready_tasks(Path(temp_hive_dir), "test-project", limit=10)

        titles = [task["title"] for task in tasks]
        assert "Task 1" in titles
        assert "Task 2" in titles


class TestDashboardIntegration:
    """Integration tests for dashboard functionality."""

    def test_full_workflow(self, temp_hive_dir, temp_project):
        """Test complete workflow: discover -> load -> generate context."""
        base_path = Path(temp_hive_dir)
        migrate_v1_to_v2(temp_hive_dir)

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
        migrate_v1_to_v2(temp_hive_dir)

        # Discover all projects
        projects = discover_projects(base_path)
        assert len(projects) == 2

        # Generate context for each
        for project in projects:
            context = generate_deep_work_context(project["path"], base_path)
            assert context is not None
            assert project["metadata"]["project_id"] in context
class TestConsoleShimHelpers:
    """Compatibility wrappers should delegate cleanly to the React console state layer."""

    def test_console_shim_helpers_cover_run_and_inbox_views(self, temp_hive_dir, capsys):
        waiting_run, review_run = _bootstrap_observe_workspace(temp_hive_dir, capsys)
        base_path = Path(temp_hive_dir)

        runs = list_runs(base_path, driver="codex")
        timeline = load_run_timeline(base_path, waiting_run.id)
        inbox = build_inbox(base_path)
        home = build_home_view(base_path)
        detail = load_run_detail(base_path, waiting_run.id)
        review_detail = load_run_detail(base_path, review_run.id)

        assert len(runs) == 1
        assert runs[0]["id"] == waiting_run.id
        assert timeline
        assert any(item["kind"] == "run-input" for item in inbox)
        assert any(item["kind"] == "run-review" for item in inbox)
        assert home["active_runs"]
        assert home["inbox"]
        assert detail["run"]["id"] == waiting_run.id
        assert detail["timeline"]
        assert detail["artifacts"]["context_manifest"]
        assert review_detail["promotion_decision"]["decision"] == "accept"

    def test_main_exits_with_console_advice(self, temp_hive_dir):
        with patch.dict(os.environ, {"HIVE_BASE_PATH": temp_hive_dir}):
            with pytest.raises(SystemExit) as excinfo:
                dashboard_main()

        message = str(excinfo.value)
        assert "hive console serve" in message
        assert "--path" not in message
        assert str(Path(temp_hive_dir).resolve()) in message

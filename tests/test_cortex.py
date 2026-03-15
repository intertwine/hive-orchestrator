"""Tests for the Hive v2 Cortex compatibility wrapper."""

# pylint: disable=unused-argument,import-error,wrong-import-position

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cortex import Cortex, main, run_v2_projection_sync
from src.hive.migrate import migrate_v1_to_v2
from src.security import safe_load_agency_md


class TestCortexInitialization:
    """Initialization and basic filesystem attributes."""

    def test_init_with_default_path(self):
        """Default initialization uses the current working directory."""
        cortex = Cortex()
        assert cortex.base_path == Path(os.getcwd())
        assert cortex.global_file == Path(os.getcwd()) / "GLOBAL.md"
        assert cortex.projects_dir == Path(os.getcwd()) / "projects"

    def test_init_with_custom_path(self, temp_hive_dir):
        """Custom initialization stores the provided base path."""
        cortex = Cortex(temp_hive_dir)
        assert cortex.base_path == Path(temp_hive_dir)
        assert cortex.global_file == Path(temp_hive_dir) / "GLOBAL.md"
        assert cortex.projects_dir == Path(temp_hive_dir) / "projects"


class TestGlobalContext:
    """Tests for GLOBAL.md compatibility helpers."""

    def test_read_global_context_success(self, temp_hive_dir):
        """GLOBAL.md is returned as metadata/content/path."""
        cortex = Cortex(temp_hive_dir)
        global_ctx = cortex.read_global_context()

        assert global_ctx is not None
        assert global_ctx["metadata"]["status"] == "active"
        assert global_ctx["path"] == str(Path(temp_hive_dir) / "GLOBAL.md")

    def test_read_global_context_missing_file(self, temp_hive_dir):
        """Missing GLOBAL.md returns None."""
        (Path(temp_hive_dir) / "GLOBAL.md").unlink()
        cortex = Cortex(temp_hive_dir)

        assert cortex.read_global_context() is None

    def test_read_global_context_malformed_file(self, temp_hive_dir):
        """Malformed GLOBAL.md content falls back to plain markdown safely."""
        (Path(temp_hive_dir) / "GLOBAL.md").write_text(":\nnot yaml", encoding="utf-8")
        cortex = Cortex(temp_hive_dir)

        global_ctx = cortex.read_global_context()
        assert global_ctx is not None
        assert global_ctx["metadata"] == {}
        assert "not yaml" in global_ctx["content"]


class TestProjectAndTaskQueries:
    """Tests for project and ready-work compatibility methods."""

    def test_discover_projects_returns_legacy_dict_shape(self, temp_hive_dir, temp_project):
        """discover_projects exposes project metadata in the old dict shape."""
        cortex = Cortex(temp_hive_dir)

        projects = cortex.discover_projects()

        assert len(projects) == 1
        assert projects[0]["project_id"] == "test-project"
        assert projects[0]["metadata"]["priority"] == "high"
        assert "Task 1" in projects[0]["content"]

    def test_ready_work_returns_canonical_ready_tasks(self, temp_hive_dir, temp_project):
        """ready_work proxies the v2 ready queue after migration."""
        migrate_v1_to_v2(temp_hive_dir)
        cortex = Cortex(temp_hive_dir)

        ready = cortex.ready_work()

        assert ready
        assert ready[0]["project_id"] == "test-project"
        assert ready[0]["id"].startswith("task_")

    def test_get_dependency_summary(self, temp_hive_dir, temp_project_with_dependency):
        """Dependency summary comes from the v2 scheduler layer."""
        cortex = Cortex(temp_hive_dir)

        summary = cortex.get_dependency_summary()

        assert summary["total_projects"] == 1
        assert summary["projects"][0]["project_id"] == "dependent-project"

    def test_is_blocked_reports_dependencies(
        self, temp_hive_dir, temp_project_with_dependency, temp_prereq_project_incomplete
    ):
        """Blocked project status is exposed in the compatibility shape."""
        cortex = Cortex(temp_hive_dir)

        blocking = cortex.is_blocked("dependent-project")

        assert blocking["is_blocked"] is True
        assert "prereq-project" in blocking["blocking_projects"]

    def test_is_blocked_returns_unblocked_for_missing_project(self, temp_hive_dir, temp_project):
        """Unknown projects return an unblocked placeholder instead of raising."""
        cortex = Cortex(temp_hive_dir)

        blocking = cortex.is_blocked("missing-project")

        assert blocking["project_id"] == "missing-project"
        assert blocking["is_blocked"] is False
        assert blocking["blocking_projects"] == []


class TestReadyFormatting:
    """Formatting and printing ready-task output."""

    def test_format_ready_work_json(self, temp_hive_dir, temp_project):
        """Ready-task JSON includes versioned task payload."""
        migrate_v1_to_v2(temp_hive_dir)
        cortex = Cortex(temp_hive_dir)

        payload = json.loads(cortex.format_ready_work_json(cortex.ready_work()))

        assert payload["version"] == "2.0"
        assert payload["tasks"]

    def test_format_ready_work_text(self, temp_hive_dir, temp_project):
        """Ready-task text output is human readable."""
        migrate_v1_to_v2(temp_hive_dir)
        cortex = Cortex(temp_hive_dir)

        output = cortex.format_ready_work_text(cortex.ready_work())

        assert "READY TASKS (Hive v2)" in output
        assert "test-project" in output

    def test_run_ready_json(self, temp_hive_dir, temp_project, capsys):
        """run_ready prints JSON when requested."""
        migrate_v1_to_v2(temp_hive_dir)
        cortex = Cortex(temp_hive_dir)

        result = cortex.run_ready(output_json=True)

        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        assert result is True
        assert payload["version"] == "2.0"

    def test_run_ready_text(self, temp_hive_dir, temp_project, capsys):
        """run_ready prints text by default."""
        migrate_v1_to_v2(temp_hive_dir)
        cortex = Cortex(temp_hive_dir)

        result = cortex.run_ready(output_json=False)

        captured = capsys.readouterr()
        assert result is True
        assert "READY TASKS (Hive v2)" in captured.out


class TestDependencyFormatting:
    """Formatting and printing dependency summaries."""

    def test_format_deps_json(self, temp_hive_dir, temp_project_with_dependency):
        """Dependency JSON includes version and project list."""
        cortex = Cortex(temp_hive_dir)

        payload = json.loads(cortex.format_deps_json(cortex.get_dependency_summary()))

        assert payload["version"] == "2.0"
        assert payload["projects"]

    def test_format_deps_text(self, temp_hive_dir, temp_project_with_dependency):
        """Dependency text output is human readable."""
        cortex = Cortex(temp_hive_dir)

        output = cortex.format_deps_text(cortex.get_dependency_summary())

        assert "TASK DEPENDENCY SUMMARY (Hive v2)" in output
        assert "dependent-project" in output

    def test_run_deps_json(self, temp_hive_dir, temp_project_with_dependency, capsys):
        """run_deps prints JSON when requested."""
        cortex = Cortex(temp_hive_dir)

        result = cortex.run_deps(output_json=True)

        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        assert result is True
        assert payload["version"] == "2.0"

    def test_run_deps_text(self, temp_hive_dir, temp_project_with_dependency, capsys):
        """run_deps prints text by default."""
        cortex = Cortex(temp_hive_dir)

        result = cortex.run_deps(output_json=False)

        captured = capsys.readouterr()
        assert result is True
        assert "TASK DEPENDENCY SUMMARY (Hive v2)" in captured.out


class TestProjectionSync:
    """Projection sync helpers and CLI behavior."""

    def test_run_projection_sync_updates_global_metadata(self, temp_hive_dir, temp_project):
        """Projection sync refreshes compatibility timestamps in GLOBAL.md."""
        migrate_v1_to_v2(temp_hive_dir)

        result = run_v2_projection_sync(temp_hive_dir, output_json=False)

        post = safe_load_agency_md(Path(temp_hive_dir) / "GLOBAL.md")
        assert result is True
        assert post.metadata["last_cortex_run"] is not None
        assert post.metadata["last_sync"] is not None

    def test_run_projection_sync_tolerates_malformed_global_metadata(
        self, temp_hive_dir, temp_project, capsys
    ):
        """Malformed GLOBAL.md frontmatter should not abort projection sync."""
        migrate_v1_to_v2(temp_hive_dir)
        (Path(temp_hive_dir) / "GLOBAL.md").write_text(
            "---\nstatus: [\n---\n# Broken Global\n",
            encoding="utf-8",
        )

        result = run_v2_projection_sync(temp_hive_dir, output_json=False)

        captured = capsys.readouterr()
        assert result is True
        assert "Warning: skipping GLOBAL.md timestamp refresh" in captured.err
        assert "<!-- hive:begin projects -->" in (Path(temp_hive_dir) / "GLOBAL.md").read_text(
            encoding="utf-8"
        )

    def test_cortex_run_uses_projection_sync(self, temp_hive_dir, temp_project):
        """Cortex.run now delegates to the v2 projection sync."""
        migrate_v1_to_v2(temp_hive_dir)
        cortex = Cortex(temp_hive_dir)

        assert cortex.run() is True

    def test_main_defaults_to_projection_sync_text(
        self, temp_hive_dir, temp_project, monkeypatch, capsys
    ):
        """The default CLI behavior is projection sync text output."""
        migrate_v1_to_v2(temp_hive_dir)
        monkeypatch.setattr(sys, "argv", ["cortex.py", "--path", temp_hive_dir])

        with pytest.raises(SystemExit) as excinfo:
            main()

        captured = capsys.readouterr()
        assert excinfo.value.code == 0
        assert "HIVE V2 PROJECTION SYNC" in captured.out

    def test_main_defaults_to_projection_sync_json(
        self, temp_hive_dir, temp_project, monkeypatch, capsys
    ):
        """The default CLI behavior supports JSON output."""
        migrate_v1_to_v2(temp_hive_dir)
        monkeypatch.setattr(sys, "argv", ["cortex.py", "--path", temp_hive_dir, "--json"])

        with pytest.raises(SystemExit) as excinfo:
            main()

        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        assert excinfo.value.code == 0
        assert payload["action"] == "projection_sync"
        assert payload["version"] == "2.0"

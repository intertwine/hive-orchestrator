"""Tests for run worktree helpers."""

from __future__ import annotations

from pathlib import Path
import pytest

from src.hive.migrate import migrate_v1_to_v2
from src.hive.runs.worktree import ensure_clean_repo


class TestRunWorktree:
    """Tests for git-worktree guardrails."""

    def test_ensure_clean_repo_allows_dirty_canonical_hive_state(
        self, temp_hive_dir, temp_project, commit_workspace
    ):
        """Dirty canonical Hive state should not block run scaffolding."""
        del temp_project
        migrate_v1_to_v2(temp_hive_dir)
        commit_workspace(temp_hive_dir, "baseline")
        task_file = next((Path(temp_hive_dir) / ".hive" / "tasks").glob("task_*.md"))
        task_file.write_text(task_file.read_text(encoding="utf-8") + "\n", encoding="utf-8")

        ensure_clean_repo(temp_hive_dir)

    def test_ensure_clean_repo_allows_dirty_run_artifacts(
        self, temp_hive_dir, temp_project, commit_workspace
    ):
        """Dirty run metadata should not block subsequent run scaffolding."""
        del temp_project
        migrate_v1_to_v2(temp_hive_dir)
        commit_workspace(temp_hive_dir, "baseline")
        run_metadata = Path(temp_hive_dir) / ".hive" / "runs" / "run_test" / "metadata.json"
        run_metadata.parent.mkdir(parents=True, exist_ok=True)
        run_metadata.write_text('{"id": "run_test"}\n', encoding="utf-8")

        ensure_clean_repo(temp_hive_dir)

    def test_ensure_clean_repo_rejects_dirty_noncanonical_paths(
        self, temp_hive_dir, temp_project, commit_workspace
    ):
        """Dirty source files should still block run scaffolding."""
        del temp_project
        migrate_v1_to_v2(temp_hive_dir)
        commit_workspace(temp_hive_dir, "baseline")
        source_path = Path(temp_hive_dir) / "src" / "dirty.py"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text("print('dirty')\n", encoding="utf-8")

        with pytest.raises(ValueError, match="Dirty paths"):
            ensure_clean_repo(temp_hive_dir)

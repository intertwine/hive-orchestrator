"""Tests for run worktree helpers."""

# pylint: disable=protected-access,duplicate-code

from __future__ import annotations

from pathlib import Path
import subprocess
import pytest

from src.hive.migrate import migrate_v1_to_v2
from src.hive.runs import worktree as worktree_module
from src.hive.runs.worktree import (
    create_checkpoint_commit,
    ensure_clean_repo,
    remove_worktree,
    split_dirty_paths,
)


class TestRunWorktree:
    """Tests for git-worktree guardrails."""

    def test_ensure_clean_repo_requires_initial_commit(self, temp_hive_dir, temp_project):
        """Fresh Git repos should guide users toward making an initial commit first."""
        del temp_project
        subprocess.run(["git", "init", "-q"], cwd=temp_hive_dir, check=True)

        with pytest.raises(ValueError, match="initial Git commit"):
            ensure_clean_repo(temp_hive_dir)

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

    def test_ensure_clean_repo_allows_dirty_worktree_artifacts(
        self, temp_hive_dir, temp_project, commit_workspace
    ):
        """Dirty worktree directories should not block subsequent run scaffolding."""
        del temp_project
        migrate_v1_to_v2(temp_hive_dir)
        commit_workspace(temp_hive_dir, "baseline")
        worktree_marker = Path(temp_hive_dir) / ".hive" / "worktrees" / "run_test" / ".git"
        worktree_marker.parent.mkdir(parents=True, exist_ok=True)
        worktree_marker.write_text("gitdir: /tmp/run_test\n", encoding="utf-8")

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

    def test_split_dirty_paths_separates_canonical_and_noncanonical(
        self, temp_hive_dir, temp_project, commit_workspace
    ):
        """Dirty-path classification should distinguish Hive state from source edits."""
        del temp_project
        migrate_v1_to_v2(temp_hive_dir)
        commit_workspace(temp_hive_dir, "baseline")
        task_file = next((Path(temp_hive_dir) / ".hive" / "tasks").glob("task_*.md"))
        task_file.write_text(task_file.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        source_path = Path(temp_hive_dir) / "src" / "dirty.py"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text("print('dirty')\n", encoding="utf-8")

        dirty = split_dirty_paths(temp_hive_dir)

        assert any(path.startswith(".hive/tasks/") for path in dirty["canonical"])
        assert dirty["noncanonical"] == ["src/dirty.py"]

    def test_split_dirty_paths_ignores_derived_cache_files(
        self, temp_hive_dir, temp_project, commit_workspace
    ):
        """Derived cache files should not block promotion or run startup decisions."""
        del temp_project
        migrate_v1_to_v2(temp_hive_dir)
        commit_workspace(temp_hive_dir, "baseline")
        cache_file = Path(temp_hive_dir) / ".hive" / "cache" / "index.sqlite"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text("derived-cache\n", encoding="utf-8")

        dirty = split_dirty_paths(temp_hive_dir)

        assert dirty["canonical"] == []
        assert dirty["noncanonical"] == []

    def test_split_dirty_paths_ignores_local_worktree_directories(
        self, temp_hive_dir, temp_project, commit_workspace
    ):
        """Linked worktree directories should behave like local machinery, not tracked state."""
        del temp_project
        migrate_v1_to_v2(temp_hive_dir)
        commit_workspace(temp_hive_dir, "baseline")
        worktree_marker = Path(temp_hive_dir) / ".hive" / "worktrees" / "run_test" / ".git"
        worktree_marker.parent.mkdir(parents=True, exist_ok=True)
        worktree_marker.write_text("gitdir: /tmp/run_test\n", encoding="utf-8")

        dirty = split_dirty_paths(temp_hive_dir)

        assert dirty["canonical"] == []
        assert dirty["noncanonical"] == []

    def test_create_checkpoint_commit_records_bootstrap_snapshot(self, temp_hive_dir):
        """Checkpoint commits should stage and commit the current workspace state."""
        subprocess.run(["git", "init", "-q"], cwd=temp_hive_dir, check=True)
        subprocess.run(
            ["git", "config", "user.email", "tests@example.com"], cwd=temp_hive_dir, check=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Agent Hive Tests"], cwd=temp_hive_dir, check=True
        )
        Path(temp_hive_dir, "README.md").write_text("# Demo\n", encoding="utf-8")

        payload = create_checkpoint_commit(temp_hive_dir, message="Bootstrap workspace")

        assert payload["committed"] is True
        assert payload["commit"]
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=temp_hive_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        assert payload["commit"] == head.stdout.strip()

    def test_remove_worktree_reports_manual_cleanup_fallback(self, temp_hive_dir, monkeypatch):
        """Worktree cleanup should report when it falls back to filesystem deletion."""
        subprocess.run(["git", "init", "-q"], cwd=temp_hive_dir, check=True)
        worktree_path = Path(temp_hive_dir) / ".hive" / "worktrees" / "run_test"
        worktree_path.mkdir(parents=True, exist_ok=True)
        original_run_git = worktree_module._run_git

        def fake_run_git(repo_root, *args, **kwargs):
            if args[:3] == ("worktree", "remove", "--force"):
                return subprocess.CompletedProcess(["git", *args], 1, "", "worktree locked")
            if args[:2] == ("worktree", "prune"):
                return subprocess.CompletedProcess(["git", *args], 0, "", "")
            return original_run_git(repo_root, *args, **kwargs)

        monkeypatch.setattr(worktree_module, "_run_git", fake_run_git)

        result = remove_worktree(temp_hive_dir, worktree_path)

        assert result["removed"] is True
        assert result["manual_cleanup"] is True
        assert result["warnings"]

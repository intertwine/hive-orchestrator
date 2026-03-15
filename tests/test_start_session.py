"""Tests for the Hive v2 session bootstrap script."""

import os
import subprocess
from pathlib import Path

from src.hive.migrate import migrate_v1_to_v2
from src.hive.scheduler.query import ready_tasks


def test_start_session_script_generates_v2_context(temp_hive_dir, temp_project):
    """The bootstrap script should emit the new Hive v2 startup context."""
    migrate_v1_to_v2(temp_hive_dir)
    first_task_title = ready_tasks(temp_hive_dir, project_id="test-project", limit=1)[0]["title"]
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / "start_session.sh"
    session_file = Path(temp_hive_dir) / "projects" / "test-project" / "SESSION_CONTEXT.md"

    env = dict(os.environ)
    env["HIVE_BASE_PATH"] = temp_hive_dir
    result = subprocess.run(
        ["/bin/bash", str(script_path), "test-project"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert session_file.exists()
    content = session_file.read_text(encoding="utf-8")
    assert "HIVE STARTUP CONTEXT" in content
    assert "READY TASKS" in content
    assert first_task_title in content


def test_start_session_script_still_accepts_project_paths(temp_hive_dir, temp_project):
    """The bootstrap script should keep supporting project directory paths."""
    migrate_v1_to_v2(temp_hive_dir)
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / "start_session.sh"

    env = dict(os.environ)
    env["HIVE_BASE_PATH"] = temp_hive_dir
    result = subprocess.run(
        ["/bin/bash", str(script_path), "projects/test-project"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout


def test_start_session_script_hides_python_traceback_for_missing_project(temp_hive_dir):
    """Missing projects should return a clean shell error without Python noise."""
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / "start_session.sh"

    env = dict(os.environ)
    env["HIVE_BASE_PATH"] = temp_hive_dir
    result = subprocess.run(
        ["/bin/bash", str(script_path), "missing-project"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    combined_output = f"{result.stdout}\n{result.stderr}"

    assert result.returncode == 1
    assert "Could not resolve project 'missing-project'" in combined_output
    assert "Traceback" not in combined_output
    assert "PROJECT_LOOKUP_ERROR:" not in combined_output

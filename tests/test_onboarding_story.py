"""Regression tests for the checked-in onboarding story."""

# pylint: disable=cyclic-import,duplicate-code

from __future__ import annotations

from pathlib import Path
import subprocess

from src.hive.store.task_files import list_tasks


REPO_ROOT = Path(__file__).resolve().parents[1]


def _head_snapshot(tmp_path: Path, *relative_paths: str) -> Path:
    """Materialize committed files into a temp workspace without touching local state."""
    snapshot_root = tmp_path / "head-snapshot"
    for relative_path in relative_paths:
        target = snapshot_root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        content = subprocess.run(
            ["git", "show", f"HEAD:{relative_path}"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        target.write_text(content, encoding="utf-8")
    return snapshot_root


def test_demo_project_uses_the_checked_in_three_step_onboarding_chain(tmp_path):
    """The repo demo should stay aligned with the real quickstart story."""
    task_paths = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "HEAD", ".hive/tasks"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    snapshot_root = _head_snapshot(tmp_path, *task_paths)
    demo_tasks = sorted(
        [task for task in list_tasks(snapshot_root) if task.project_id == "demo"],
        key=lambda task: (task.priority, task.title.lower()),
    )

    assert [task.title for task in demo_tasks] == [
        "Claim the first demo task and capture startup context",
        "Make one small docs-only improvement in the demo project",
        "Sync projections, record the result, and leave a clean handoff",
    ]
    assert [task.status for task in demo_tasks] == ["ready", "proposed", "proposed"]
    assert demo_tasks[0].edges["blocks"] == [demo_tasks[1].id]
    assert demo_tasks[1].edges["blocks"] == [demo_tasks[2].id]
    assert all(not values for values in demo_tasks[2].edges.values())


def test_onboarding_docs_keep_everyday_user_flow_task_specific():
    """The main docs should keep the installed-user and maintainer paths distinct."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    quickstart = (REPO_ROOT / "docs" / "QUICKSTART.md").read_text(encoding="utf-8")
    demo_agency = (REPO_ROOT / "projects" / "demo" / "AGENCY.md").read_text(encoding="utf-8")

    assert "## Start Here" in readme
    assert "[Install Hive](docs/START_HERE.md)" in readme
    assert "## Adopt Hive In An Existing Repo" in readme
    assert "## Maintainers" in readme
    assert "Do this in a fresh workspace, not inside this repository checkout." in readme
    assert "hive next --project-id demo" in readme
    assert "hive onboard demo" in readme
    assert "hive console serve" in readme
    assert "[docs/MAINTAINING.md](docs/MAINTAINING.md)" in readme

    assert "Use a fresh directory for this walkthrough." in quickstart
    assert "If you are maintaining Hive itself" in quickstart
    assert "Once you have more than one project and want the cross-project queue" in quickstart
    assert "hive program doctor demo" in quickstart

    assert "hive task ready --project-id demo" in demo_agency
    assert "make session PROJECT=demo" in demo_agency
    assert "checkout convenience, not the main product path" in demo_agency

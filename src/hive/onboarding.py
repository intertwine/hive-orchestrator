"""Guided onboarding and adoption flows for Hive 2.2."""

from __future__ import annotations

from pathlib import Path
import subprocess

from src.hive.payloads import project_payload
from src.hive.program import add_evaluator_template, doctor_program
from src.hive.scaffold import starter_task_specs
from src.hive.store.layout import bootstrap_workspace
from src.hive.store.projects import create_project, discover_projects
from src.hive.store.task_files import create_task, link_tasks, list_tasks
from src.hive.workspace import sync_workspace


def _has_git_head(root: Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:  # pragma: no cover - defensive
        return False
    return result.returncode == 0


def _serializable_bootstrap(payload: dict[str, object]) -> dict[str, object]:
    layout = {
        key: str(value)
        for key, value in dict(payload.get("layout", {})).items()
    }
    return {
        "layout": layout,
        "created_files": list(payload.get("created_files", [])),
        "updated_files": list(payload.get("updated_files", [])),
    }


def _seed_starter_tasks(
    root: Path, project_id: str, project_title: str, objective: str | None = None
) -> list[dict[str, object]]:
    existing = [task for task in list_tasks(root) if task.project_id == project_id]
    if existing:
        return [
            {
                "id": task.id,
                "project_id": task.project_id,
                "title": task.title,
                "status": task.status,
                "priority": task.priority,
            }
            for task in existing
        ]
    tasks = []
    for spec in starter_task_specs(project_title, objective):
        task = create_task(
            root,
            project_id,
            str(spec["title"]),
            status=str(spec["status"]),
            priority=int(spec["priority"]),
            acceptance=list(spec["acceptance"]),
            summary_md=str(spec["summary_md"]),
        )
        tasks.append(task)
    for current, nxt in zip(tasks, tasks[1:]):
        link_tasks(root, current.id, "blocks", nxt.id)
    return [
        {
            "id": task.id,
            "project_id": task.project_id,
            "title": task.title,
            "status": task.status,
            "priority": task.priority,
        }
        for task in tasks
    ]


def _auto_fix_program(root: Path, project_id: str) -> dict:
    diagnosis = doctor_program(root, project_id)
    if diagnosis["blocked_autonomous_promotion"] and len(diagnosis["suggested_templates"]) == 1:
        template_id = diagnosis["suggested_templates"][0]["id"]
        diagnosis = add_evaluator_template(root, project_id, template_id)
    return diagnosis


def onboard_workspace(
    path: str | Path | None,
    *,
    slug: str = "demo",
    title: str | None = None,
    objective: str | None = None,
) -> dict:
    """Guide a new user from empty directory to a real Hive project."""
    root = Path(path or Path.cwd()).resolve()
    bootstrapped = bootstrap_workspace(root)
    project = None
    for candidate in discover_projects(root):
        if slug in {candidate.slug, candidate.id}:
            project = candidate
            break
    if project is None:
        project = create_project(root, slug, title=title, objective=objective)
    tasks = _seed_starter_tasks(root, project.id, project.title, objective)
    diagnosis = _auto_fix_program(root, project.id)
    sync_workspace(root)
    return {
        "workspace": str(root),
        "bootstrapped": _serializable_bootstrap(bootstrapped),
        "project": project_payload(project),
        "tasks": tasks,
        "program": diagnosis,
        "git_ready": _has_git_head(root),
    }


def adopt_repository(
    path: str | Path | None,
    *,
    slug: str | None = None,
    title: str | None = None,
    objective: str | None = None,
) -> dict:
    """Guide an existing repo into a safe Hive 2.2 baseline."""
    root = Path(path or Path.cwd()).resolve()
    bootstrapped = bootstrap_workspace(root)
    projects = discover_projects(root)
    project = projects[0] if projects else None
    if project is None:
        resolved_slug = slug or root.name.replace("_", "-")
        project = create_project(root, resolved_slug, title=title, objective=objective)
    tasks = _seed_starter_tasks(root, project.id, project.title, objective)
    diagnosis = _auto_fix_program(root, project.id)
    sync_workspace(root)
    return {
        "workspace": str(root),
        "bootstrapped": _serializable_bootstrap(bootstrapped),
        "project": project_payload(project),
        "tasks": tasks,
        "program": diagnosis,
        "git_ready": _has_git_head(root),
    }

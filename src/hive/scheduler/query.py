"""Ready detection and project summaries."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.hive.models.project import ProjectRecord
from src.hive.models.task import TaskRecord
from src.hive.store.projects import discover_projects
from src.hive.store.task_files import list_tasks


def _is_claim_active(task: TaskRecord) -> bool:
    if not task.owner or not task.claimed_until:
        return False
    try:
        claim_time = datetime.fromisoformat(task.claimed_until.replace("Z", "+00:00"))
    except ValueError:
        return False
    return claim_time > datetime.now(timezone.utc)


def _effective_status(task: TaskRecord) -> str:
    """Return the task status after accounting for lease expiry."""
    if task.status == "claimed" and not _is_claim_active(task):
        return "ready"
    return task.status


def _blocked_by(task: TaskRecord, tasks_by_id: dict[str, TaskRecord]) -> list[str]:
    blockers = []
    for candidate in tasks_by_id.values():
        if task.id in candidate.edges.get("blocks", []) and candidate.status not in {
            "done",
            "archived",
        }:
            blockers.append(candidate.id)
    return blockers


def _is_superseded(task: TaskRecord, tasks_by_id: dict[str, TaskRecord]) -> bool:
    for candidate in tasks_by_id.values():
        if candidate.id == task.id:
            continue
        if task.id in candidate.edges.get("duplicates", []) and candidate.status not in {
            "done",
            "archived",
        }:
            return True
        if task.id in candidate.edges.get("supersedes", []) and candidate.status not in {
            "done",
            "archived",
        }:
            return True
    return False


def ready_tasks(
    path: str | Path | None = None,
    *,
    project_id: str | None = None,
    limit: int | None = None,
) -> list[dict[str, object]]:
    """Return ranked ready tasks."""
    tasks = list_tasks(path)
    tasks_by_id = {task.id: task for task in tasks}
    ready: list[dict[str, object]] = []

    for task in tasks:
        if project_id and task.project_id != project_id:
            continue
        effective_status = _effective_status(task)
        if effective_status not in {"proposed", "ready"}:
            continue
        blocked = _blocked_by(task, tasks_by_id)
        if blocked or _is_superseded(task, tasks_by_id):
            continue
        score = float(100 - (task.priority * 10))
        ready.append(
            {
                "id": task.id,
                "project_id": task.project_id,
                "title": task.title,
                "status": effective_status,
                "priority": task.priority,
                "owner": task.owner,
                "blocked_by": blocked,
                "score": score,
            }
        )

    ready.sort(key=lambda item: (item["priority"], str(item["title"]).lower()))
    if limit is not None:
        ready = ready[:limit]
    return ready


def project_summary(path: str | Path | None = None) -> list[dict[str, object]]:
    """Return discovered projects with task counts."""
    projects = discover_projects(path)
    tasks = list_tasks(path)
    summaries: list[dict[str, object]] = []
    for project in projects:
        project_tasks = [task for task in tasks if task.project_id == project.id]
        summaries.append(
            {
                "id": project.id,
                "slug": project.slug,
                "title": project.title,
                "status": project.status,
                "priority": project.priority,
                "owner": project.owner,
                "path": str(project.agency_path),
                "ready": len(
                    [task for task in project_tasks if _effective_status(task) in {"proposed", "ready"}]
                ),
                "in_progress": len(
                    [task for task in project_tasks if _effective_status(task) in {"claimed", "in_progress"}]
                ),
                "blocked": len([task for task in project_tasks if task.status == "blocked"]),
            }
        )
    return summaries


def dependency_summary(path: str | Path | None = None) -> dict[str, object]:
    """Return a project dependency summary compatible with v1 deps views."""
    projects = discover_projects(path)
    project_map = {project.id: project for project in projects}
    summary = {
        "total_projects": len(projects),
        "projects": [],
        "has_cycles": False,
        "cycles": [],
    }
    for project in projects:
        dependencies = project.metadata.get("dependencies", {})
        blocked_by = list(dependencies.get("blocked_by", []))
        blocks = list(dependencies.get("blocks", []))
        effectively_blocked = any(
            blocker not in project_map or project_map[blocker].status != "completed"
            for blocker in blocked_by
        )
        summary["projects"].append(
            {
                "project_id": project.id,
                "status": project.status,
                "priority": project.priority,
                "owner": project.owner,
                "blocked": project.metadata.get("blocked", False),
                "blocks": blocks,
                "blocked_by": blocked_by,
                "effectively_blocked": effectively_blocked,
                "blocking_reasons": blocked_by if effectively_blocked else [],
                "in_cycle": False,
            }
        )
    return summary

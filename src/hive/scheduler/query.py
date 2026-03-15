"""Ready detection and project summaries."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json

from src.hive.models.task import TaskRecord
from src.hive.store.layout import runs_dir
from src.hive.store.projects import discover_projects
from src.hive.store.task_files import list_tasks

ACTIVE_RUN_STATUSES = {"running", "evaluating"}
TERMINAL_RUN_STATUSES = {"accepted", "rejected", "escalated", "aborted"}


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _age_hours(value: str | None) -> float:
    timestamp = _parse_iso(value)
    if timestamp is None:
        return 0.0
    return max((datetime.now(timezone.utc) - timestamp).total_seconds() / 3600.0, 0.0)


def _is_claim_active(task: TaskRecord) -> bool:
    if not task.owner or not task.claimed_until:
        return False
    claim_time = _parse_iso(task.claimed_until)
    if claim_time is None:
        return False
    return claim_time > datetime.now(timezone.utc)


def _claim_adjusted_status(task: TaskRecord) -> str:
    """Return the task status after accounting for lease expiry."""
    if task.status == "claimed" and not _is_claim_active(task):
        return "ready"
    return task.status


def _has_incoming_blockers(task: TaskRecord, tasks_by_id: dict[str, TaskRecord]) -> bool:
    """Return whether any task declares this task as blocked by it."""
    return any(task.id in candidate.edges.get("blocks", []) for candidate in tasks_by_id.values())


def _effective_status(task: TaskRecord, tasks_by_id: dict[str, TaskRecord] | None = None) -> str:
    """Return the task status after accounting for claims and cleared dependencies."""
    status = _claim_adjusted_status(task)
    if (
        status == "blocked"
        and tasks_by_id is not None
        and _has_incoming_blockers(task, tasks_by_id)
        and not _blocked_by(task, tasks_by_id)
    ):
        return "ready"
    return status


def _blocked_by(task: TaskRecord, tasks_by_id: dict[str, TaskRecord]) -> list[str]:
    blockers = []
    for candidate in tasks_by_id.values():
        if task.id in candidate.edges.get("blocks", []) and _claim_adjusted_status(candidate) not in {
            "done",
            "archived",
        }:
            blockers.append(candidate.id)
    return blockers


def _is_superseded(task: TaskRecord, tasks_by_id: dict[str, TaskRecord]) -> bool:
    for candidate in tasks_by_id.values():
        if candidate.id == task.id:
            continue
        candidate_status = _claim_adjusted_status(candidate)
        if task.id in candidate.edges.get("duplicates", []) and candidate_status not in {
            "done",
            "archived",
        }:
            return True
        if task.id in candidate.edges.get("supersedes", []) and candidate_status not in {
            "done",
            "archived",
        }:
            return True
    return False


def _run_pressure(path: str | Path | None) -> tuple[dict[str, int], dict[str, float]]:
    active_counts: dict[str, int] = {}
    recent_terminal_hours: dict[str, float] = {}
    root = Path(path or Path.cwd())
    runs_root = runs_dir(root)
    if not runs_root.exists():
        return active_counts, recent_terminal_hours
    for metadata_path in runs_root.glob("*/metadata.json"):
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        project_id = str(metadata.get("project_id") or "").strip()
        if not project_id:
            continue
        status = str(metadata.get("status") or "")
        if status in ACTIVE_RUN_STATUSES:
            active_counts[project_id] = active_counts.get(project_id, 0) + 1
        if status in TERMINAL_RUN_STATUSES:
            hours = _age_hours(metadata.get("finished_at"))
            current = recent_terminal_hours.get(project_id)
            if current is None or hours < current:
                recent_terminal_hours[project_id] = hours
    return active_counts, recent_terminal_hours


def _task_score(
    task: TaskRecord,
    *,
    effective_status: str,
    project_priority: int,
    active_runs: int,
    recent_terminal_age_hours: float | None,
) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 140.0 - (task.priority * 18.0)
    reasons.append(f"Priority p{task.priority} sets the baseline")

    project_bonus = max(0.0, 12.0 - (project_priority * 4.0))
    if project_bonus:
        score += project_bonus
        reasons.append(f"Project priority adds +{project_bonus:.1f}")

    if effective_status == "ready":
        score += 8.0
        reasons.append("Already in ready state")
    else:
        reasons.append("Still in proposed state")

    age_bonus = min(_age_hours(task.created_at) * 0.35, 20.0)
    if age_bonus:
        score += age_bonus
        reasons.append(f"Aging boost +{age_bonus:.1f}")

    stale_age_bonus = min(_age_hours(task.updated_at) * 0.05, 4.0)
    if stale_age_bonus:
        score += stale_age_bonus
        reasons.append(f"Stale context bonus +{stale_age_bonus:.1f}")

    if active_runs:
        penalty = active_runs * 18.0
        score -= penalty
        reasons.append(f"Project already has {active_runs} active run(s)")

    if recent_terminal_age_hours is not None and recent_terminal_age_hours < 12:
        penalty = max(0.0, 12.0 - recent_terminal_age_hours)
        score -= penalty
        reasons.append("Recent project activity nudges work toward quieter projects")

    return score, reasons


def ready_tasks(
    path: str | Path | None = None,
    *,
    project_id: str | None = None,
    limit: int | None = None,
) -> list[dict[str, object]]:
    """Return ranked ready tasks."""
    tasks = list_tasks(path)
    tasks_by_id = {task.id: task for task in tasks}
    projects = {project.id: project for project in discover_projects(path)}
    active_runs_by_project, recent_terminal_by_project = _run_pressure(path)
    ready: list[dict[str, object]] = []

    for task in tasks:
        if project_id and task.project_id != project_id:
            continue
        project = projects.get(task.project_id)
        if project is None:
            continue
        if project.status in {"blocked", "completed", "archived"}:
            continue
        effective_status = _effective_status(task, tasks_by_id)
        if effective_status not in {"proposed", "ready"}:
            continue
        blocked = _blocked_by(task, tasks_by_id)
        superseded = _is_superseded(task, tasks_by_id)
        if blocked or superseded:
            continue
        score, reasons = _task_score(
            task,
            effective_status=effective_status,
            project_priority=project.priority,
            active_runs=active_runs_by_project.get(task.project_id, 0),
            recent_terminal_age_hours=recent_terminal_by_project.get(task.project_id),
        )
        ready.append(
            {
                "id": task.id,
                "project_id": task.project_id,
                "title": task.title,
                "status": effective_status,
                "priority": task.priority,
                "project_priority": project.priority,
                "owner": task.owner,
                "blocked_by": blocked,
                "score": round(score, 2),
                "reasons": reasons,
            }
        )

    ready.sort(
        key=lambda item: (
            -float(item["score"]),
            int(item["priority"]),
            str(item["title"]).lower(),
            str(item["id"]),
        )
    )
    if limit is not None:
        ready = ready[:limit]
    return ready


def project_summary(path: str | Path | None = None) -> list[dict[str, object]]:
    """Return discovered projects with truthful task counts and next-work hints."""
    projects = discover_projects(path)
    tasks = list_tasks(path)
    summaries: list[dict[str, object]] = []
    for project in projects:
        project_tasks = [task for task in tasks if task.project_id == project.id]
        project_tasks_by_id = {task.id: task for task in project_tasks}
        ready = ready_tasks(path, project_id=project.id, limit=None)
        summaries.append(
            {
                "id": project.id,
                "slug": project.slug,
                "title": project.title,
                "status": project.status,
                "priority": project.priority,
                "owner": project.owner,
                "path": str(project.agency_path),
                "ready": len(ready),
                "next_task_id": ready[0]["id"] if ready else None,
                "next_task_title": ready[0]["title"] if ready else None,
                "next_task_score": ready[0]["score"] if ready else None,
                "in_progress": len(
                    [
                        task
                        for task in project_tasks
                        if _effective_status(task, project_tasks_by_id) in {"claimed", "in_progress"}
                    ]
                ),
                "blocked": len(
                    [
                        task
                        for task in project_tasks
                        if _effective_status(task, project_tasks_by_id) == "blocked"
                    ]
                ),
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

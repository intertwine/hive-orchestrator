"""Ready detection, graph analysis, and project summaries."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json

from src.hive.constants import RUN_ACTIVE_STATUSES, RUN_TERMINAL_STATUSES
from src.hive.models.task import TaskRecord
from src.hive.store.layout import runs_dir
from src.hive.store.projects import discover_projects
from src.hive.store.task_files import list_tasks


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
        if (
            task.id in candidate.edges.get("blocks", [])
            and _claim_adjusted_status(candidate) not in {"done", "archived"}
        ):
            blockers.append(candidate.id)
    return blockers


def _count_task_unblock_impact(task: TaskRecord, tasks_by_id: dict[str, TaskRecord]) -> int:
    """Count reachable downstream tasks this task would unblock."""
    seen: set[str] = set()
    pending_states = {"proposed", "ready", "blocked", "claimed", "in_progress"}
    stack = list(task.edges.get("blocks", []))
    while stack:
        candidate_id = stack.pop()
        if candidate_id in seen:
            continue
        seen.add(candidate_id)
        candidate = tasks_by_id.get(candidate_id)
        if candidate is None:
            continue
        if _claim_adjusted_status(candidate) in pending_states:
            stack.extend(candidate.edges.get("blocks", []))
    return len(seen)


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
        if status in RUN_ACTIVE_STATUSES:
            active_counts[project_id] = active_counts.get(project_id, 0) + 1
        if status in RUN_TERMINAL_STATUSES:
            hours = _age_hours(metadata.get("finished_at"))
            current = recent_terminal_hours.get(project_id)
            if current is None or hours < current:
                recent_terminal_hours[project_id] = hours
    return active_counts, recent_terminal_hours


def _project_dependency_lists(project) -> tuple[list[str], list[str]]:
    dependencies = project.metadata.get("dependencies", {})
    if not isinstance(dependencies, dict):
        return [], []
    blocked_by = [
        str(value).strip()
        for value in dependencies.get("blocked_by", [])
        if str(value).strip()
    ]
    blocks = [
        str(value).strip()
        for value in dependencies.get("blocks", [])
        if str(value).strip()
    ]
    return blocked_by, blocks


def _project_dependency_graph(projects) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Return dependency and reverse-dependency graphs keyed by project id."""
    graph: dict[str, set[str]] = {project.id: set() for project in projects}
    reverse_graph: dict[str, set[str]] = {project.id: set() for project in projects}
    for project in projects:
        blocked_by, blocks = _project_dependency_lists(project)
        for blocker in blocked_by:
            graph.setdefault(project.id, set()).add(blocker)
            reverse_graph.setdefault(blocker, set()).add(project.id)
        for blocked in blocks:
            graph.setdefault(blocked, set()).add(project.id)
            reverse_graph.setdefault(project.id, set()).add(blocked)
    return graph, reverse_graph


def _normalize_cycle(cycle: list[str]) -> tuple[str, ...]:
    """Rotate a cycle to a stable representation for deduplication."""
    if len(cycle) <= 1:
        return tuple(cycle)
    ring = cycle[:-1] if cycle[0] == cycle[-1] else cycle
    if not ring:
        return tuple()
    rotations = [tuple(ring[index:] + ring[:index]) for index in range(len(ring))]
    reverse_ring = list(reversed(ring))
    reverse_rotations = [
        tuple(reverse_ring[index:] + reverse_ring[:index]) for index in range(len(reverse_ring))
    ]
    best = min(rotations + reverse_rotations)
    return best + (best[0],)


def _find_project_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    """Detect dependency cycles in the project graph."""
    cycles: set[tuple[str, ...]] = set()

    def _visit(node: str, path: list[str], visiting: set[str]) -> None:
        visiting.add(node)
        path.append(node)
        for neighbor in sorted(graph.get(node, set())):
            if neighbor not in graph:
                continue
            if neighbor in visiting:
                start = path.index(neighbor)
                cycles.add(_normalize_cycle(path[start:] + [neighbor]))
                continue
            if neighbor in path:
                continue
            _visit(neighbor, path, visiting)
        path.pop()
        visiting.discard(node)

    for node in sorted(graph):
        _visit(node, [], set())
    return [list(cycle) for cycle in sorted(cycles)]


def _reachable_count(node: str, adjacency: dict[str, set[str]]) -> int:
    seen: set[str] = set()
    stack = list(adjacency.get(node, set()))
    while stack:
        candidate = stack.pop()
        if candidate in seen:
            continue
        seen.add(candidate)
        stack.extend(adjacency.get(candidate, set()))
    return len(seen)


def _task_score(
    task: TaskRecord,
    *,
    effective_status: str,
    project_priority: int,
    active_runs: int,
    recent_terminal_age_hours: float | None,
    project_downstream_count: int,
    project_in_cycle: bool,
    task_unblock_count: int,
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

    if project_downstream_count:
        downstream_bonus = min(project_downstream_count * 2.0, 10.0)
        score += downstream_bonus
        reasons.append(f"Project unblocks {project_downstream_count} downstream project(s)")

    if task_unblock_count:
        unblock_bonus = min(task_unblock_count * 3.0, 15.0)
        score += unblock_bonus
        reasons.append(f"Completing this task would unblock {task_unblock_count} task(s)")

    if project_in_cycle:
        score -= 12.0
        reasons.append("Project is inside a dependency cycle and needs human untangling")

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
    project_records = discover_projects(path)
    projects = {project.id: project for project in project_records}
    project_graph, reverse_graph = _project_dependency_graph(project_records)
    project_cycles = _find_project_cycles(project_graph)
    projects_in_cycles = {
        project_id
        for cycle in project_cycles
        for project_id in cycle[:-1]
    }
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
            project_downstream_count=_reachable_count(task.project_id, reverse_graph),
            project_in_cycle=task.project_id in projects_in_cycles,
            task_unblock_count=_count_task_unblock_impact(task, tasks_by_id),
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
                "graph_rank": {
                    "project_downstream_count": _reachable_count(task.project_id, reverse_graph),
                    "task_unblock_count": _count_task_unblock_impact(task, tasks_by_id),
                    "project_in_cycle": task.project_id in projects_in_cycles,
                },
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
                        if _effective_status(task, project_tasks_by_id)
                        in {"claimed", "in_progress"}
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
    project_graph, reverse_graph = _project_dependency_graph(projects)
    cycles = _find_project_cycles(project_graph)
    cycle_members = {
        project_id
        for cycle in cycles
        for project_id in cycle[:-1]
    }
    summary = {
        "total_projects": len(projects),
        "projects": [],
        "has_cycles": bool(cycles),
        "cycles": cycles,
    }
    for project in projects:
        blocked_by, blocks = _project_dependency_lists(project)
        effectively_blocked = any(
            blocker not in project_map or project_map[blocker].status != "completed"
            for blocker in blocked_by
        )
        blocking_reasons = list(blocked_by) if effectively_blocked else []
        if project.id in cycle_members:
            effectively_blocked = True
            blocking_reasons.append("dependency cycle")
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
                "blocking_reasons": blocking_reasons,
                "in_cycle": project.id in cycle_members,
                "upstream_count": _reachable_count(project.id, project_graph),
                "downstream_count": _reachable_count(project.id, reverse_graph),
            }
        )
    return summary

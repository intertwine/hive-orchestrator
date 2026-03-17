"""Portfolio-manager helpers built on top of canonical Hive primitives."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import getpass
import json
import os

from src.hive.constants import RUN_ACTIVE_STATUSES
from src.hive.context_bundle import build_context_bundle
from src.hive.runs.engine import (
    accept_run,
    cleanup_terminal_runs,
    escalate_run,
    eval_run,
    load_run,
    promote_run,
    reject_run,
    start_run,
)
from src.hive.runs.worktree import create_checkpoint_commit
from src.hive.scheduler.query import project_summary, ready_tasks
from src.hive.store.events import emit_event, load_events
from src.hive.store.projects import discover_projects, get_project, save_project
from src.hive.store.task_files import claim_task, get_task
from src.hive.workspace import resolve_workspace_path, sync_workspace


STEERING_DEFAULTS = {
    "paused": False,
    "focus_task_id": None,
    "boost": 0,
    "force_review": False,
    "note": "",
    "updated_at": None,
    "updated_by": None,
}
ACTIVE_RUN_STATUSES = set(RUN_ACTIVE_STATUSES)
REVIEW_RUN_STATUSES = {"awaiting_review", "evaluating"}


def _default_owner() -> str:
    for env_name in ("HIVE_OWNER", "USER", "LOGNAME"):
        value = os.environ.get(env_name, "").strip()
        if value:
            return value
    try:
        return getpass.getuser() or "operator"
    except OSError:  # pragma: no cover - defensive
        return "operator"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _claim_is_active(task) -> bool:
    claim_deadline = _parse_iso(getattr(task, "claimed_until", None))
    return (
        bool(getattr(task, "owner", None))
        and claim_deadline is not None
        and claim_deadline > datetime.now(timezone.utc)
    )


def steering_state(project) -> dict[str, Any]:
    """Return normalized steering metadata for a project."""
    raw = project.metadata.get("steering", {})
    state = dict(STEERING_DEFAULTS)
    if isinstance(raw, dict):
        state.update(raw)
    state["paused"] = bool(state.get("paused", False))
    state["force_review"] = bool(state.get("force_review", False))
    try:
        state["boost"] = int(state.get("boost", 0))
    except (TypeError, ValueError):
        state["boost"] = 0
    focus_task_id = state.get("focus_task_id")
    state["focus_task_id"] = str(focus_task_id).strip() if focus_task_id else None
    state["note"] = str(state.get("note", "")).strip()
    state["updated_at"] = state.get("updated_at")
    state["updated_by"] = state.get("updated_by")
    return state


def _project_payload(project) -> dict[str, Any]:
    return {
        "id": project.id,
        "slug": project.slug,
        "title": project.title,
        "status": project.status,
        "priority": project.priority,
        "owner": project.owner,
        "path": str(project.agency_path),
        "program_path": str(project.program_path),
        "steering": steering_state(project),
    }


def _run_metadata_paths(root: Path) -> list[Path]:
    return sorted((root / ".hive" / "runs").glob("run_*/metadata.json"))


def _record_run_context_output(root: Path, run_id: str, output_path: Path) -> None:
    metadata_path = root / ".hive" / "runs" / run_id / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata.setdefault("metadata_json", {})["context_output_path"] = str(output_path)
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")


def _active_runs(root: Path) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for metadata_path in _run_metadata_paths(root):
        metadata = load_run(root, metadata_path.parent.name)
        if metadata.get("status") not in ACTIVE_RUN_STATUSES:
            continue
        runs.append(metadata)
    runs.sort(key=lambda item: item.get("started_at") or item["id"])
    return runs


def _evaluating_runs(root: Path) -> list[dict[str, Any]]:
    return [run for run in _active_runs(root) if run.get("status") in REVIEW_RUN_STATUSES]


def _recent_manager_events(root: Path, *, limit: int = 12) -> list[dict[str, Any]]:
    interesting_prefixes = ("portfolio.", "project.steered", "run.")
    events = [
        event
        for event in load_events(root)
        if str(event.get("event_type", "")).startswith(interesting_prefixes)
    ]
    events.sort(key=lambda item: item.get("occurred_at", ""), reverse=True)
    return events[:limit]


def portfolio_status(path: str | Path | None = None) -> dict[str, Any]:
    """Return an agent-manager view over the workspace."""
    root = Path(path or Path.cwd()).resolve()
    projects = discover_projects(root)
    summary_by_id = {item["id"]: item for item in project_summary(root)}
    ready = ready_tasks(root, limit=20)
    recommended = recommend_next_task(root, emit_decision_event=False)
    return {
        "workspace": str(root),
        "projects": [
            summary_by_id.get(project.id, {}) | _project_payload(project) for project in projects
        ],
        "ready_tasks": ready,
        "active_runs": _active_runs(root),
        "evaluating_runs": _evaluating_runs(root),
        "recommended_next": recommended,
        "recent_events": _recent_manager_events(root),
        "cleanup_hint": "Run `hive run cleanup --terminal` to prune old terminal worktrees.",
    }


def _candidate_reasons(task: dict[str, Any], project) -> tuple[float, list[str]]:
    steering = steering_state(project)
    score = float(task.get("score", 0.0))
    reasons: list[str] = list(task.get("reasons") or [])
    if steering["paused"]:
        reasons.append(f"Skipped because project {project.id} is paused")
        return -1000000.0, reasons
    if steering["focus_task_id"] == task["id"]:
        score += 1000
        reasons.append("Focused task pinned by a steering override")
    if steering["boost"]:
        score += float(steering["boost"] * 10)
        reasons.append(f"Project boost applied ({steering['boost']})")
    if task.get("status") == "ready":
        score += 5
        reasons.append("Already in ready state")
    if task.get("priority") == 1:
        reasons.append("Highest task priority")
    return score, reasons


def recommend_next_task(
    path: str | Path | None = None,
    *,
    project_id: str | None = None,
    emit_decision_event: bool = True,
) -> dict[str, Any] | None:
    """Recommend the next task for a human or agent manager."""
    root = Path(path or Path.cwd()).resolve()
    projects = {project.id: project for project in discover_projects(root)}
    candidates = ready_tasks(root, project_id=project_id, limit=None)
    ranked: list[dict[str, Any]] = []
    for task in candidates:
        project = projects.get(task["project_id"])
        if project is None:
            continue
        score, reasons = _candidate_reasons(task, project)
        if score < -999999:
            continue
        ranked.append(
            {
                "task": task,
                "project": _project_payload(project),
                "score": score,
                "reasons": reasons or ["Highest-ranked ready task in the current queue"],
            }
        )
    ranked.sort(
        key=lambda item: (
            -float(item["score"]),
            int(item["task"].get("priority", 9)),
            str(item["task"].get("title", "")).lower(),
            str(item["task"].get("id", "")),
        )
    )
    recommendation = ranked[0] if ranked else None
    if recommendation and emit_decision_event:
        emit_event(
            root,
            actor="hive",
            entity_type="portfolio",
            entity_id=project_id or "workspace",
            event_type="portfolio.recommended",
            source="portfolio.next",
            payload={
                "task_id": recommendation["task"]["id"],
                "project_id": recommendation["task"]["project_id"],
                "reasons": recommendation["reasons"],
            },
        )
    return recommendation


def steer_project(
    path: str | Path | None,
    project_ref: str,
    *,
    paused: bool | None = None,
    focus_task_id: str | None = None,
    clear_focus: bool = False,
    boost: int | None = None,
    force_review: bool | None = None,
    note: str | None = None,
    actor: str | None = None,
) -> dict[str, Any]:
    """Persist a human steering override into the project metadata."""
    root = Path(path or Path.cwd()).resolve()
    project = get_project(root, project_ref)
    steering = steering_state(project)
    if paused is not None:
        steering["paused"] = paused
    if clear_focus:
        steering["focus_task_id"] = None
    elif focus_task_id is not None:
        get_task(root, focus_task_id)
        steering["focus_task_id"] = focus_task_id
    if boost is not None:
        steering["boost"] = boost
    if force_review is not None:
        steering["force_review"] = force_review
    if note is not None:
        steering["note"] = note.strip()
    steering["updated_at"] = _iso_now()
    steering["updated_by"] = actor or _default_owner()
    project.metadata["steering"] = steering
    save_project(project)
    sync_workspace(root)
    emit_event(
        root,
        actor=steering["updated_by"],
        entity_type="project",
        entity_id=project.id,
        event_type="project.steered",
        source="portfolio.steer",
        payload={"steering": steering},
    )
    return {"project": _project_payload(project), "steering": steering}


def work_on_task(
    path: str | Path | None,
    *,
    task_id: str | None = None,
    project_id: str | None = None,
    owner: str | None = None,
    ttl_minutes: int = 60,
    driver: str = "local",
    model: str | None = None,
    campaign_id: str | None = None,
    profile: str = "default",
    output_path: str | Path | None = None,
    checkpoint: bool = True,
    checkpoint_message: str | None = None,
) -> dict[str, Any]:
    """Claim a task, refresh context, and start a governed run."""
    root = Path(path or Path.cwd()).resolve()
    resolved_owner = (owner or _default_owner()).strip() or "operator"
    recommendation = None
    if task_id is None:
        recommendation = recommend_next_task(root, project_id=project_id)
        if recommendation is None:
            raise ValueError("No ready task is available for `hive work`.")
        task_id = str(recommendation["task"]["id"])

    task = get_task(root, task_id)

    checkpoint_payload = None
    if checkpoint:
        checkpoint_payload = create_checkpoint_commit(
            root,
            message=checkpoint_message or f"Checkpoint before starting {task_id}",
        )
    if task.owner and task.owner != resolved_owner:
        if task.status == "in_progress":
            raise ValueError(f"Task {task.id} is already in progress by {task.owner}.")
        if task.status == "claimed" and _claim_is_active(task):
            raise ValueError(
                f"Task {task.id} is actively claimed by {task.owner} until {task.claimed_until}."
            )
    if task.status in {"proposed", "ready"} or (
        task.status == "claimed" and task.owner == resolved_owner
    ):
        task = claim_task(root, task.id, resolved_owner, ttl_minutes)
        sync_workspace(root)
    run = start_run(
        root,
        task.id,
        driver_name=driver,
        model=model,
        campaign_id=campaign_id,
        profile=profile,
    )
    sync_workspace(root)
    bundle = build_context_bundle(
        root,
        project_ref=task.project_id,
        mode="startup",
        profile=profile,
        task_id=task.id,
        refresh=True,
    )
    rendered_context = str(bundle["rendered"])
    written_output = None
    if output_path:
        target = resolve_workspace_path(root, output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered_context, encoding="utf-8")
        written_output = str(target)
        _record_run_context_output(root, run.id, target)

    emit_event(
        root,
        actor=resolved_owner,
        entity_type="run",
        entity_id=run.id,
        event_type="portfolio.work.started",
        source="portfolio.work",
        payload={
            "task_id": task.id,
            "project_id": task.project_id,
            "recommendation": recommendation,
        },
    )
    return {
        "task": task.to_frontmatter() | {"path": str(task.path) if task.path else None},
        "run": run.to_dict(),
        "checkpoint": checkpoint_payload,
        "recommendation": recommendation,
        "project": bundle["project_payload"],
        "context": bundle["context"],
        "rendered_context": rendered_context if written_output is None else None,
        "output_path": written_output,
    }


def finish_run_flow(
    path: str | Path | None,
    run_id: str,
    *,
    promote: bool = True,
    cleanup_worktree: bool = True,
    actor: str | None = None,
) -> dict[str, Any]:
    """Evaluate and close a run through the manager-friendly happy path."""
    root = Path(path or Path.cwd()).resolve()
    resolved_actor = (actor or _default_owner()).strip() or "operator"
    metadata = load_run(root, run_id)
    evaluation = None
    if metadata.get("status") == "running":
        evaluation = eval_run(root, run_id)
        metadata = evaluation["run"]
    elif metadata.get("status") in {"awaiting_input", "completed_candidate"}:
        evaluation = eval_run(root, run_id)
        metadata = evaluation["run"]
    decision = (
        metadata.get("metadata_json", {}).get("promotion_decision")
        or (evaluation or {}).get("promotion_decision")
        or {"decision": "reject", "reasons": ["Run has no promotion decision recorded"]}
    )

    project = get_project(root, metadata["project_id"])
    steering = steering_state(project)
    action = "reject"
    final_run: dict[str, Any]
    promotion = None
    if metadata.get("status") == "accepted":
        action = "promote" if promote else "accept"
        final_run = metadata
        if promote:
            promotion = promote_run(root, run_id, cleanup_worktree=cleanup_worktree)
    elif steering["force_review"]:
        action = "escalate"
        final_run = escalate_run(
            root,
            run_id,
            "Project steering requires review before acceptance.",
        )
    elif decision.get("decision") == "accept":
        action = "promote" if promote else "accept"
        final_run = accept_run(root, run_id)
        if promote:
            promotion = promote_run(root, run_id, cleanup_worktree=cleanup_worktree)
    elif decision.get("decision") == "escalate":
        action = "escalate"
        final_run = escalate_run(root, run_id, "; ".join(decision.get("reasons", [])) or None)
    else:
        action = "reject"
        final_run = reject_run(root, run_id, "; ".join(decision.get("reasons", [])) or None)

    sync_workspace(root)
    emit_event(
        root,
        actor=resolved_actor,
        entity_type="run",
        entity_id=run_id,
        event_type="portfolio.finish.completed",
        source="portfolio.finish",
        payload={"action": action, "promotion_decision": decision},
    )
    return {
        "action": action,
        "run": final_run,
        "evaluation": evaluation,
        "promotion_decision": decision,
        "promotion": promotion,
    }


def tick_portfolio(
    path: str | Path | None,
    *,
    mode: str = "recommend",
    owner: str | None = None,
    project_id: str | None = None,
    profile: str = "default",
    output_path: str | Path | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Run one bounded portfolio-manager tick."""
    root = Path(path or Path.cwd()).resolve()
    if mode == "recommend":
        return {
            "mode": mode,
            "status": portfolio_status(root),
            "recommendation": recommend_next_task(root, project_id=project_id),
        }
    if mode == "start":
        return {
            "mode": mode,
            "status": portfolio_status(root),
            "work": work_on_task(
                root,
                task_id=None,
                project_id=project_id,
                owner=owner,
                driver="local",
                profile=profile,
                output_path=output_path,
            ),
        }
    if mode == "review":
        candidate_run_id = run_id
        if candidate_run_id is None:
            evaluating = _evaluating_runs(root)
            if not evaluating:
                raise ValueError(
                    "No review-ready run is available for `hive portfolio tick --mode review`."
                )
            candidate_run_id = evaluating[0]["id"]
        return {
            "mode": mode,
            "status": portfolio_status(root),
            "finish": finish_run_flow(root, candidate_run_id, actor=owner),
        }
    if mode == "cleanup":
        return {
            "mode": mode,
            "status": portfolio_status(root),
            "cleanups": cleanup_terminal_runs(root),
        }
    raise ValueError(f"Unsupported portfolio tick mode: {mode}")

"""Typed local Hive client for execute surfaces."""

# pylint: disable=missing-function-docstring

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.hive.control import (
    finish_run_flow,
    portfolio_status,
    release_task_flow,
    recommend_next_task,
    steer_project,
    tick_portfolio,
    work_on_task,
)
from src.hive.drivers import SteeringRequest
from src.hive.memory.context import handoff_context, startup_context
from src.hive.memory.observe import observe
from src.hive.memory.reflect import reflect
from src.hive.memory.search import search as search_memory
from src.hive.payloads import project_payload
from src.hive.runs.engine import (
    accept_run,
    escalate_run,
    eval_run,
    load_run,
    reject_run,
    run_artifacts,
    start_run,
    steer_run,
)
from src.hive.scheduler.query import ready_tasks
from src.hive.store.cache import rebuild_cache
from src.hive.store.projects import discover_projects, get_project
from src.hive.store.task_files import (
    claim_task,
    get_task,
    link_tasks,
    list_tasks,
    update_task,
)
from src.hive.workspace import sync_workspace


def _task_payload(task) -> dict[str, Any]:
    return task.to_frontmatter() | {"path": str(task.path) if task.path else None}


@dataclass
class ProjectModule:
    """Project-facing helpers exposed inside bounded local execute."""

    root: Path

    def list(self, payload: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        payload = payload or {}
        statuses = set(payload.get("status", []))
        projects = []
        for project in discover_projects(self.root):
            current = project_payload(project)
            if statuses and current["status"] not in statuses:
                continue
            projects.append(current)
        return projects

    def show(self, payload: dict[str, Any]) -> dict[str, Any]:
        project = get_project(self.root, payload["id"])
        return dict(project_payload(project))


@dataclass
class TaskModule:
    """Task-facing helpers exposed inside bounded local execute."""

    root: Path

    def list(self, payload: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        payload = payload or {}
        statuses = set(payload.get("status", []))
        project_id = payload.get("projectId")
        tasks = []
        for task in list_tasks(self.root):
            if project_id and task.project_id != project_id:
                continue
            if statuses and task.status not in statuses:
                continue
            tasks.append(_task_payload(task))
        return tasks

    def ready(self, payload: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        payload = payload or {}
        return ready_tasks(
            self.root,
            project_id=payload.get("projectId"),
            limit=payload.get("limit"),
        )

    def show(self, payload: dict[str, Any]) -> dict[str, Any]:
        return _task_payload(get_task(self.root, payload["id"]))

    def claim(self, payload: dict[str, Any]) -> dict[str, Any]:
        task = claim_task(
            self.root,
            payload["id"],
            payload["owner"],
            int(payload.get("ttlMinutes", 30)),
        )
        sync_workspace(self.root)
        return _task_payload(task)

    def release(self, payload: dict[str, Any]) -> dict[str, Any]:
        released = release_task_flow(self.root, payload["id"])
        return dict(released["task"]) | {"cancelled_runs": list(released.get("cancelled_runs", []))}

    def update(self, payload: dict[str, Any]) -> dict[str, Any]:
        task = update_task(self.root, payload["id"], dict(payload.get("patch", {})))
        sync_workspace(self.root)
        return _task_payload(task)

    def link(self, payload: dict[str, Any]) -> dict[str, Any]:
        task = link_tasks(self.root, payload["srcId"], payload["edgeType"], payload["dstId"])
        sync_workspace(self.root)
        return _task_payload(task)


@dataclass
class RunModule:
    """Run lifecycle helpers exposed inside bounded local execute."""

    root: Path

    def start(self, payload: dict[str, Any]) -> dict[str, Any]:
        run = start_run(
            self.root,
            payload["taskId"],
            driver_name=payload.get("driver"),
            model=payload.get("model"),
            campaign_id=payload.get("campaignId"),
            profile=payload.get("profile", "default"),
        )
        sync_workspace(self.root)
        return run.to_dict()

    def show(self, payload: dict[str, Any]) -> dict[str, Any]:
        return load_run(self.root, payload["id"])

    def artifacts(self, payload: dict[str, Any]) -> dict[str, Any]:
        return run_artifacts(self.root, payload["id"])

    def eval(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = eval_run(self.root, payload["id"])
        sync_workspace(self.root)
        return result

    def accept(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = accept_run(self.root, payload["id"])
        sync_workspace(self.root)
        return result

    def reject(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = reject_run(self.root, payload["id"], payload.get("reason"))
        sync_workspace(self.root)
        return result

    def escalate(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = escalate_run(self.root, payload["id"], payload.get("reason"))
        sync_workspace(self.root)
        return result

    def steer(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = steer_run(
            self.root,
            payload["id"],
            SteeringRequest(
                action=payload["action"],
                reason=payload.get("reason"),
                target=payload.get("target"),
                budget_delta=payload.get("budgetDelta"),
                note=payload.get("note"),
            ),
            actor=payload.get("owner"),
        )
        sync_workspace(self.root)
        return result


@dataclass
class MemoryModule:
    """Memory helpers exposed inside bounded local execute."""

    root: Path

    def search(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        return search_memory(
            self.root,
            payload["query"],
            scope=payload.get("scope", "all"),
            project_id=payload.get("projectId"),
            task_id=payload.get("taskId"),
            limit=int(payload.get("limit", 8)),
        )

    def observe(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        path = observe(
            self.root,
            transcript_path=payload.get("transcriptPath"),
            note=payload.get("note"),
            scope=payload.get("scope", "project"),
            harness=payload.get("harness"),
        )
        rebuild_cache(self.root)
        return {"path": str(path)}

    def reflect(self, payload: dict[str, Any] | None = None) -> dict[str, str]:
        payload = payload or {}
        result = {
            key: str(value)
            for key, value in reflect(self.root, scope=payload.get("scope", "project")).items()
        }
        rebuild_cache(self.root)
        return result


@dataclass
class ContextModule:
    """Context assembly helpers exposed inside bounded local execute."""

    root: Path

    def startup(self, payload: dict[str, Any]) -> dict[str, Any]:
        return startup_context(
            self.root,
            project_id=payload["projectId"],
            profile=payload.get("profile", "default"),
            query=payload.get("query"),
            task_id=payload.get("taskId"),
        )

    def handoff(self, payload: dict[str, Any]) -> dict[str, Any]:
        return handoff_context(self.root, project_id=payload["projectId"])


@dataclass
class SchedulerModule:
    """Scheduler helpers exposed inside bounded local execute."""

    root: Path

    def next(self, payload: dict[str, Any] | None = None) -> dict[str, Any] | None:
        payload = payload or {}
        ready = ready_tasks(self.root, project_id=payload.get("projectId"), limit=1)
        return ready[0] if ready else None


@dataclass
class ControlModule:
    """Manager-loop helpers exposed inside bounded local execute."""

    root: Path

    def next(self, payload: dict[str, Any] | None = None) -> dict[str, Any] | None:
        payload = payload or {}
        return recommend_next_task(self.root, project_id=payload.get("projectId"))

    def work(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        return work_on_task(
            self.root,
            task_id=payload.get("taskId"),
            project_id=payload.get("projectId"),
            owner=payload.get("owner"),
            ttl_minutes=int(payload.get("ttlMinutes", 60)),
            profile=payload.get("profile", "default"),
            output_path=payload.get("outputPath"),
            checkpoint=not bool(payload.get("noCheckpoint", False)),
            checkpoint_message=payload.get("checkpointMessage"),
        )

    def finish(self, payload: dict[str, Any]) -> dict[str, Any]:
        return finish_run_flow(
            self.root,
            payload["runId"],
            promote=not bool(payload.get("noPromote", False)),
            cleanup_worktree=not bool(payload.get("keepWorktree", False)),
            actor=payload.get("owner"),
        )

    def status(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        del payload
        return portfolio_status(self.root)

    def steer(self, payload: dict[str, Any]) -> dict[str, Any]:
        return steer_project(
            self.root,
            payload["projectRef"],
            paused=payload.get("paused"),
            focus_task_id=payload.get("focusTaskId"),
            clear_focus=bool(payload.get("clearFocus", False)),
            boost=payload.get("boost"),
            force_review=payload.get("forceReview"),
            note=payload.get("note"),
            actor=payload.get("owner"),
        )

    def tick(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        return tick_portfolio(
            self.root,
            mode=payload.get("mode", "recommend"),
            owner=payload.get("owner"),
            project_id=payload.get("projectId"),
            profile=payload.get("profile", "default"),
            output_path=payload.get("outputPath"),
            run_id=payload.get("runId"),
        )


class HiveClient:  # pylint: disable=too-many-instance-attributes,too-few-public-methods
    """Typed local client used inside the execute sandbox."""

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.project = ProjectModule(self.root)
        self.task = TaskModule(self.root)
        self.run = RunModule(self.root)
        self.memory = MemoryModule(self.root)
        self.context = ContextModule(self.root)
        self.scheduler = SchedulerModule(self.root)
        self.control = ControlModule(self.root)


__all__ = ["HiveClient"]

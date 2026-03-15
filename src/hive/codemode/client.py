"""Typed local Hive client for execute surfaces."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.hive.memory.context import handoff_context, startup_context
from src.hive.memory.observe import observe
from src.hive.memory.reflect import reflect
from src.hive.memory.search import search as search_memory
from src.hive.runs.engine import accept_run, escalate_run, eval_run, load_run, reject_run, start_run
from src.hive.scheduler.query import ready_tasks
from src.hive.store.cache import rebuild_cache
from src.hive.store.projects import discover_projects, get_project
from src.hive.store.task_files import (
    claim_task,
    get_task,
    link_tasks,
    list_tasks,
    release_task,
    update_task,
)


def _task_payload(task) -> dict[str, Any]:
    return task.to_frontmatter() | {"path": str(task.path) if task.path else None}


@dataclass
class ProjectModule:
    root: Path

    def list(self, input: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        input = input or {}
        statuses = set(input.get("status", []))
        projects = []
        for project in discover_projects(self.root):
            payload = {
                "id": project.id,
                "slug": project.slug,
                "title": project.title,
                "status": project.status,
                "priority": project.priority,
                "owner": project.owner,
                "path": str(project.agency_path),
                "program_path": str(project.program_path),
            }
            if statuses and payload["status"] not in statuses:
                continue
            projects.append(payload)
        return projects

    def show(self, input: dict[str, Any]) -> dict[str, Any]:
        project = get_project(self.root, input["id"])
        return {
            "id": project.id,
            "slug": project.slug,
            "title": project.title,
            "status": project.status,
            "priority": project.priority,
            "owner": project.owner,
            "path": str(project.agency_path),
            "program_path": str(project.program_path),
        }


@dataclass
class TaskModule:
    root: Path

    def list(self, input: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        input = input or {}
        statuses = set(input.get("status", []))
        project_id = input.get("projectId")
        tasks = []
        for task in list_tasks(self.root):
            if project_id and task.project_id != project_id:
                continue
            if statuses and task.status not in statuses:
                continue
            tasks.append(_task_payload(task))
        return tasks

    def ready(self, input: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        input = input or {}
        return ready_tasks(
            self.root,
            project_id=input.get("projectId"),
            limit=input.get("limit"),
        )

    def show(self, input: dict[str, Any]) -> dict[str, Any]:
        return _task_payload(get_task(self.root, input["id"]))

    def claim(self, input: dict[str, Any]) -> dict[str, Any]:
        task = claim_task(
            self.root,
            input["id"],
            input["owner"],
            int(input.get("ttlMinutes", 30)),
        )
        rebuild_cache(self.root)
        return _task_payload(task)

    def release(self, input: dict[str, Any]) -> dict[str, Any]:
        task = release_task(self.root, input["id"])
        rebuild_cache(self.root)
        return _task_payload(task)

    def update(self, input: dict[str, Any]) -> dict[str, Any]:
        task = update_task(self.root, input["id"], dict(input.get("patch", {})))
        rebuild_cache(self.root)
        return _task_payload(task)

    def link(self, input: dict[str, Any]) -> dict[str, Any]:
        task = link_tasks(self.root, input["srcId"], input["edgeType"], input["dstId"])
        rebuild_cache(self.root)
        return _task_payload(task)


@dataclass
class RunModule:
    root: Path

    def start(self, input: dict[str, Any]) -> dict[str, Any]:
        run = start_run(self.root, input["taskId"])
        rebuild_cache(self.root)
        return run.to_dict()

    def show(self, input: dict[str, Any]) -> dict[str, Any]:
        return load_run(self.root, input["id"])

    def eval(self, input: dict[str, Any]) -> dict[str, Any]:
        payload = eval_run(self.root, input["id"])
        rebuild_cache(self.root)
        return payload

    def accept(self, input: dict[str, Any]) -> dict[str, Any]:
        payload = accept_run(self.root, input["id"])
        rebuild_cache(self.root)
        return payload

    def reject(self, input: dict[str, Any]) -> dict[str, Any]:
        payload = reject_run(self.root, input["id"], input.get("reason"))
        rebuild_cache(self.root)
        return payload

    def escalate(self, input: dict[str, Any]) -> dict[str, Any]:
        payload = escalate_run(self.root, input["id"], input.get("reason"))
        rebuild_cache(self.root)
        return payload


@dataclass
class MemoryModule:
    root: Path

    def search(self, input: dict[str, Any]) -> list[dict[str, Any]]:
        return search_memory(self.root, input["query"])

    def observe(self, input: dict[str, Any] | None = None) -> dict[str, Any]:
        input = input or {}
        path = observe(self.root, transcript_path=input.get("transcriptPath"), note=input.get("note"))
        rebuild_cache(self.root)
        return {"path": str(path)}

    def reflect(self, input: dict[str, Any] | None = None) -> dict[str, str]:
        del input
        return {key: str(value) for key, value in reflect(self.root).items()}


@dataclass
class ContextModule:
    root: Path

    def startup(self, input: dict[str, Any]) -> dict[str, Any]:
        return startup_context(
            self.root,
            project_id=input["projectId"],
            profile=input.get("profile", "default"),
            query=input.get("query"),
        )

    def handoff(self, input: dict[str, Any]) -> dict[str, Any]:
        return handoff_context(self.root, project_id=input["projectId"])


@dataclass
class SchedulerModule:
    root: Path

    def next(self, input: dict[str, Any] | None = None) -> dict[str, Any] | None:
        input = input or {}
        ready = ready_tasks(self.root, project_id=input.get("projectId"), limit=1)
        return ready[0] if ready else None


class HiveClient:
    """Typed local client used inside the execute sandbox."""

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.project = ProjectModule(self.root)
        self.task = TaskModule(self.root)
        self.run = RunModule(self.root)
        self.memory = MemoryModule(self.root)
        self.context = ContextModule(self.root)
        self.scheduler = SchedulerModule(self.root)


__all__ = ["HiveClient"]

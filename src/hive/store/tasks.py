"""Compatibility wrappers for canonical task storage and ready detection."""

from __future__ import annotations

from pathlib import Path

from src.hive.layout import HivePaths
from src.hive.models.task import TaskRecord
from src.hive.scheduler.query import dependency_summary as _dependency_summary
from src.hive.scheduler.query import ready_tasks as _ready_tasks
from src.hive.store.task_files import (
    claim_task as _claim_task,
    create_task as _create_task,
    get_task as _get_task,
    link_tasks as _link_tasks,
    list_tasks as _list_tasks,
    release_task as _release_task,
    save_task as _save_task,
    task_path,
    update_task as _update_task,
)


def _root(paths: HivePaths) -> Path:
    return paths.root


def list_tasks(paths: HivePaths, project_id: str | None = None) -> list[TaskRecord]:
    """Load all canonical tasks."""
    return _list_tasks(_root(paths)) if project_id is None else [
        task for task in _list_tasks(_root(paths)) if task.project_id == project_id
    ]


def load_task(paths: HivePaths, task_id: str) -> TaskRecord:
    """Load a single task."""
    return _get_task(_root(paths), task_id)


def save_task(paths: HivePaths, task: TaskRecord) -> TaskRecord:
    """Persist a task file."""
    _save_task(_root(paths), task)
    return task


def create_task(paths: HivePaths, task: TaskRecord) -> TaskRecord:
    """Create a new task from a TaskRecord."""
    _create_task(
        _root(paths),
        task.project_id,
        task.title,
        kind=task.kind,
        status=task.status,
        priority=task.priority,
        parent_id=task.parent_id,
        labels=task.labels,
        relevant_files=task.relevant_files,
        acceptance=task.acceptance,
        source=task.source,
        summary_md=task.summary_md,
        notes_md=task.notes_md,
        history_md=task.history_md,
    )
    return task


def update_task(paths: HivePaths, task_id: str, patch: dict) -> TaskRecord:
    """Patch an existing task."""
    return _update_task(_root(paths), task_id, patch)


def link_tasks(paths: HivePaths, src_id: str, edge_type: str, dst_id: str) -> TaskRecord:
    """Create a typed edge between two tasks."""
    return _link_tasks(_root(paths), src_id, edge_type, dst_id)


def claim_task(paths: HivePaths, task_id: str, owner: str, ttl_minutes: int = 30) -> TaskRecord:
    """Acquire a lease on a task."""
    return _claim_task(_root(paths), task_id, owner, ttl_minutes)


def release_task(paths: HivePaths, task_id: str, owner: str | None = None) -> TaskRecord:
    """Release a task claim."""
    task = _get_task(_root(paths), task_id)
    if owner and task.owner not in {None, owner}:
        raise ValueError(f"Task {task_id} is owned by {task.owner}")
    return _release_task(_root(paths), task_id)


def ready_tasks(paths: HivePaths, project_id: str | None = None) -> list[dict]:
    """Compute the ready task set."""
    return _ready_tasks(_root(paths), project_id=project_id)


def dependency_summary(paths: HivePaths) -> dict:
    """Build a task-level dependency summary for compatibility surfaces."""
    return _dependency_summary(_root(paths))

"""Canonical task-file storage."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.hive.clock import utc_now_iso
from src.hive.ids import new_id
from src.hive.models.task import TaskRecord
from src.hive.store.layout import tasks_dir
from src.security import safe_dump_agency_md, safe_load_agency_md

_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$")
_CANONICAL_SECTIONS = ("Summary", "Notes", "History")


def _parse_sections(body: str) -> tuple[dict[str, str], list[tuple[str, str]]]:
    sections: dict[str, list[str]] = {name: [] for name in _CANONICAL_SECTIONS}
    section_order: list[str] = ["Summary"]
    current = "Summary"
    for line in body.splitlines():
        match = _SECTION_RE.match(line.strip())
        if match:
            name = match.group(1).strip()
            current = name
            if name not in sections:
                sections[name] = []
            if name not in section_order:
                section_order.append(name)
            continue
        sections[current].append(line)
    canonical = {name: "\n".join(sections.get(name, [])).strip() for name in _CANONICAL_SECTIONS}
    extra_sections = [
        (name, "\n".join(sections[name]).strip())
        for name in section_order
        if name not in _CANONICAL_SECTIONS
    ]
    return canonical, extra_sections


def _serialize_sections(task: TaskRecord) -> str:
    parts = [
        "## Summary",
        task.summary_md.strip() or f"Track work for `{task.title}`.",
        "",
        "## Notes",
        task.notes_md.strip() or "- Imported or created by Hive 2.0.",
        "",
        "## History",
        task.history_md.strip() or f"- {task.created_at} bootstrap created.",
    ]
    for name, content in task.extra_sections:
        parts.extend(["", f"## {name}", content.strip()])
    return "\n".join(parts).strip()


def task_path(path: str | Path | None, task_id: str) -> Path:
    """Return the task file path."""
    return tasks_dir(path) / f"{task_id}.md"


def load_task(file_path: str | Path) -> TaskRecord:
    """Load a canonical task file."""
    parsed = safe_load_agency_md(Path(file_path))
    metadata = dict(parsed.metadata)
    sections, extra_sections = _parse_sections(parsed.content)
    extra = metadata.copy()
    known = {
        "id",
        "project_id",
        "title",
        "kind",
        "status",
        "priority",
        "parent_id",
        "owner",
        "claimed_until",
        "labels",
        "relevant_files",
        "acceptance",
        "edges",
        "created_at",
        "updated_at",
        "source",
    }
    for key in known:
        extra.pop(key, None)

    task = TaskRecord(
        id=metadata["id"],
        project_id=metadata["project_id"],
        title=metadata["title"],
        kind=metadata.get("kind", "task"),
        status=metadata.get("status", "ready"),
        priority=int(metadata.get("priority", 2)),
        parent_id=metadata.get("parent_id"),
        owner=metadata.get("owner"),
        claimed_until=metadata.get("claimed_until"),
        labels=list(metadata.get("labels", [])),
        relevant_files=list(metadata.get("relevant_files", [])),
        acceptance=list(metadata.get("acceptance", [])),
        edges=dict(metadata.get("edges", {})),
        created_at=metadata.get("created_at", utc_now_iso()),
        updated_at=metadata.get("updated_at", utc_now_iso()),
        summary_md=sections.get("Summary", ""),
        notes_md=sections.get("Notes", ""),
        history_md=sections.get("History", ""),
        extra_sections=extra_sections,
        source=dict(metadata.get("source", {})),
        metadata=extra,
        path=Path(file_path),
    )
    task.validate()
    return task


def save_task(path: str | Path | None, task: TaskRecord) -> Path:
    """Persist a canonical task file."""
    task.validate()
    task.updated_at = utc_now_iso()
    target = task.path or task_path(path, task.id)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        safe_dump_agency_md(task.to_frontmatter(), _serialize_sections(task)),
        encoding="utf-8",
    )
    task.path = target
    return target


def load_task_file(file_path: str | Path) -> TaskRecord:
    """Compatibility alias for loading task files."""
    return load_task(file_path)


def save_task_file(task: TaskRecord, file_path: str | Path) -> Path:
    """Compatibility helper for saving task files to an explicit path."""
    task.validate()
    task.updated_at = utc_now_iso()
    target = Path(file_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        safe_dump_agency_md(task.to_frontmatter(), _serialize_sections(task)),
        encoding="utf-8",
    )
    task.path = target
    return target


def list_tasks(path: str | Path | None = None) -> list[TaskRecord]:
    """List all canonical task files."""
    directory = tasks_dir(path)
    if not directory.exists():
        return []
    return [load_task(file_path) for file_path in sorted(directory.glob("task_*.md"))]


def get_task(path: str | Path | None, task_id: str) -> TaskRecord:
    """Load a single task by ID."""
    candidate = task_path(path, task_id)
    if not candidate.exists():
        raise FileNotFoundError(f"Task not found: {task_id}")
    return load_task(candidate)


def create_task(
    path: str | Path | None,
    project_id: str,
    title: str,
    *,
    kind: str = "task",
    status: str = "ready",
    priority: int = 2,
    parent_id: str | None = None,
    labels: list[str] | None = None,
    relevant_files: list[str] | None = None,
    acceptance: list[str] | None = None,
    source: dict[str, Any] | None = None,
    summary_md: str = "",
    notes_md: str = "",
    history_md: str = "",
) -> TaskRecord:
    """Create and persist a canonical task file."""
    if parent_id:
        get_task(path, parent_id)
    task = TaskRecord(
        id=new_id("task"),
        project_id=project_id,
        title=title,
        kind=kind,
        status=status,
        priority=priority,
        parent_id=parent_id,
        labels=labels or [],
        relevant_files=relevant_files or [],
        acceptance=acceptance or [],
        source=source or {},
        summary_md=summary_md,
        notes_md=notes_md,
        history_md=history_md,
    )
    save_task(path, task)
    return task


def update_task(path: str | Path | None, task_id: str, patch: dict[str, Any]) -> TaskRecord:
    """Apply an in-place patch to a task file."""
    task = get_task(path, task_id)
    if patch.get("parent_id"):
        get_task(path, patch["parent_id"])
    for key, value in patch.items():
        if hasattr(task, key):
            setattr(task, key, value)
        else:
            task.metadata[key] = value
    save_task(path, task)
    return task


def claim_task(
    path: str | Path | None, task_id: str, owner: str, ttl_minutes: int = 30
) -> TaskRecord:
    """Claim a task lease."""
    from datetime import timedelta

    from src.hive.clock import utc_now

    task = get_task(path, task_id)
    expires_at = utc_now() + timedelta(minutes=ttl_minutes)
    task.owner = owner
    task.claimed_until = expires_at.isoformat().replace("+00:00", "Z")
    if task.status in {"proposed", "ready"}:
        task.status = "claimed"
    save_task(path, task)
    return task


def release_task(path: str | Path | None, task_id: str) -> TaskRecord:
    """Release a task lease."""
    task = get_task(path, task_id)
    task.owner = None
    task.claimed_until = None
    if task.status == "claimed":
        task.status = "ready"
    save_task(path, task)
    return task


def link_tasks(path: str | Path | None, src_id: str, edge_type: str, dst_id: str) -> TaskRecord:
    """Create a typed edge between tasks."""
    task = get_task(path, src_id)
    get_task(path, dst_id)
    task.edges.setdefault(edge_type, [])
    if dst_id not in task.edges[edge_type]:
        task.edges[edge_type].append(dst_id)
    save_task(path, task)
    if edge_type in {"relates_to", "duplicates"}:
        reverse = get_task(path, dst_id)
        reverse.edges.setdefault(edge_type, [])
        if src_id not in reverse.edges[edge_type]:
            reverse.edges[edge_type].append(src_id)
            save_task(path, reverse)
    return task

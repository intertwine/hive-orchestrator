"""Shared helpers for project-scoped memory behavior."""

from __future__ import annotations

from pathlib import Path

from src.hive.store.layout import memory_project_dir, project_memory_candidates
from src.hive.store.projects import discover_projects, get_project

LEGACY_PROJECT_SCOPE = "workspace"


def resolve_project_scope_key(path: str | Path | None, project_id: str | None = None) -> str:
    """Resolve the project memory scope key for reads and writes."""
    if project_id:
        return get_project(path, project_id).id
    projects = discover_projects(path)
    if len(projects) == 1:
        return projects[0].id
    return LEGACY_PROJECT_SCOPE


def project_memory_scope_dir(path: str | Path | None, project_id: str | None = None) -> Path:
    """Return the best write target for project-local memory."""
    scope_key = resolve_project_scope_key(path, project_id)
    if scope_key == LEGACY_PROJECT_SCOPE:
        return memory_project_dir(path)
    return memory_project_dir(path, project_id=scope_key)


def project_memory_read_dirs(path: str | Path | None, project_id: str | None = None) -> list[Path]:
    """Return project-local memory directories from most-specific to fallback."""
    scope_key = resolve_project_scope_key(path, project_id)
    if scope_key == LEGACY_PROJECT_SCOPE:
        return [memory_project_dir(path)]
    return project_memory_candidates(path, project_id=scope_key)


__all__ = [
    "LEGACY_PROJECT_SCOPE",
    "project_memory_read_dirs",
    "project_memory_scope_dir",
    "resolve_project_scope_key",
]

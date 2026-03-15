"""Project discovery and persistence helpers."""

from __future__ import annotations

from pathlib import Path

from src.hive.constants import PRIORITY_MAP
from src.hive.ids import new_id
from src.hive.models.project import ProjectRecord
from src.security import safe_dump_agency_md, safe_load_agency_md


def _extract_title(content: str, fallback: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return fallback


def _priority_value(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return PRIORITY_MAP.get(value.lower(), 2)
    return 2


def discover_projects(path: str | Path | None = None) -> list[ProjectRecord]:
    """Discover projects from AGENCY.md files."""
    base = Path(path or Path.cwd())
    projects_root = base / "projects"
    if not projects_root.exists():
        return []

    projects: list[ProjectRecord] = []
    for agency_path in sorted(projects_root.glob("**/AGENCY.md")):
        parsed = safe_load_agency_md(agency_path)
        rel_slug = agency_path.parent.relative_to(projects_root).as_posix()
        project_id = parsed.metadata.get("project_id") or new_id("proj")
        title = _extract_title(parsed.content, agency_path.parent.name)
        projects.append(
            ProjectRecord(
                id=project_id,
                slug=rel_slug,
                agency_path=agency_path,
                title=title,
                status=parsed.metadata.get("status", "active"),
                priority=_priority_value(parsed.metadata.get("priority", "medium")),
                owner=parsed.metadata.get("owner"),
                metadata=parsed.metadata,
                content=parsed.content,
            )
        )
    return projects


def get_project(path: str | Path | None, project_id: str) -> ProjectRecord:
    """Get a single project by ID."""
    for project in discover_projects(path):
        if project.id == project_id:
            return project
    raise FileNotFoundError(f"Project not found: {project_id}")


def ensure_project_id(project: ProjectRecord) -> ProjectRecord:
    """Persist a generated project_id when needed."""
    if project.metadata.get("project_id"):
        return project

    project.metadata["project_id"] = project.id
    project.agency_path.write_text(
        safe_dump_agency_md(project.metadata, project.content),
        encoding="utf-8",
    )
    return project

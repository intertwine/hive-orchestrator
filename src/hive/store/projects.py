"""Project discovery and persistence helpers."""

from __future__ import annotations

from pathlib import Path
import re

from src.hive.constants import PRIORITY_MAP
from src.hive.ids import new_id
from src.hive.models.project import ProjectRecord
from src.hive.scaffold import generate_program_stub
from src.security import safe_dump_agency_md, safe_load_agency_md


SLUG_PART_RE = re.compile(r"[^a-z0-9]+")


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


def _normalize_slug(value: str) -> str:
    parts: list[str] = []
    for raw_part in value.strip().strip("/").split("/"):
        lowered = raw_part.strip().lower()
        lowered = SLUG_PART_RE.sub("-", lowered).strip("-")
        if lowered:
            parts.append(lowered)
    if not parts:
        raise ValueError("Project slug must contain at least one alphanumeric segment")
    return "/".join(parts)


def _title_from_slug(slug: str) -> str:
    label = slug.split("/")[-1].replace("-", " ").strip()
    return label.title() or "Untitled Project"


def _project_id_from_slug(slug: str) -> str:
    return slug.replace("/", "-")


def _default_agency_body(title: str, objective: str | None = None) -> str:
    mission = (
        objective or "Describe the outcome, constraints, and operating notes for this project."
    )
    return f"""# {title}

## Mission
{mission}

## Notes
Use this document for human context, links, architecture notes, and handoff details.

## Working Rules
- Keep canonical task state in `.hive/tasks/*.md`.
- Read `PROGRAM.md` before autonomous edits or evaluator runs.
- Refresh projections after state changes with `hive sync projections --json`.
"""


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
    """Get a single project by ID, slug, or path."""
    root = Path(path or Path.cwd()).resolve()
    reference = project_id.strip()
    candidate_path = Path(reference)
    if not candidate_path.is_absolute():
        candidate_path = (root / candidate_path).resolve()

    for project in discover_projects(root):
        agency_path = project.agency_path.resolve()
        if reference in {project.id, project.slug}:
            return project
        if candidate_path in {agency_path, agency_path.parent}:
            return project
    raise FileNotFoundError(f"Project not found: {project_id}")


def create_project(
    path: str | Path | None,
    slug: str,
    *,
    title: str | None = None,
    project_id: str | None = None,
    status: str = "active",
    priority: int = 2,
    objective: str | None = None,
    tags: list[str] | None = None,
) -> ProjectRecord:
    """Create a new project scaffold with AGENCY.md and PROGRAM.md."""
    root = Path(path or Path.cwd())
    normalized_slug = _normalize_slug(slug)
    resolved_title = title.strip() if title else _title_from_slug(normalized_slug)
    if project_id and project_id.strip():
        resolved_project_id = project_id.strip()
    else:
        resolved_project_id = _project_id_from_slug(normalized_slug)
    project_dir = root / "projects" / normalized_slug
    agency_path = project_dir / "AGENCY.md"
    program_path = project_dir / "PROGRAM.md"
    existing_ids = {project.id for project in discover_projects(root)}

    if agency_path.exists() or program_path.exists():
        raise FileExistsError(f"Project already exists at {project_dir}")
    if resolved_project_id in existing_ids:
        raise FileExistsError(f"A project with id '{resolved_project_id}' already exists")

    project_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "project_id": resolved_project_id,
        "status": status,
        "priority": priority,
    }
    if tags:
        metadata["tags"] = list(tags)

    agency_path.write_text(
        safe_dump_agency_md(metadata, _default_agency_body(resolved_title, objective)),
        encoding="utf-8",
    )

    generate_program_stub(project_dir)
    return get_project(root, resolved_project_id)


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


def save_project(project: ProjectRecord) -> ProjectRecord:
    """Persist project metadata and content back to AGENCY.md."""
    project.agency_path.write_text(
        safe_dump_agency_md(project.metadata, project.content),
        encoding="utf-8",
    )
    return project

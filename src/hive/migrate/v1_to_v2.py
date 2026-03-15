"""Migrate a v1 Hive repo to the v2 substrate."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

from src.hive.clock import utc_now_iso
from src.hive.projections.agency_md import sync_agency_md
from src.hive.projections.agents_md import sync_agents_md
from src.hive.projections.global_md import sync_global_md
from src.hive.runs.engine import generate_program_stub
from src.hive.store.cache import rebuild_cache
from src.hive.store.events import emit_event
from src.hive.store.layout import ensure_layout
from src.hive.store.projects import discover_projects, ensure_project_id
from src.hive.store.task_files import create_task, list_tasks
from src.hive.constants import PRIORITY_MAP

CHECKBOX_RE = re.compile(r"^(?P<indent>\s*)[-*]\s+\[(?P<checked>[ xX])\]\s+(?P<title>.+?)\s*$")
HEADING_RE = re.compile(r"^(?P<level>#{1,6})\s+(?P<title>.+?)\s*$")


@dataclass
class MigrationWarning:
    """Structured migration warning."""

    path: str
    line: int
    message: str


@dataclass
class MigrationReport:
    """Structured migration result."""

    ok: bool = True
    projects_imported: int = 0
    tasks_imported: int = 0
    warnings: list[MigrationWarning] = field(default_factory=list)
    created_files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """Serialize the report."""
        return {
            "ok": self.ok,
            "projects_imported": self.projects_imported,
            "tasks_imported": self.tasks_imported,
            "warnings": [warning.__dict__ for warning in self.warnings],
            "created_files": self.created_files,
        }


def _priority_value(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return PRIORITY_MAP.get(value.lower(), 2)
    return 2


def migrate_v1_to_v2(
    path: str | Path | None = None,
    *,
    dry_run: bool = False,
    project_filter: str | None = None,
    owner: str = "codex",
) -> MigrationReport:
    """Import v1 projects into the v2 substrate."""
    root = Path(path or Path.cwd()).resolve()
    report = MigrationReport()
    if not dry_run:
        ensure_layout(root)

    existing_tasks = list_tasks(root)
    if existing_tasks and not dry_run:
        raise ValueError("Existing .hive/tasks detected. Start from a clean v2 substrate for migration.")

    for project in discover_projects(root):
        if project_filter and project.slug != project_filter and project.id != project_filter:
            continue
        report.projects_imported += 1
        if not dry_run:
            ensure_project_id(project)
        if not project.program_path.exists():
            if not dry_run:
                stub_path = generate_program_stub(project.directory)
                report.created_files.append(str(stub_path.relative_to(root)))

        heading_stack: list[tuple[int, str]] = []
        parent_by_indent: dict[int, str] = {}
        for line_number, line in enumerate(project.content.splitlines(), start=1):
            heading_match = HEADING_RE.match(line)
            if heading_match:
                level = len(heading_match.group("level"))
                title = heading_match.group("title").strip()
                heading_stack = [entry for entry in heading_stack if entry[0] < level]
                heading_stack.append((level, title))
                continue

            checkbox_match = CHECKBOX_RE.match(line)
            if not checkbox_match:
                continue

            indent = len(checkbox_match.group("indent").replace("\t", "  "))
            title = checkbox_match.group("title").strip()
            checked = checkbox_match.group("checked").lower() == "x"
            status = "done" if checked else "ready"
            if any("blocked" in heading.lower() for _, heading in heading_stack):
                status = "blocked" if not checked else "done"

            parent_candidates = [candidate_indent for candidate_indent in parent_by_indent if candidate_indent < indent]
            parent_id = parent_by_indent[max(parent_candidates)] if parent_candidates else None
            source = {
                "imported_from": {
                    "path": str(project.agency_path.relative_to(root)),
                    "line": line_number,
                },
                "heading_path": [heading for _, heading in heading_stack],
                "checked": checked,
                "indent": indent,
                "imported_by": owner,
            }
            if not dry_run:
                task = create_task(
                    root,
                    project.id,
                    title,
                    status=status,
                    priority=_priority_value(project.metadata.get("priority", "medium")),
                    parent_id=parent_id,
                    relevant_files=list(project.metadata.get("relevant_files", [])),
                    source=source,
                    summary_md=f"Imported from `{project.agency_path.relative_to(root)}`.",
                    notes_md="\n".join(
                        [
                            f"- Imported from line {line_number}.",
                            f"- Heading ancestry: {' > '.join(source['heading_path']) or '(root)'}",
                        ]
                    ),
                    history_md=f"- {utc_now_iso()} imported from v1 checklist.",
                )
                parent_by_indent[indent] = task.id
                report.created_files.append(str(task.path.relative_to(root)))
                emit_event(
                    root,
                    actor="migration",
                    entity_type="task",
                    entity_id=task.id,
                    event_type="task.imported",
                    source="migrate",
                    payload=source,
                )
            report.tasks_imported += 1

        if not dry_run:
            emit_event(
                root,
                actor="migration",
                entity_type="project",
                entity_id=project.id,
                event_type="project.imported",
                source="migrate",
                payload={"path": str(project.agency_path.relative_to(root))},
            )

    if not dry_run:
        sync_global_md(root)
        sync_agency_md(root)
        sync_agents_md(root)
        rebuild_cache(root)

    return report

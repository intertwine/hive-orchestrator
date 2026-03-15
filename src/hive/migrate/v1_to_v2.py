"""Migrate a v1 Hive repo to the v2 substrate."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

from src.hive.clock import utc_now_iso
from src.hive.constants import PRIORITY_MAP
from src.hive.projections.agency_md import sync_agency_md
from src.hive.projections.agents_md import sync_agents_md
from src.hive.projections.global_md import sync_global_md
from src.hive.runs.engine import generate_program_stub
from src.hive.store.cache import rebuild_cache
from src.hive.store.events import emit_event, event_file
from src.hive.store.layout import ensure_layout
from src.hive.store.projects import discover_projects, ensure_project_id
from src.hive.store.task_files import create_task, get_task, list_tasks, save_task
from src.security import safe_dump_agency_md

CHECKBOX_RE = re.compile(r"^(?P<indent>\s*)[-*]\s+\[(?P<checked>[ xX])\]\s+(?P<title>.+?)\s*$")
HEADING_RE = re.compile(r"^(?P<level>#{1,6})\s+(?P<title>.+?)\s*$")
DEPENDENCY_RE = re.compile(
    r"\b(?:depends on|blocked by|requires)\s+(?P<target>[^.;]+)",
    re.IGNORECASE,
)
DUPLICATE_RE = re.compile(r"\bduplicate of\s+(?P<target>[^.;]+)", re.IGNORECASE)
SUPERSEDES_RE = re.compile(r"\bsupersedes\s+(?P<target>[^.;]+)", re.IGNORECASE)
LEGACY_TASK_HEADINGS = {"tasks", "imported legacy tasks"}


@dataclass
class MigrationWarning:
    """Structured migration warning."""

    path: str
    line: int
    message: str


@dataclass
class RelationHint:
    """Possible edge inferred from legacy text."""

    kind: str
    target_title: str
    line: int


@dataclass
class ImportedTask:
    """Parsed checkbox task awaiting canonical persistence."""

    line: int
    indent: int
    title: str
    checked: bool
    status: str
    heading_path: list[str]
    parent_line: int | None = None
    detail_lines: list[str] = field(default_factory=list)
    relation_hints: list[RelationHint] = field(default_factory=list)
    relation_blocking: bool = False
    task_id: str | None = None


@dataclass
class MigrationReport:
    """Structured migration result."""

    ok: bool = True
    projects_imported: int = 0
    tasks_imported: int = 0
    edges_inferred: int = 0
    warnings: list[MigrationWarning] = field(default_factory=list)
    created_files: list[str] = field(default_factory=list)
    rewritten_files: list[str] = field(default_factory=list)

    def add_created_file(self, relative_path: str) -> None:
        """Track a created file once."""
        if relative_path not in self.created_files:
            self.created_files.append(relative_path)

    def add_rewritten_file(self, relative_path: str) -> None:
        """Track a rewritten file once."""
        if relative_path not in self.rewritten_files:
            self.rewritten_files.append(relative_path)

    def warn(self, *, path: str, line: int, message: str) -> None:
        """Append a structured warning."""
        self.warnings.append(MigrationWarning(path=path, line=line, message=message))

    def to_dict(self) -> dict[str, object]:
        """Serialize the report."""
        return {
            "ok": self.ok,
            "projects_imported": self.projects_imported,
            "tasks_imported": self.tasks_imported,
            "edges_inferred": self.edges_inferred,
            "warnings": [warning.__dict__ for warning in self.warnings],
            "created_files": self.created_files,
            "rewritten_files": self.rewritten_files,
        }


def _priority_value(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return PRIORITY_MAP.get(value.lower(), 2)
    return 2


def _normalize_title(value: str) -> str:
    normalized = value.strip().strip("`'\"")
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = normalized.rstrip(".:;,)").strip()
    normalized = normalized.lstrip("([")
    return normalized.casefold()


def _clean_relation_target(value: str) -> str:
    target = value.strip()
    target = target.strip("`'\"")
    target = target.rstrip(").,:;")
    target = target.removeprefix("task ").strip()
    return target


def _project_matches_filter(project, project_filter: str | None, root: Path) -> bool:
    if not project_filter:
        return True
    filter_value = project_filter.strip().strip("/")
    candidates = {
        project.slug,
        project.id,
        str(project.agency_path.relative_to(root)),
        str(project.agency_path.parent.relative_to(root)),
    }
    return filter_value in candidates


def _rewrite_legacy_tasks_section(content: str, *, rewrite: bool) -> str:
    lines = content.splitlines()
    for index, line in enumerate(lines):
        heading_match = HEADING_RE.match(line)
        if not heading_match:
            continue
        title = heading_match.group("title").strip().lower()
        if title not in LEGACY_TASK_HEADINGS:
            continue
        level = len(heading_match.group("level"))
        finish = len(lines)
        for candidate_index in range(index + 1, len(lines)):
            candidate_match = HEADING_RE.match(lines[candidate_index])
            if candidate_match and len(candidate_match.group("level")) <= level:
                finish = candidate_index
                break
        if rewrite:
            replacement = [
                f"{heading_match.group('level')} Imported Legacy Tasks",
                "",
                "Legacy checkbox tasks were migrated into `.hive/tasks/*.md`.",
                "Use the generated task rollup below as the current human-readable view.",
            ]
        else:
            replacement = list(lines[index:finish])
            replacement[0] = f"{heading_match.group('level')} Imported Legacy Tasks"
        updated = lines[:index] + replacement + lines[finish:]
        return "\n".join(updated).rstrip() + "\n"
    return content


def _extract_relation_hints(
    title: str,
    detail_lines: list[str],
    *,
    line: int,
) -> list[RelationHint]:
    relation_hints: list[RelationHint] = []
    for text in [title, *detail_lines]:
        for match in DEPENDENCY_RE.finditer(text):
            relation_hints.append(
                RelationHint(
                    kind="depends_on",
                    target_title=_clean_relation_target(match.group("target")),
                    line=line,
                )
            )
        for match in DUPLICATE_RE.finditer(text):
            relation_hints.append(
                RelationHint(
                    kind="duplicate_of",
                    target_title=_clean_relation_target(match.group("target")),
                    line=line,
                )
            )
        for match in SUPERSEDES_RE.finditer(text):
            relation_hints.append(
                RelationHint(
                    kind="supersedes",
                    target_title=_clean_relation_target(match.group("target")),
                    line=line,
                )
            )
    return relation_hints


def _line_contains_relation_keyword(text: str) -> bool:
    return bool(
        DEPENDENCY_RE.search(text)
        or DUPLICATE_RE.search(text)
        or SUPERSEDES_RE.search(text)
    )


def _parse_project_tasks(project, root: Path, report: MigrationReport) -> list[ImportedTask]:
    heading_stack: list[tuple[int, str]] = []
    parent_line_by_indent: dict[int, int] = {}
    parsed_tasks: list[ImportedTask] = []
    active_task: ImportedTask | None = None
    relative_path = str(project.agency_path.relative_to(root))
    project_dependencies = project.metadata.get("dependencies") or {}
    if not isinstance(project_dependencies, dict):
        project_dependencies = {}
    project_blocked = bool(
        project.metadata.get("blocked")
        or project.metadata.get("blocking_reason")
        or project_dependencies.get("blocked_by")
    )

    for line_number, raw_line in enumerate(project.content.splitlines(), start=1):
        heading_match = HEADING_RE.match(raw_line)
        if heading_match:
            level = len(heading_match.group("level"))
            title = heading_match.group("title").strip()
            heading_stack = [entry for entry in heading_stack if entry[0] < level]
            heading_stack.append((level, title))
            active_task = None
            continue

        checkbox_match = CHECKBOX_RE.match(raw_line)
        if checkbox_match:
            indent = len(checkbox_match.group("indent").replace("\t", "  "))
            title = checkbox_match.group("title").strip()
            checked = checkbox_match.group("checked").lower() == "x"
            blocked_heading = any(
                "blocked" in heading.casefold() for _, heading in heading_stack
            )
            status = (
                "done"
                if checked
                else "blocked"
                if (blocked_heading or project_blocked)
                else "ready"
            )
            parent_candidates = [
                candidate_indent
                for candidate_indent in parent_line_by_indent
                if candidate_indent < indent
            ]
            parent_line = (
                parent_line_by_indent[max(parent_candidates)]
                if parent_candidates
                else None
            )
            if indent > 0 and parent_line is None:
                report.warn(
                    path=relative_path,
                    line=line_number,
                    message=f"Could not confidently infer parent for nested task '{title}'",
                )
            parent_line_by_indent = {
                candidate_indent: candidate_line
                for candidate_indent, candidate_line in parent_line_by_indent.items()
                if candidate_indent < indent
            }
            parent_line_by_indent[indent] = line_number
            imported = ImportedTask(
                line=line_number,
                indent=indent,
                title=title,
                checked=checked,
                status=status,
                heading_path=[heading for _, heading in heading_stack],
                parent_line=parent_line,
            )
            parsed_tasks.append(imported)
            active_task = imported
            continue

        if active_task is None:
            continue
        stripped = raw_line.strip()
        if not stripped:
            continue
        note_indent = len(raw_line) - len(raw_line.lstrip(" \t"))
        if note_indent > active_task.indent:
            active_task.detail_lines.append(stripped)
            continue
        if _line_contains_relation_keyword(stripped):
            report.warn(
                path=relative_path,
                line=line_number,
                message=(
                    f"Relation hint '{stripped}' was not indented under "
                    f"'{active_task.title}', so it was ignored."
                ),
            )
        active_task = None

    for imported in parsed_tasks:
        imported.relation_hints = _extract_relation_hints(
            imported.title,
            imported.detail_lines,
            line=imported.line,
        )
        if imported.relation_hints and not imported.checked:
            imported.status = "blocked"
            imported.relation_blocking = True
    return parsed_tasks


def _persist_project_doc(project, *, content: str) -> None:
    project.agency_path.write_text(
        safe_dump_agency_md(project.metadata, content),
        encoding="utf-8",
    )
    project.content = content


def _task_notes(imported: ImportedTask) -> str:
    lines = [
        f"- Imported from line {imported.line}.",
        f"- Heading ancestry: {' > '.join(imported.heading_path) or '(root)'}",
    ]
    if imported.detail_lines:
        lines.append("- Imported detail lines:")
        lines.extend(f"  - {detail}" for detail in imported.detail_lines)
    return "\n".join(lines)


def _resolve_relation_target(
    title_index: dict[str, list[str]],
    *,
    current_task_id: str,
    relation: RelationHint,
    report: MigrationReport,
    source_path: str,
) -> str | None:
    matches = title_index.get(_normalize_title(relation.target_title), [])
    matches = [match for match in matches if match != current_task_id]
    if not matches:
        report.warn(
            path=source_path,
            line=relation.line,
            message=f"Could not confidently infer relation target '{relation.target_title}'",
        )
        return None
    if len(matches) > 1:
        report.warn(
            path=source_path,
            line=relation.line,
            message=f"Ambiguous relation target '{relation.target_title}' matched multiple tasks",
        )
        return None
    return matches[0]


def _append_edge(root: Path, *, src_id: str, edge_type: str, dst_id: str) -> None:
    source_task = get_task(root, src_id)
    if dst_id not in source_task.edges[edge_type]:
        source_task.edges[edge_type].append(dst_id)
        save_task(root, source_task)


def _infer_edges(
    root: Path,
    *,
    imported_tasks: list[ImportedTask],
    task_by_line: dict[int, str],
    report: MigrationReport,
    source_path: str,
) -> None:
    title_index: dict[str, list[str]] = {}
    for imported in imported_tasks:
        if imported.task_id is None:
            continue
        title_index.setdefault(_normalize_title(imported.title), []).append(imported.task_id)

    for imported in imported_tasks:
        if imported.task_id is None:
            continue
        task = get_task(root, imported.task_id)
        if imported.parent_line and imported.parent_line in task_by_line:
            task.parent_id = task_by_line[imported.parent_line]
            save_task(root, task)

        any_blocking_resolved = False
        needs_proposed_downgrade = False
        for relation in imported.relation_hints:
            target_id = _resolve_relation_target(
                title_index,
                current_task_id=task.id,
                relation=relation,
                report=report,
                source_path=source_path,
            )
            if target_id is None:
                if (
                    relation.kind == "depends_on"
                    and imported.relation_blocking
                    and task.status == "blocked"
                    and not any_blocking_resolved
                ):
                    needs_proposed_downgrade = True
                continue
            if relation.kind == "depends_on":
                _append_edge(root, src_id=target_id, edge_type="blocks", dst_id=task.id)
                if task.status != "done":
                    task.status = "blocked"
                    save_task(root, task)
                any_blocking_resolved = True
                needs_proposed_downgrade = False
            elif relation.kind == "duplicate_of":
                _append_edge(root, src_id=target_id, edge_type="duplicates", dst_id=task.id)
            elif relation.kind == "supersedes":
                _append_edge(root, src_id=task.id, edge_type="supersedes", dst_id=target_id)
            report.edges_inferred += 1
        if needs_proposed_downgrade:
            task.status = "proposed"
            save_task(root, task)


def migrate_v1_to_v2(
    path: str | Path | None = None,
    *,
    dry_run: bool = False,
    project_filter: str | None = None,
    owner: str = "codex",
    rewrite: bool = False,
) -> MigrationReport:
    """Import v1 projects into the v2 substrate."""
    root = Path(path or Path.cwd()).resolve()
    report = MigrationReport()
    if not dry_run:
        ensure_layout(root)

    existing_tasks = list_tasks(root)
    if existing_tasks and not dry_run:
        raise ValueError(
            "Existing .hive/tasks detected. Start from a clean v2 substrate for migration."
        )

    for project in discover_projects(root):
        if not _project_matches_filter(project, project_filter, root):
            continue

        report.projects_imported += 1
        if not dry_run:
            ensure_project_id(project)

        imported_tasks = _parse_project_tasks(project, root, report)
        rewritten_content = _rewrite_legacy_tasks_section(project.content, rewrite=rewrite)
        if rewritten_content != project.content:
            report.add_rewritten_file(str(project.agency_path.relative_to(root)))
            if not dry_run:
                _persist_project_doc(project, content=rewritten_content)

        if not project.program_path.exists():
            stub_path = project.directory / "PROGRAM.md"
            if not dry_run:
                stub_path = generate_program_stub(project.directory)
            report.add_created_file(str(stub_path.relative_to(root)))

        task_by_line: dict[int, str] = {}
        source_path = str(project.agency_path.relative_to(root))
        for imported in imported_tasks:
            source = {
                "imported_from": {
                    "path": source_path,
                    "line": imported.line,
                },
                "heading_path": imported.heading_path,
                "checked": imported.checked,
                "indent": imported.indent,
                "imported_by": owner,
            }
            if not dry_run:
                task = create_task(
                    root,
                    project.id,
                    imported.title,
                    status=imported.status,
                    priority=_priority_value(project.metadata.get("priority", "medium")),
                    labels=list(project.metadata.get("tags", [])),
                    relevant_files=list(project.metadata.get("relevant_files", [])),
                    source=source,
                    summary_md=f"Imported from `{source_path}`.",
                    notes_md=_task_notes(imported),
                    history_md=f"- {utc_now_iso()} imported from v1 checklist.",
                )
                imported.task_id = task.id
                task_by_line[imported.line] = task.id
                report.add_created_file(str(task.path.relative_to(root)))
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
            _infer_edges(
                root,
                imported_tasks=imported_tasks,
                task_by_line=task_by_line,
                report=report,
                source_path=source_path,
            )
            _ = emit_event(
                root,
                actor="migration",
                entity_type="project",
                entity_id=project.id,
                event_type="project.imported",
                source="migrate",
                payload={"path": source_path},
            )
            report.add_created_file(str(event_file(root).relative_to(root)))

    if not dry_run:
        sync_global_md(root)
        sync_agency_md(root)
        sync_agents_md(root)
        rebuild_cache(root)

    return report

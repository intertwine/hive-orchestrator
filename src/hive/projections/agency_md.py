"""Projection renderer for project AGENCY.md files."""

from __future__ import annotations

from pathlib import Path

from src.hive.store.projects import discover_projects
from src.hive.store.task_files import list_tasks

TASK_BEGIN = "<!-- hive:begin task-rollup -->"
TASK_END = "<!-- hive:end task-rollup -->"
RUN_BEGIN = "<!-- hive:begin recent-runs -->"
RUN_END = "<!-- hive:end recent-runs -->"


def _render_task_rollup(project_id: str, path: str | Path | None = None) -> str:
    tasks = [task for task in list_tasks(path) if task.project_id == project_id]
    lines = [
        "## Task Rollup",
        "",
        "| ID | Status | Priority | Owner | Title |",
        "|---|---|---:|---|---|",
    ]
    for task in sorted(tasks, key=lambda item: (item.priority, item.title.lower())):
        lines.append(
            f"| {task.id} | {task.status} | {task.priority} | {task.owner or ''} | {task.title} |"
        )
    if len(lines) == 4:
        lines.append("| No imported tasks | - | - | - | - |")
    return "\n".join(lines)


def _render_recent_runs(project_id: str, path: str | Path | None = None) -> str:
    runs_root = Path(path or Path.cwd()) / ".hive" / "runs"
    lines = [
        "## Recent Runs",
        "",
        "| Run | Status | Task |",
        "|---|---|---|",
    ]
    if runs_root.exists():
        for metadata_path in sorted(runs_root.glob("*/metadata.json"), reverse=True):
            import json

            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if metadata.get("project_id") != project_id:
                continue
            lines.append(f"| {metadata['id']} | {metadata['status']} | {metadata['task_id']} |")
    if len(lines) == 4:
        lines.append("| No runs | - | - |")
    return "\n".join(lines)


def sync_agency_md(path: str | Path | None = None) -> list[Path]:
    """Update all AGENCY.md files with generated rollups."""
    from src.hive.projections.common import replace_marker_block

    updated_paths: list[Path] = []
    for project in discover_projects(path):
        content = project.agency_path.read_text(encoding="utf-8")
        updated = replace_marker_block(
            content, TASK_BEGIN, TASK_END, _render_task_rollup(project.id, path)
        )
        updated = replace_marker_block(
            updated, RUN_BEGIN, RUN_END, _render_recent_runs(project.id, path)
        )
        project.agency_path.write_text(updated, encoding="utf-8")
        updated_paths.append(project.agency_path)
    return updated_paths

"""Projection renderer for GLOBAL.md."""

from __future__ import annotations

from pathlib import Path

from src.hive.projections.common import replace_marker_block
from src.hive.scheduler.query import project_summary

BEGIN = "<!-- hive:begin projects -->"
END = "<!-- hive:end projects -->"


def render_projects_table(path: str | Path | None = None) -> str:
    """Render the GLOBAL.md generated project rollup."""
    projects = project_summary(path)
    lines = [
        "## Projects",
        "",
        "| Project | ID | Status | Priority | Ready | In Progress | Blocked |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for project in projects:
        lines.append(
            f"| {project['title']} | {project['id']} | {project['status']} | "
            f"{project['priority']} | {project['ready']} | {project['in_progress']} | "
            f"{project['blocked']} |"
        )
    if len(lines) == 4:
        lines.append("| No projects | - | - | - | - | - | - |")
    return "\n".join(lines)


def sync_global_md(path: str | Path | None = None) -> Path:
    """Update GLOBAL.md with the generated project rollup."""
    root = Path(path or Path.cwd())
    global_path = root / "GLOBAL.md"
    content = global_path.read_text(encoding="utf-8")
    updated = replace_marker_block(content, BEGIN, END, render_projects_table(root))
    global_path.write_text(updated, encoding="utf-8")
    return global_path

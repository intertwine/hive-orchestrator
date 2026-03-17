#!/usr/bin/env python3
"""Legacy dashboard compatibility helpers.

The primary human control surface in Hive 2.2 is the React observe-and-steer console
served by ``hive console serve``. This module sticks around only so older imports and
tests can keep using the data-loading helpers without depending on Streamlit.
"""

from __future__ import annotations

import glob
import os
from pathlib import Path

from src.hive.console.state import (
    build_home_view as build_console_home_view,
    build_inbox as build_console_inbox,
    list_runs as list_console_runs,
    load_run_detail as load_console_run_detail,
    load_run_timeline as load_console_run_timeline,
)
from src.hive.context_bundle import build_context_bundle, generate_file_tree as render_file_tree
from src.hive.scheduler.query import ready_tasks
from src.hive.workspace import sync_workspace
from src.security import safe_dump_agency_md, safe_load_agency_md


def load_project(project_path: str):
    """Load and parse an AGENCY.md file using safe YAML loading."""
    try:
        parsed = safe_load_agency_md(Path(project_path))
    except Exception:
        return None
    return {
        "path": project_path,
        "metadata": parsed.metadata,
        "content": parsed.content,
        "raw": safe_dump_agency_md(parsed.metadata, parsed.content),
    }


def discover_projects(base_path: Path):
    """Find all AGENCY.md files in the projects directory."""
    projects_dir = base_path / "projects"
    if not projects_dir.exists():
        return []

    agency_files = glob.glob(str(projects_dir / "**" / "AGENCY.md"), recursive=True)
    projects = [project for path in agency_files if (project := load_project(path))]
    return sorted(projects, key=lambda item: item["metadata"].get("project_id", ""))


def generate_file_tree(
    directory: Path, prefix: str = "", max_depth: int = 3, current_depth: int = 0
):
    """Generate a text-based file tree."""
    return render_file_tree(directory, prefix, max_depth, current_depth)


def generate_deep_work_context(project_path: str, base_path: Path):
    """Generate a v2 startup context package for focused work sessions."""
    return generate_hive_context(project_path, base_path, mode="startup", profile="light")


def list_project_ready_tasks(base_path: Path, project_id: str, limit: int = 10):
    """Return canonical ready tasks for a single project."""
    return ready_tasks(base_path, project_id=project_id, limit=limit)


def sync_hive_views(base_path: Path):
    """Refresh generated projections and the derived cache."""
    sync_workspace(base_path)


def list_runs(
    base_path: Path,
    *,
    project_id: str | None = None,
    driver: str | None = None,
    health: str | None = None,
) -> list[dict]:
    """Return normalized runs for the observe console."""
    return list_console_runs(base_path, project_id=project_id, driver=driver, health=health)


def load_run_timeline(base_path: Path, run_id: str) -> list[dict]:
    """Load a per-run event timeline, falling back to the global audit log."""
    return load_console_run_timeline(base_path, run_id)


def build_inbox(base_path: Path) -> list[dict]:
    """Return typed attention items for the operator inbox."""
    return build_console_inbox(base_path)


def build_home_view(base_path: Path) -> dict:
    """Answer the five core operator questions from one payload."""
    return build_console_home_view(base_path)


def load_run_detail(base_path: Path, run_id: str) -> dict:
    """Return the detail payload for a single run."""
    return load_console_run_detail(base_path, run_id)


def generate_hive_context(
    project_path: str,
    base_path: Path,
    *,
    mode: str = "startup",
    profile: str = "light",
):
    """Generate a formatted Hive v2 startup or handoff context."""
    project_data = load_project(project_path)
    if not project_data:
        return None

    project_id = project_data["metadata"].get("project_id", "unknown")
    try:
        bundle = build_context_bundle(
            base_path,
            project_ref=project_id,
            mode=mode,
            profile=profile,
        )
    except FileNotFoundError:
        return None
    return str(bundle["rendered"])


def main():
    """Explain how to launch the primary React console."""
    root = Path(os.getenv("HIVE_BASE_PATH", os.getcwd())).resolve()
    raise SystemExit(
        "Streamlit is no longer the primary Hive dashboard. "
        f"Run `hive console serve --path {root}` and open /console/ instead."
    )


if __name__ == "__main__":  # pragma: no cover - manual entrypoint only.
    main()

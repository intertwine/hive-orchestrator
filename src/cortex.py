#!/usr/bin/env python3
"""
Hive v2 compatibility wrapper.

`src.cortex` used to be the center of the v1 LLM orchestration engine. Hive 2.0
is now CLI-first and `.hive/`-backed, so this module intentionally exposes only
the thin compatibility surfaces that are still useful:

- projection sync (`python -m src.cortex`)
- ready task queries (`--ready`)
- dependency summaries (`--deps`)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from src.hive.common import isoformat_z
from src.hive.projections.agency_md import sync_agency_md
from src.hive.projections.agents_md import sync_agents_md
from src.hive.projections.global_md import sync_global_md
from src.hive.scheduler.query import dependency_summary, ready_tasks
from src.hive.store.cache import rebuild_cache
from src.hive.store.projects import discover_projects as discover_v2_projects
from src.security import safe_dump_agency_md, safe_load_agency_md


class CortexError(Exception):
    """Base exception for compatibility-wrapper failures."""


def _project_to_dict(project: Any) -> dict[str, Any]:
    metadata = dict(project.metadata)
    metadata.setdefault("project_id", project.id)
    return {
        "project_id": project.id,
        "path": str(project.agency_path),
        "metadata": metadata,
        "content": project.content,
        "raw": safe_dump_agency_md(metadata, project.content),
    }


def _sync_global_metadata(root: Path) -> None:
    global_path = root / "GLOBAL.md"
    if not global_path.exists():
        return
    try:
        parsed = safe_load_agency_md(global_path)
    except Exception as exc:  # pylint: disable=broad-except
        print(
            f"Warning: skipping GLOBAL.md timestamp refresh due to parse error: {exc}",
            file=sys.stderr,
        )
        return
    timestamp = isoformat_z()
    # Keep the legacy key for compatibility while making the newer meaning explicit.
    parsed.metadata["last_cortex_run"] = timestamp
    parsed.metadata["last_sync"] = timestamp
    global_path.write_text(
        safe_dump_agency_md(parsed.metadata, parsed.content),
        encoding="utf-8",
    )


def run_v2_projection_sync(base_path: str | Path | None, output_json: bool = False) -> bool:
    """Rebuild cache and refresh generated projections."""
    root = Path(base_path or os.getcwd())
    _sync_global_metadata(root)
    rebuild_cache(root)
    sync_global_md(root)
    sync_agency_md(root)
    sync_agents_md(root)

    payload = {
        "action": "projection_sync",
        "generated_at": isoformat_z(),
        "ok": True,
        "path": str(root),
        "version": "2.0",
    }
    if output_json:
        print(json.dumps(payload, indent=2))
    else:
        print("=" * 60)
        print("HIVE V2 PROJECTION SYNC")
        print("=" * 60)
        print(f"Path: {root}")
        print("Rebuilt cache and synced GLOBAL.md / AGENCY.md / AGENTS.md projections")
        print("=" * 60)
    return True


class Cortex:
    """Thin compatibility facade over Hive v2 queries and sync operations."""

    def __init__(self, base_path: str | None = None):
        self.base_path = Path(base_path or os.getcwd())
        self.global_file = self.base_path / "GLOBAL.md"
        self.projects_dir = self.base_path / "projects"

    def read_global_context(self) -> dict[str, Any] | None:
        """Read GLOBAL.md for compatibility callers."""
        if not self.global_file.exists():
            return None
        try:
            parsed = safe_load_agency_md(self.global_file)
        except Exception:  # pylint: disable=broad-except
            return None
        return {
            "path": str(self.global_file),
            "metadata": dict(parsed.metadata),
            "content": parsed.content,
        }

    def discover_projects(self) -> list[dict[str, Any]]:
        """Return project metadata in the legacy dict shape."""
        return [_project_to_dict(project) for project in discover_v2_projects(self.base_path)]

    def ready_work(self, projects: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        """Return canonical ready tasks."""
        del projects  # Compatibility parameter retained intentionally.
        return ready_tasks(self.base_path)

    def format_ready_work_json(self, ready: list[dict[str, Any]]) -> str:
        """Serialize ready tasks to JSON."""
        return json.dumps(
            {
                "version": "2.0",
                "generated_at": isoformat_z(),
                "tasks": ready,
            },
            indent=2,
        )

    def format_ready_work_text(self, ready: list[dict[str, Any]]) -> str:
        """Render human-readable ready task output."""
        lines = ["=" * 60, "READY TASKS (Hive v2)", "=" * 60]
        if not ready:
            lines.append("No canonical ready tasks found.")
        else:
            for task in ready:
                lines.append(
                    f"- {task['id']} [{task['status']}] "
                    f"p{task['priority']} {task['project_id']}: {task['title']}"
                )
        lines.append("=" * 60)
        return "\n".join(lines)

    def run_ready(self, output_json: bool = False) -> bool:
        """Print ready tasks in text or JSON form."""
        ready = self.ready_work()
        print(
            self.format_ready_work_json(ready)
            if output_json
            else self.format_ready_work_text(ready)
        )
        return True

    def get_dependency_summary(
        self,
        projects: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Return the v2 dependency summary."""
        del projects  # Compatibility parameter retained intentionally.
        return dependency_summary(self.base_path)

    def is_blocked(
        self,
        project_id: str,
        projects: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Return blocked status for a single project."""
        del projects  # Compatibility parameter retained intentionally.
        summary = self.get_dependency_summary()
        entry = next(
            (item for item in summary["projects"] if item["project_id"] == project_id), None
        )
        if not entry:
            return {
                "project_id": project_id,
                "is_blocked": False,
                "blocking_projects": [],
                "blocking_reasons": [],
            }
        return {
            "project_id": project_id,
            "is_blocked": bool(entry["effectively_blocked"]),
            "blocking_projects": list(entry["blocked_by"]),
            "blocking_reasons": list(entry["blocking_reasons"]),
        }

    def format_deps_json(self, summary: dict[str, Any]) -> str:
        """Serialize dependency summary to JSON."""
        payload = {"version": "2.0", "generated_at": isoformat_z(), **summary}
        return json.dumps(payload, indent=2)

    def format_deps_text(self, summary: dict[str, Any]) -> str:
        """Render a human-readable dependency summary."""
        lines = ["=" * 60, "TASK DEPENDENCY SUMMARY (Hive v2)", "=" * 60]
        if not summary["projects"]:
            lines.append("No projects found.")
        else:
            for entry in summary["projects"]:
                blocked = "blocked" if entry["effectively_blocked"] else "ready"
                deps = ", ".join(entry["blocked_by"]) if entry["blocked_by"] else "-"
                lines.append(
                    f"- {entry['project_id']} [{entry['status']}] {blocked} "
                    f"(depends on: {deps})"
                )
        lines.append("=" * 60)
        return "\n".join(lines)

    def run_deps(self, output_json: bool = False) -> bool:
        """Print dependency summary in text or JSON form."""
        summary = self.get_dependency_summary()
        print(self.format_deps_json(summary) if output_json else self.format_deps_text(summary))
        return True

    def run(self) -> bool:
        """Run the v2 projection sync compatibility path."""
        return run_v2_projection_sync(self.base_path, output_json=False)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Hive v2 compatibility wrapper for ready/deps/sync commands",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run v2 projection sync
  python -m src.cortex

  # Find ready work
  python -m src.cortex --ready

  # Show dependency summary
  python -m src.cortex --deps

  # Output as JSON for programmatic use
  python -m src.cortex --ready --json
  python -m src.cortex --deps --json
  python -m src.cortex --json
        """,
    )
    parser.add_argument("--ready", "-r", action="store_true", help="Show ready canonical tasks")
    parser.add_argument("--deps", "-d", action="store_true", help="Show dependency summary")
    parser.add_argument("--json", "-j", action="store_true", help="Output JSON")
    parser.add_argument(
        "--path",
        "-p",
        type=str,
        default=None,
        help="Base path for the workspace (default: current directory)",
    )
    return parser.parse_args()


def main() -> None:
    """CLI entry point."""
    args = parse_args()
    cortex = Cortex(base_path=args.path)

    if args.ready:
        success = cortex.run_ready(output_json=args.json)
    elif args.deps:
        success = cortex.run_deps(output_json=args.json)
    else:
        success = run_v2_projection_sync(args.path or os.getcwd(), output_json=args.json)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

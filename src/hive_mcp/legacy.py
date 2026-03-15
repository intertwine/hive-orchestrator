"""Legacy MCP helper functions kept for compatibility tests."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.security import safe_dump_agency_md, safe_load_agency_md, validate_path_within_base


def format_project(project: dict[str, Any]) -> dict[str, Any]:
    """Format a project for JSON output."""
    return {
        "project_id": project["project_id"],
        "path": project["path"],
        "status": project["metadata"].get("status"),
        "owner": project["metadata"].get("owner"),
        "blocked": project["metadata"].get("blocked", False),
        "blocking_reason": project["metadata"].get("blocking_reason"),
        "priority": project["metadata"].get("priority", "medium"),
        "tags": project["metadata"].get("tags", []),
        "last_updated": project["metadata"].get("last_updated"),
        "dependencies": project["metadata"].get("dependencies", {}),
    }


def update_project_field(
    project_path: str, field: str, value: Any, base_path: str | None = None
) -> bool:
    """Update a frontmatter field in a project's AGENCY.md file."""
    try:
        file_path = Path(project_path)

        if base_path and not validate_path_within_base(file_path, Path(base_path)):
            return False
        if not file_path.exists():
            return False

        parsed = safe_load_agency_md(file_path)
        parsed.metadata[field] = value
        parsed.metadata["last_updated"] = (
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )

        with open(file_path, "w", encoding="utf-8") as handle:
            handle.write(safe_dump_agency_md(parsed.metadata, parsed.content))

        return True
    except Exception:  # pylint: disable=broad-except
        return False


def add_agent_note(project_path: str, agent: str, note: str, base_path: str | None = None) -> bool:
    """Add a timestamped note to the Agent Notes section of AGENCY.md."""
    try:
        file_path = Path(project_path)

        if base_path and not validate_path_within_base(file_path, Path(base_path)):
            return False
        if not file_path.exists():
            return False

        parsed = safe_load_agency_md(file_path)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        truncated_note = note[:2000] if len(note) > 2000 else note
        new_note = f"- **{timestamp} - {agent}**: {truncated_note}"
        content = parsed.content.strip()

        if "## Agent Notes" in content:
            parts = content.split("## Agent Notes")
            after_header = parts[1].strip() if len(parts) >= 2 else ""
            updated_notes = f"{new_note}\n{after_header}" if after_header else new_note
            content = f"{parts[0].strip()}\n\n## Agent Notes\n{updated_notes}"
        else:
            content = f"{content}\n\n## Agent Notes\n{new_note}"

        parsed.metadata["last_updated"] = (
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )

        with open(file_path, "w", encoding="utf-8") as handle:
            handle.write(safe_dump_agency_md(parsed.metadata, content))

        return True
    except Exception:  # pylint: disable=broad-except
        return False


__all__ = ["add_agent_note", "format_project", "update_project_field"]

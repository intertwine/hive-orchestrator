"""Shared payload builders for public Hive surfaces."""

from __future__ import annotations


def project_payload(project) -> dict[str, object]:
    """Return the canonical project payload shared across CLI, control, and context surfaces."""
    return {
        "id": project.id,
        "slug": project.slug,
        "title": project.title,
        "status": project.status,
        "priority": project.priority,
        "owner": project.owner,
        "path": str(project.agency_path),
        "program_path": str(project.program_path),
    }

"""Task record model."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.hive.clock import utc_now_iso
from src.hive.constants import EDGE_TYPES, TASK_KINDS, TASK_STATUSES


def _default_edges() -> dict[str, list[str]]:
    return {edge_type: [] for edge_type in EDGE_TYPES}


@dataclass
class TaskRecord:
    """Canonical task file representation."""

    id: str
    project_id: str
    title: str
    kind: str = "task"
    status: str = "ready"
    priority: int = 2
    parent_id: str | None = None
    owner: str | None = None
    claimed_until: str | None = None
    labels: list[str] = field(default_factory=list)
    relevant_files: list[str] = field(default_factory=list)
    acceptance: list[str] = field(default_factory=list)
    edges: dict[str, list[str]] = field(default_factory=_default_edges)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    summary_md: str = ""
    notes_md: str = ""
    history_md: str = ""
    source: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    path: Path | None = None

    def validate(self) -> None:
        """Validate task invariants."""
        if self.kind not in TASK_KINDS:
            raise ValueError(f"Unsupported task kind: {self.kind}")
        if self.status not in TASK_STATUSES:
            raise ValueError(f"Unsupported task status: {self.status}")
        unknown_edges = set(self.edges) - EDGE_TYPES
        if unknown_edges:
            raise ValueError(f"Unsupported edge types: {sorted(unknown_edges)}")
        for edge_type in EDGE_TYPES:
            self.edges.setdefault(edge_type, [])

    def to_frontmatter(self) -> dict[str, Any]:
        """Serialize to frontmatter while preserving unknown keys."""
        metadata = dict(self.metadata)
        metadata.update(
            {
                "id": self.id,
                "project_id": self.project_id,
                "title": self.title,
                "kind": self.kind,
                "status": self.status,
                "priority": self.priority,
                "parent_id": self.parent_id,
                "owner": self.owner,
                "claimed_until": self.claimed_until,
                "labels": self.labels,
                "relevant_files": self.relevant_files,
                "acceptance": self.acceptance,
                "edges": self.edges,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
                "source": self.source,
            }
        )
        return metadata


Task = TaskRecord

__all__ = ["EDGE_TYPES", "TASK_STATUSES", "Task", "TaskRecord"]

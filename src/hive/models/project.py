"""Project model."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ProjectRecord:
    """Discovered project metadata."""

    id: str
    slug: str
    agency_path: Path
    title: str
    status: str = "active"
    priority: int = 2
    owner: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    content: str = ""

    @property
    def directory(self) -> Path:
        """Project directory."""
        return self.agency_path.parent

    @property
    def program_path(self) -> Path:
        """Path to PROGRAM.md."""
        return self.directory / "PROGRAM.md"

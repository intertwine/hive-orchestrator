"""Program contract model."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ProgramRecord:
    """Canonical PROGRAM.md representation."""

    path: Path
    body: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """Validate the MVP program schema."""
        required = ["program_version", "mode", "default_executor"]
        missing = [key for key in required if key not in self.metadata]
        if missing:
            raise ValueError(f"PROGRAM.md is missing required fields: {', '.join(missing)}")

        for key in ["budgets", "paths", "commands", "evaluators", "promotion", "escalation"]:
            self.metadata.setdefault(key, {} if key != "evaluators" else [])

        if not isinstance(self.metadata["evaluators"], list):
            raise ValueError("PROGRAM.md evaluators must be a list")

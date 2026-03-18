"""Base types for v2.3 sandbox probing."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SandboxProbe:
    """Availability and truthfulness payload for one backend."""

    backend: str
    available: bool
    isolation_class: str
    configured: bool | None = None
    supported_profiles: list[str] = field(default_factory=list)
    experimental: bool = False
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the probe for JSON output."""
        return asdict(self)


__all__ = ["SandboxProbe"]

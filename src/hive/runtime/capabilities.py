"""Truthful capability models for the v2.3 runtime contract."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from src.hive.clock import utc_now_iso


@dataclass
class CapabilitySurface:
    """One capability view: declared, probed-effective, or run-effective."""

    launch_mode: str = "staged"
    session_persistence: str = "none"
    event_stream: str = "none"
    approvals: list[str] = field(default_factory=list)
    skills: str = "file_projection"
    worktrees: str = "host_managed"
    subagents: str = "none"
    native_sandbox: str = "none"
    outer_sandbox_required: bool = True
    artifacts: list[str] = field(default_factory=list)
    reroute_export: str = "none"

    def to_dict(self) -> dict[str, Any]:
        """Serialize the capability surface."""
        return asdict(self)


@dataclass
class CapabilitySnapshot:
    """Truthful per-driver or per-run capability snapshot."""

    driver: str
    driver_version: str = "0.0.0"
    captured_at: str = field(default_factory=utc_now_iso)
    declared: CapabilitySurface = field(default_factory=CapabilitySurface)
    probed: dict[str, Any] = field(default_factory=dict)
    effective: CapabilitySurface = field(default_factory=CapabilitySurface)
    confidence: dict[str, str] = field(default_factory=dict)
    evidence: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the snapshot for JSON output."""
        return {
            "driver": self.driver,
            "driver_version": self.driver_version,
            "captured_at": self.captured_at,
            "declared": self.declared.to_dict(),
            "probed": dict(self.probed),
            "effective": self.effective.to_dict(),
            "confidence": dict(self.confidence),
            "evidence": dict(self.evidence),
        }


def capability_surface(**kwargs: Any) -> CapabilitySurface:
    """Small helper to keep driver probe code concise."""
    return CapabilitySurface(**kwargs)


__all__ = ["CapabilitySnapshot", "CapabilitySurface", "capability_surface"]

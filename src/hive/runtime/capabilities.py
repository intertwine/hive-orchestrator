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
    attach_supported: bool = False
    managed_supported: bool = False
    steering: str = "none"
    approvals: list[str] = field(default_factory=list)
    skills: str = "file_projection"
    worktrees: str = "host_managed"
    subagents: str = "none"
    native_sandbox: str = "none"
    context_projection: str = "none"
    outer_sandbox_owned_by_hive: bool = False
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
    # v2.4 adapter-family metadata — defaults preserve backward compat with existing drivers.
    governance_mode: str = "governed"
    integration_level: str = "managed"
    adapter_family: str = "legacy_driver"

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
            "governance_mode": self.governance_mode,
            "integration_level": self.integration_level,
            "adapter_family": self.adapter_family,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> CapabilitySnapshot:
        """Hydrate a snapshot from serialized JSON data."""
        return cls(
            driver=str(payload.get("driver", "")),
            driver_version=str(payload.get("driver_version", "0.0.0")),
            captured_at=str(payload.get("captured_at", utc_now_iso())),
            declared=CapabilitySurface(**dict(payload.get("declared") or {})),
            probed=dict(payload.get("probed") or {}),
            effective=CapabilitySurface(**dict(payload.get("effective") or {})),
            confidence={str(key): str(value) for key, value in dict(payload.get("confidence") or {}).items()},
            evidence={str(key): str(value) for key, value in dict(payload.get("evidence") or {}).items()},
            governance_mode=str(payload.get("governance_mode", "governed")),
            integration_level=str(payload.get("integration_level", "managed")),
            adapter_family=str(payload.get("adapter_family", "legacy_driver")),
        )


def capability_surface(**kwargs: Any) -> CapabilitySurface:
    """Small helper to keep driver probe code concise."""
    return CapabilitySurface(**kwargs)


__all__ = ["CapabilitySnapshot", "CapabilitySurface", "capability_surface"]

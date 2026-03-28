"""Core v2.4 adapter-family models and enums."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from src.hive.clock import utc_now_iso
from src.hive.runtime.capabilities import CapabilitySnapshot


class AdapterFamily(StrEnum):
    """Discriminates the two v2.4 adapter families from legacy drivers."""

    WORKER_SESSION = "worker_session"
    DELEGATE_GATEWAY = "delegate_gateway"
    LEGACY_DRIVER = "legacy_driver"


class IntegrationLevel(StrEnum):
    """How deeply a harness is integrated with Hive."""

    PACK = "pack"
    COMPANION = "companion"
    ATTACH = "attach"
    MANAGED = "managed"


class GovernanceMode(StrEnum):
    """Whether Hive is advisory or has governing authority over a session."""

    ADVISORY = "advisory"
    GOVERNED = "governed"


@dataclass
class IntegrationInfo:
    """Probe result for a v2.4 adapter integration."""

    adapter: str
    adapter_family: AdapterFamily
    governance_mode: GovernanceMode = GovernanceMode.GOVERNED
    integration_level: IntegrationLevel = IntegrationLevel.PACK
    version: str = "0.0.0"
    available: bool = True
    capability_snapshot: CapabilitySnapshot | None = None
    supported_levels: list[IntegrationLevel] = field(default_factory=list)
    supported_governance_modes: list[GovernanceMode] = field(default_factory=list)
    install_path: str | None = None
    configuration_problems: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSON output."""
        payload: dict[str, Any] = {
            "adapter": self.adapter,
            "adapter_family": str(self.adapter_family),
            "governance_mode": str(self.governance_mode),
            "integration_level": str(self.integration_level),
            "version": self.version,
            "available": self.available,
            "configuration_problems": list(self.configuration_problems),
            "next_steps": list(self.next_steps),
            "notes": list(self.notes),
        }
        if self.supported_levels:
            payload["supported_levels"] = [str(level) for level in self.supported_levels]
        if self.supported_governance_modes:
            payload["supported_governance_modes"] = [
                str(mode) for mode in self.supported_governance_modes
            ]
        if self.install_path is not None:
            payload["install_path"] = self.install_path
        if self.capability_snapshot is not None:
            payload["capability_snapshot"] = self.capability_snapshot.to_dict()
        return payload


@dataclass
class SessionHandle:
    """Generalized session handle for v2.4 adapters."""

    session_id: str
    adapter_name: str
    adapter_family: AdapterFamily
    native_session_ref: str
    governance_mode: GovernanceMode = GovernanceMode.GOVERNED
    integration_level: IntegrationLevel = IntegrationLevel.PACK
    run_id: str | None = None
    delegate_session_id: str | None = None
    project_id: str | None = None
    task_id: str | None = None
    status: str = "active"
    attached_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize handle metadata."""
        return {
            "session_id": self.session_id,
            "adapter_name": self.adapter_name,
            "adapter_family": str(self.adapter_family),
            "native_session_ref": self.native_session_ref,
            "governance_mode": str(self.governance_mode),
            "integration_level": str(self.integration_level),
            "run_id": self.run_id,
            "delegate_session_id": self.delegate_session_id,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "status": self.status,
            "attached_at": self.attached_at,
            "metadata": dict(self.metadata),
        }


__all__ = [
    "AdapterFamily",
    "GovernanceMode",
    "IntegrationInfo",
    "IntegrationLevel",
    "SessionHandle",
]

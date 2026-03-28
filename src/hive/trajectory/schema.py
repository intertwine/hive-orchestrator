"""Normalized trajectory event vocabulary for v2.4."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.hive.clock import utc_now_iso
from src.hive.constants import TRAJECTORY_REQUIRED_KINDS, TRAJECTORY_SCHEMA_VERSION


@dataclass
class TrajectoryEvent:
    """A single normalized trajectory event."""

    seq: int
    kind: str
    harness: str = ""
    adapter_family: str = ""
    native_session_ref: str = ""
    run_id: str | None = None
    delegate_session_id: str | None = None
    project_id: str | None = None
    task_id: str | None = None
    campaign_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    raw_ref: str | None = None
    ts: str = field(default_factory=utc_now_iso)
    schema_version: str = TRAJECTORY_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSONL output."""
        return {
            "seq": self.seq,
            "kind": self.kind,
            "harness": self.harness,
            "adapter_family": self.adapter_family,
            "native_session_ref": self.native_session_ref,
            "run_id": self.run_id,
            "delegate_session_id": self.delegate_session_id,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "campaign_id": self.campaign_id,
            "payload": dict(self.payload),
            "raw_ref": self.raw_ref,
            "ts": self.ts,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TrajectoryEvent:
        """Deserialize from a parsed JSONL record."""
        return cls(
            seq=data["seq"],
            kind=data["kind"],
            harness=data.get("harness", ""),
            adapter_family=data.get("adapter_family", ""),
            native_session_ref=data.get("native_session_ref", ""),
            run_id=data.get("run_id"),
            delegate_session_id=data.get("delegate_session_id"),
            project_id=data.get("project_id"),
            task_id=data.get("task_id"),
            campaign_id=data.get("campaign_id"),
            payload=data.get("payload", {}),
            raw_ref=data.get("raw_ref"),
            ts=data.get("ts", ""),
            schema_version=data.get("schema_version", TRAJECTORY_SCHEMA_VERSION),
        )


def trajectory_event(**kwargs: Any) -> TrajectoryEvent:
    """Convenience factory for building trajectory events."""
    return TrajectoryEvent(**kwargs)


__all__ = [
    "TRAJECTORY_REQUIRED_KINDS",
    "TRAJECTORY_SCHEMA_VERSION",
    "TrajectoryEvent",
    "trajectory_event",
]

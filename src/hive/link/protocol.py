"""Hive Link message types — pure data, no I/O."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Union

from src.hive.clock import utc_now_iso

LINK_PROTOCOL_VERSION = "1"


# ---------------------------------------------------------------------------
# Message dataclasses
# ---------------------------------------------------------------------------


@dataclass
class LinkHello:
    """Session initialization from harness to Hive."""

    type: str = "hello"
    protocol_version: str = LINK_PROTOCOL_VERSION
    harness: str = ""
    adapter_family: str = ""
    integration_level: str = "pack"
    native_version: str = ""
    ts: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "protocol_version": self.protocol_version,
            "harness": self.harness,
            "adapter_family": self.adapter_family,
            "integration_level": self.integration_level,
            "native_version": self.native_version,
            "ts": self.ts,
        }


@dataclass
class LinkAttach:
    """Request to bind a native session to a Hive run or delegate session."""

    type: str = "attach"
    native_session_ref: str = ""
    project_id: str | None = None
    task_id: str | None = None
    campaign_id: str | None = None
    requested_governance: str = "advisory"
    ts: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "native_session_ref": self.native_session_ref,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "campaign_id": self.campaign_id,
            "requested_governance": self.requested_governance,
            "ts": self.ts,
        }


@dataclass
class LinkAttachOk:
    """Confirmation that a session has been bound."""

    type: str = "attach_ok"
    run_id: str | None = None
    delegate_session_id: str | None = None
    effective_governance: str = "advisory"
    capabilities: dict[str, Any] = field(default_factory=dict)
    ts: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "run_id": self.run_id,
            "delegate_session_id": self.delegate_session_id,
            "effective_governance": self.effective_governance,
            "capabilities": dict(self.capabilities),
            "ts": self.ts,
        }


@dataclass
class LinkEvent:
    """Normalized event from harness to Hive."""

    type: str = "event"
    event: dict[str, Any] = field(default_factory=dict)
    ts: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "event": dict(self.event), "ts": self.ts}


@dataclass
class LinkArtifact:
    """Artifact published from harness to Hive."""

    type: str = "artifact"
    artifact: dict[str, Any] = field(default_factory=dict)
    ts: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "artifact": dict(self.artifact), "ts": self.ts}


@dataclass
class LinkPollActions:
    """Harness polls Hive for pending steering/approvals."""

    type: str = "poll_actions"
    native_session_ref: str = ""
    since_seq: int = 0
    ts: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "native_session_ref": self.native_session_ref,
            "since_seq": self.since_seq,
            "ts": self.ts,
        }


@dataclass
class LinkActions:
    """Hive returns pending actions to harness."""

    type: str = "actions"
    items: list[dict[str, Any]] = field(default_factory=list)
    ts: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "items": list(self.items),
            "ts": self.ts,
        }


@dataclass
class LinkHeartbeat:
    """Session health check from harness."""

    type: str = "heartbeat"
    native_session_ref: str = ""
    status: str = "alive"
    ts: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "native_session_ref": self.native_session_ref,
            "status": self.status,
            "ts": self.ts,
        }


@dataclass
class LinkClose:
    """Session termination from either side."""

    type: str = "close"
    native_session_ref: str = ""
    reason: str = ""
    ts: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "native_session_ref": self.native_session_ref,
            "reason": self.reason,
            "ts": self.ts,
        }


# ---------------------------------------------------------------------------
# Union type and message dispatch
# ---------------------------------------------------------------------------

LinkMessage = Union[
    LinkHello,
    LinkAttach,
    LinkAttachOk,
    LinkEvent,
    LinkArtifact,
    LinkPollActions,
    LinkActions,
    LinkHeartbeat,
    LinkClose,
]

LINK_MESSAGE_TYPES = (
    "hello",
    "attach",
    "attach_ok",
    "event",
    "artifact",
    "poll_actions",
    "actions",
    "heartbeat",
    "close",
)

_TYPE_MAP: dict[str, type] = {
    "hello": LinkHello,
    "attach": LinkAttach,
    "attach_ok": LinkAttachOk,
    "event": LinkEvent,
    "artifact": LinkArtifact,
    "poll_actions": LinkPollActions,
    "actions": LinkActions,
    "heartbeat": LinkHeartbeat,
    "close": LinkClose,
}


def parse_link_message(raw: dict[str, Any]) -> LinkMessage:
    """Dispatch a raw dict to the correct message dataclass."""
    msg_type = raw.get("type")
    cls = _TYPE_MAP.get(msg_type)  # type: ignore[arg-type]
    if cls is None:
        raise ValueError(f"Unknown Hive Link message type: {msg_type!r}")
    # Filter raw to only fields the dataclass accepts.
    import dataclasses

    valid_fields = {f.name for f in dataclasses.fields(cls)}
    filtered = {k: v for k, v in raw.items() if k in valid_fields}
    return cls(**filtered)


__all__ = [
    "LINK_MESSAGE_TYPES",
    "LINK_PROTOCOL_VERSION",
    "LinkActions",
    "LinkArtifact",
    "LinkAttach",
    "LinkAttachOk",
    "LinkClose",
    "LinkEvent",
    "LinkHeartbeat",
    "LinkHello",
    "LinkMessage",
    "LinkPollActions",
    "parse_link_message",
]

"""Abstract adapter contracts for the v2.4 adapter-family split."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterator

from src.hive.drivers.types import RunLaunchRequest, SteeringRequest
from src.hive.integrations.models import (
    AdapterFamily,
    GovernanceMode,
    IntegrationInfo,
    SessionHandle,
)


class AdapterBase(ABC):
    """Common surface shared by both adapter families."""

    name: str
    adapter_family: AdapterFamily

    @abstractmethod
    def probe(self) -> IntegrationInfo:
        """Return adapter capability and availability information."""

    @abstractmethod
    def stream_events(self, session: SessionHandle) -> Iterator[dict[str, Any]]:
        """Yield normalized trajectory events for an active session."""

    @abstractmethod
    def send_steer(
        self, session: SessionHandle, request: SteeringRequest
    ) -> dict[str, Any]:
        """Apply a steering action to an active session."""

    @abstractmethod
    def collect_artifacts(self, session: SessionHandle) -> dict[str, Any]:
        """Return artifacts produced during the session."""


class WorkerSessionAdapter(AdapterBase, ABC):
    """Adapter for bounded work sessions (e.g. Pi).

    The harness owns a finite coding session — Hive can open, attach to,
    steer, and close individual sessions.
    """

    adapter_family: AdapterFamily = AdapterFamily.WORKER_SESSION

    @abstractmethod
    def prepare(self, run_id: str, config: dict[str, Any]) -> dict[str, Any]:
        """Pre-session setup (e.g. workspace scaffolding)."""

    @abstractmethod
    def open_session(self, request: RunLaunchRequest) -> SessionHandle:
        """Open a new worker session for a run."""

    @abstractmethod
    def attach_session(
        self,
        native_session_ref: str,
        governance: GovernanceMode,
        run_id: str | None = None,
    ) -> SessionHandle:
        """Attach to an existing native session."""

    @abstractmethod
    def close_session(self, session: SessionHandle, reason: str) -> dict[str, Any]:
        """Close a worker session."""


class DelegateGatewayAdapter(AdapterBase, ABC):
    """Adapter for long-lived gateway harnesses (e.g. OpenClaw, Hermes).

    The harness owns a persistent gateway with multiple concurrent sessions.
    Hive attaches as an observer/steerer rather than session owner.
    """

    adapter_family: AdapterFamily = AdapterFamily.DELEGATE_GATEWAY

    @abstractmethod
    def list_sessions(self) -> list[dict[str, Any]]:
        """List active sessions on the gateway."""

    @abstractmethod
    def attach_delegate_session(
        self,
        native_session_ref: str,
        governance: GovernanceMode,
        project_id: str | None = None,
        task_id: str | None = None,
    ) -> SessionHandle:
        """Attach to an active gateway session."""

    @abstractmethod
    def publish_note(self, session: SessionHandle, note: str) -> dict[str, Any]:
        """Publish a steering note into the delegate session."""

    @abstractmethod
    def detach_delegate_session(self, session: SessionHandle) -> dict[str, Any]:
        """Detach from a gateway session without closing it."""


__all__ = [
    "AdapterBase",
    "DelegateGatewayAdapter",
    "WorkerSessionAdapter",
]

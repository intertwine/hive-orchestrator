"""Dummy WorkerSessionAdapter for testing the v2.4 adapter contract."""

from __future__ import annotations

from typing import Any, Iterator

from src.hive.clock import utc_now_iso
from src.hive.drivers.types import RunLaunchRequest, SteeringRequest
from src.hive.ids import new_id
from src.hive.integrations.base import WorkerSessionAdapter
from src.hive.integrations.models import (
    AdapterFamily,
    GovernanceMode,
    IntegrationInfo,
    IntegrationLevel,
    SessionHandle,
)
from src.hive.runtime.capabilities import CapabilitySnapshot, capability_surface


class DummyWorkerAdapter(WorkerSessionAdapter):
    """In-memory worker-session adapter for integration tests."""

    name = "dummy-worker"
    adapter_family = AdapterFamily.WORKER_SESSION

    def __init__(self) -> None:
        self._sessions: dict[str, SessionHandle] = {}
        self._steers: list[dict[str, Any]] = []

    def probe(self) -> IntegrationInfo:
        return IntegrationInfo(
            adapter=self.name,
            adapter_family=self.adapter_family,
            governance_mode=GovernanceMode.ADVISORY,
            integration_level=IntegrationLevel.ATTACH,
            version="0.1.0-dummy",
            available=True,
            capability_snapshot=CapabilitySnapshot(
                driver=self.name,
                driver_version="0.1.0-dummy",
                declared=capability_surface(
                    launch_mode="session",
                    session_persistence="session",
                    event_stream="structured_deltas",
                ),
                effective=capability_surface(
                    launch_mode="session",
                    session_persistence="session",
                    event_stream="structured_deltas",
                ),
                governance_mode="advisory",
                integration_level="attach",
                adapter_family="worker_session",
            ),
            notes=["Dummy adapter for testing — no real harness backing."],
        )

    def prepare(self, run_id: str, config: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "run_id": run_id}

    def open_session(self, request: RunLaunchRequest) -> SessionHandle:
        session = SessionHandle(
            session_id=new_id("sess"),
            adapter_name=self.name,
            adapter_family=self.adapter_family,
            native_session_ref=f"dummy:{request.run_id}",
            governance_mode=GovernanceMode.GOVERNED,
            integration_level=IntegrationLevel.MANAGED,
            run_id=request.run_id,
            status="active",
        )
        self._sessions[session.session_id] = session
        return session

    def attach_session(
        self,
        native_session_ref: str,
        governance: GovernanceMode,
        run_id: str | None = None,
    ) -> SessionHandle:
        session = SessionHandle(
            session_id=new_id("sess"),
            adapter_name=self.name,
            adapter_family=self.adapter_family,
            native_session_ref=native_session_ref,
            governance_mode=governance,
            integration_level=IntegrationLevel.ATTACH,
            run_id=run_id,
            status="active",
        )
        self._sessions[session.session_id] = session
        return session

    def stream_events(self, session: SessionHandle) -> Iterator[dict[str, Any]]:
        yield {
            "seq": 0,
            "kind": "session_start",
            "ts": utc_now_iso(),
            "native_session_ref": session.native_session_ref,
        }
        yield {
            "seq": 1,
            "kind": "assistant_delta",
            "ts": utc_now_iso(),
            "payload": {"text": "Hello from dummy worker."},
        }
        yield {
            "seq": 2,
            "kind": "session_end",
            "ts": utc_now_iso(),
            "native_session_ref": session.native_session_ref,
        }

    def send_steer(
        self, session: SessionHandle, request: SteeringRequest
    ) -> dict[str, Any]:
        record = {
            "session_id": session.session_id,
            "action": request.action,
            "ts": utc_now_iso(),
        }
        self._steers.append(record)
        return {"ok": True, **record}

    def collect_artifacts(self, session: SessionHandle) -> dict[str, Any]:
        return {"adapter": self.name, "session_id": session.session_id, "artifacts": []}

    def close_session(self, session: SessionHandle, reason: str) -> dict[str, Any]:
        session.status = "closed"
        return {"ok": True, "session_id": session.session_id, "reason": reason}


__all__ = ["DummyWorkerAdapter"]

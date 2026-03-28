"""Dummy DelegateGatewayAdapter for testing the v2.4 adapter contract."""

from __future__ import annotations

from typing import Any, Iterator

from src.hive.clock import utc_now_iso
from src.hive.drivers.types import SteeringRequest
from src.hive.ids import new_id
from src.hive.integrations.base import DelegateGatewayAdapter
from src.hive.integrations.models import (
    AdapterFamily,
    GovernanceMode,
    IntegrationInfo,
    IntegrationLevel,
    SessionHandle,
)
from src.hive.runtime.capabilities import CapabilitySnapshot, capability_surface


class DummyGatewayAdapter(DelegateGatewayAdapter):
    """In-memory delegate-gateway adapter for integration tests."""

    name = "dummy-gateway"
    adapter_family = AdapterFamily.DELEGATE_GATEWAY

    def __init__(self) -> None:
        self._sessions: dict[str, SessionHandle] = {}
        self._notes: list[dict[str, Any]] = []
        self._steers: list[dict[str, Any]] = []

    def probe(self) -> IntegrationInfo:
        return IntegrationInfo(
            adapter=self.name,
            adapter_family=self.adapter_family,
            governance_mode=GovernanceMode.ADVISORY,
            integration_level=IntegrationLevel.COMPANION,
            version="0.1.0-dummy",
            available=True,
            capability_snapshot=CapabilitySnapshot(
                driver=self.name,
                driver_version="0.1.0-dummy",
                declared=capability_surface(
                    launch_mode="gateway",
                    session_persistence="persistent",
                    event_stream="structured_deltas",
                ),
                effective=capability_surface(
                    launch_mode="gateway",
                    session_persistence="persistent",
                    event_stream="structured_deltas",
                ),
                governance_mode="advisory",
                integration_level="companion",
                adapter_family="delegate_gateway",
            ),
            notes=["Dummy gateway adapter for testing — no real harness backing."],
        )

    def list_sessions(self) -> list[dict[str, Any]]:
        return [
            {
                "native_session_ref": "gateway-sess-001",
                "status": "active",
                "owner": "agent-alpha",
            },
            {
                "native_session_ref": "gateway-sess-002",
                "status": "idle",
                "owner": "agent-beta",
            },
        ]

    def attach_delegate_session(
        self,
        native_session_ref: str,
        governance: GovernanceMode,
        project_id: str | None = None,
        task_id: str | None = None,
    ) -> SessionHandle:
        session = SessionHandle(
            session_id=new_id("dsess"),
            adapter_name=self.name,
            adapter_family=self.adapter_family,
            native_session_ref=native_session_ref,
            governance_mode=governance,
            integration_level=IntegrationLevel.COMPANION,
            delegate_session_id=new_id("del"),
            project_id=project_id,
            task_id=task_id,
            status="attached",
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
            "kind": "user_message",
            "ts": utc_now_iso(),
            "payload": {"text": "Hello from user via gateway."},
        }
        yield {
            "seq": 2,
            "kind": "assistant_delta",
            "ts": utc_now_iso(),
            "payload": {"text": "Hello from dummy gateway agent."},
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

    def publish_note(self, session: SessionHandle, note: str) -> dict[str, Any]:
        record = {
            "session_id": session.session_id,
            "note": note,
            "ts": utc_now_iso(),
        }
        self._notes.append(record)
        return {"ok": True, **record}

    def collect_artifacts(self, session: SessionHandle) -> dict[str, Any]:
        return {"adapter": self.name, "session_id": session.session_id, "artifacts": []}

    def detach_delegate_session(self, session: SessionHandle) -> dict[str, Any]:
        session.status = "detached"
        return {"ok": True, "session_id": session.session_id}


__all__ = ["DummyGatewayAdapter"]

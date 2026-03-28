"""Tests for the v2.4 OpenClaw Gateway integration (OC-1, OC-2, OC-3)."""

from __future__ import annotations

import io
import json
from typing import Any, Iterator


from src.hive.clock import utc_now_iso
from src.hive.drivers.types import SteeringRequest
from src.hive.integrations.base import DelegateGatewayAdapter
from src.hive.integrations.models import (
    AdapterFamily,
    GovernanceMode,
    IntegrationLevel,
    SessionHandle,
)
from src.hive.integrations.openclaw import (
    BridgeProbe,
    OpenClawBridgeClient,
    OpenClawGatewayAdapter,
    append_delegate_steering,
    finalize_delegate_session,
    list_delegate_sessions,
    load_delegate_session,
    persist_delegate_session,
)
from src.hive.link.protocol import LinkAttach, LinkHello
from src.hive.link.server import LinkServer


# ---------------------------------------------------------------------------
# Stub bridge client for testing without a real OpenClaw Gateway
# ---------------------------------------------------------------------------


class StubBridgeClient(OpenClawBridgeClient):
    """In-memory bridge client that simulates a reachable Gateway."""

    def __init__(
        self,
        *,
        reachable: bool = True,
        gateway_reachable: bool = True,
        sessions: list[dict[str, Any]] | None = None,
    ) -> None:
        self._reachable = reachable
        self._gateway_reachable = gateway_reachable
        self._sessions = sessions or [
            {"session_key": "oc-sess-001", "status": "active", "owner": "agent-alpha"},
            {"session_key": "oc-sess-002", "status": "idle", "owner": "agent-beta"},
        ]
        self._attached: dict[str, dict[str, Any]] = {}
        self._steers: list[dict[str, Any]] = []
        self._notes: list[dict[str, Any]] = []
        self._events: dict[str, list[dict[str, Any]]] = {
            "oc-sess-001": [
                {"kind": "session_start", "ts": utc_now_iso()},
                {
                    "kind": "user_message",
                    "ts": utc_now_iso(),
                    "payload": {"text": "Hello from user"},
                },
                {
                    "kind": "assistant_delta",
                    "ts": utc_now_iso(),
                    "payload": {"text": "Gateway response"},
                },
            ],
        }

    def probe(self) -> BridgeProbe:
        if not self._reachable:
            return BridgeProbe(
                reachable=False,
                blockers=["Bridge not installed."],
            )
        return BridgeProbe(
            reachable=True,
            version="0.1.0-stub",
            gateway_url="http://localhost:3000",
            gateway_reachable=self._gateway_reachable,
            sessions_accessible=self._gateway_reachable,
            attach_supported=True,
            steering_supported=True,
            notes=["Stub bridge for testing."],
        )

    def list_sessions(self) -> list[dict[str, Any]]:
        return list(self._sessions)

    def attach(
        self, session_key: str, *, project_id: str | None = None
    ) -> dict[str, Any]:
        self._attached[session_key] = {
            "project_id": project_id,
            "attached_at": utc_now_iso(),
        }
        return {"ok": True, "session_key": session_key, "status": "attached"}

    def stream_events(self, session_key: str) -> Iterator[dict[str, Any]]:
        return iter(self._events.get(session_key, []))

    def send_steer(
        self, session_key: str, action: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        record = {"session_key": session_key, "action": action, "payload": payload}
        self._steers.append(record)
        return {"ok": True, **record}

    def publish_note(self, session_key: str, note: str) -> dict[str, Any]:
        record = {"session_key": session_key, "note": note}
        self._notes.append(record)
        return {"ok": True, **record}

    def detach(self, session_key: str) -> dict[str, Any]:
        self._attached.pop(session_key, None)
        return {"ok": True, "session_key": session_key, "status": "detached"}


# ---------------------------------------------------------------------------
# OC-1: Install and connect
# ---------------------------------------------------------------------------


class TestOC1InstallAndConnect:
    """Scenario OC-1 — install and connect."""

    def test_probe_with_bridge_available(self):
        adapter = OpenClawGatewayAdapter(bridge=StubBridgeClient())
        info = adapter.probe()

        assert info.adapter == "openclaw"
        assert info.adapter_family == AdapterFamily.DELEGATE_GATEWAY
        assert info.governance_mode == GovernanceMode.ADVISORY
        assert info.integration_level == IntegrationLevel.ATTACH
        assert info.available is True

    def test_probe_with_bridge_unavailable(self):
        adapter = OpenClawGatewayAdapter(bridge=StubBridgeClient(reachable=False))
        info = adapter.probe()

        assert info.available is False
        assert any("blocker" in n for n in info.notes)

    def test_probe_capability_snapshot_truthful(self):
        adapter = OpenClawGatewayAdapter(bridge=StubBridgeClient())
        info = adapter.probe()
        snap = info.capability_snapshot
        assert snap is not None

        d = snap.to_dict()
        assert d["governance_mode"] == "advisory"
        assert d["integration_level"] == "attach"
        assert d["adapter_family"] == "delegate_gateway"
        # Must not claim managed support.
        assert d["effective"]["launch_mode"] == "gateway_bridge"
        assert d["effective"]["native_sandbox"] == "external"
        assert d["effective"]["outer_sandbox_required"] is False

    def test_doctor_reaches_gateway(self):
        stub = StubBridgeClient(gateway_reachable=True)
        adapter = OpenClawGatewayAdapter(bridge=stub)
        info = adapter.probe()
        snap = info.capability_snapshot
        assert snap is not None
        assert snap.probed["gateway_reachable"] is True
        assert snap.probed["sessions_accessible"] is True

    def test_list_sessions(self):
        stub = StubBridgeClient()
        adapter = OpenClawGatewayAdapter(bridge=stub)
        sessions = adapter.list_sessions()
        assert len(sessions) == 2
        assert sessions[0]["session_key"] == "oc-sess-001"

    def test_is_delegate_gateway_adapter(self):
        adapter = OpenClawGatewayAdapter(bridge=StubBridgeClient())
        assert isinstance(adapter, DelegateGatewayAdapter)

    def test_managed_mode_not_claimed(self):
        adapter = OpenClawGatewayAdapter(bridge=StubBridgeClient())
        info = adapter.probe()
        assert "Managed mode is deferred from v2.4." in info.notes


# ---------------------------------------------------------------------------
# OC-2: Attach live Gateway session
# ---------------------------------------------------------------------------


class TestOC2AttachLiveSession:
    """Scenario OC-2 — attach live Gateway session."""

    def test_attach_creates_delegate_session(self):
        stub = StubBridgeClient()
        adapter = OpenClawGatewayAdapter(bridge=stub)
        session = adapter.attach_delegate_session(
            "oc-sess-001", GovernanceMode.ADVISORY, project_id="proj-1"
        )

        assert isinstance(session, SessionHandle)
        assert session.status == "attached"
        assert session.native_session_ref == "oc-sess-001"
        assert session.delegate_session_id is not None
        assert session.project_id == "proj-1"
        assert session.governance_mode == GovernanceMode.ADVISORY

    def test_attach_always_advisory_even_if_governed_requested(self):
        """OpenClaw sessions are always advisory — Hive never owns the sandbox."""
        stub = StubBridgeClient()
        adapter = OpenClawGatewayAdapter(bridge=stub)
        session = adapter.attach_delegate_session(
            "oc-sess-001", GovernanceMode.GOVERNED
        )
        # Must downgrade to advisory.
        assert session.governance_mode == GovernanceMode.ADVISORY

    def test_stream_events_normalized(self):
        stub = StubBridgeClient()
        adapter = OpenClawGatewayAdapter(bridge=stub)
        session = adapter.attach_delegate_session(
            "oc-sess-001", GovernanceMode.ADVISORY
        )
        events = list(adapter.stream_events(session))
        assert len(events) == 3
        kinds = [e["kind"] for e in events]
        assert kinds == ["session_start", "user_message", "assistant_delta"]
        # All events must carry harness and adapter family.
        for event in events:
            assert event["harness"] == "openclaw"
            assert event["adapter_family"] == "delegate_gateway"
            assert event["delegate_session_id"] == session.delegate_session_id

    def test_steering_round_trips(self):
        stub = StubBridgeClient()
        adapter = OpenClawGatewayAdapter(bridge=stub)
        session = adapter.attach_delegate_session(
            "oc-sess-001", GovernanceMode.ADVISORY
        )
        result = adapter.send_steer(
            session, SteeringRequest(action="pause", reason="operator check")
        )
        assert result["ok"] is True
        assert len(stub._steers) == 1
        assert stub._steers[0]["action"] == "pause"

    def test_publish_note_round_trips(self):
        stub = StubBridgeClient()
        adapter = OpenClawGatewayAdapter(bridge=stub)
        session = adapter.attach_delegate_session(
            "oc-sess-001", GovernanceMode.ADVISORY
        )
        result = adapter.publish_note(session, "check the search results")
        assert result["ok"] is True
        assert len(stub._notes) == 1

    def test_detach_leaves_gateway_session_running(self):
        stub = StubBridgeClient()
        adapter = OpenClawGatewayAdapter(bridge=stub)
        session = adapter.attach_delegate_session(
            "oc-sess-001", GovernanceMode.ADVISORY
        )
        result = adapter.detach_delegate_session(session)
        assert result["ok"] is True
        assert session.status == "detached"
        # Bridge was told to detach, not close.
        assert "oc-sess-001" not in stub._attached

    def test_no_native_plugin_required(self):
        """The base experience requires only the bridge, not a native plugin."""
        stub = StubBridgeClient()
        adapter = OpenClawGatewayAdapter(bridge=stub)
        info = adapter.probe()
        snap = info.capability_snapshot
        assert snap is not None
        # Native plugins are not the base path.
        assert snap.evidence.get("sandbox") == "Sandbox is owned by OpenClaw, not Hive."


# ---------------------------------------------------------------------------
# OC-3: Truthfulness
# ---------------------------------------------------------------------------


class TestOC3Truthfulness:
    """Scenario OC-3 — governance and sandbox truth."""

    def test_console_labels_session_advisory(self):
        stub = StubBridgeClient()
        adapter = OpenClawGatewayAdapter(bridge=stub)
        session = adapter.attach_delegate_session(
            "oc-sess-001", GovernanceMode.ADVISORY
        )
        d = session.to_dict()
        assert d["governance_mode"] == "advisory"

    def test_sandbox_owner_is_openclaw_not_hive(self):
        stub = StubBridgeClient()
        adapter = OpenClawGatewayAdapter(bridge=stub)
        info = adapter.probe()
        snap = info.capability_snapshot
        assert snap is not None
        effective = snap.effective.to_dict()
        assert effective["native_sandbox"] == "external"
        assert effective["outer_sandbox_required"] is False

    def test_capability_doctor_does_not_claim_managed(self):
        stub = StubBridgeClient()
        adapter = OpenClawGatewayAdapter(bridge=stub)
        info = adapter.probe()
        d = info.to_dict()
        assert d["integration_level"] == "attach"
        assert d["governance_mode"] == "advisory"


# ---------------------------------------------------------------------------
# Delegate session persistence
# ---------------------------------------------------------------------------


class TestDelegateSessionPersistence:
    """Verify delegate session artifacts on disk."""

    def test_persist_and_load(self, tmp_path):
        session = SessionHandle(
            session_id="sess-001",
            adapter_name="openclaw",
            adapter_family=AdapterFamily.DELEGATE_GATEWAY,
            native_session_ref="oc-sess-001",
            governance_mode=GovernanceMode.ADVISORY,
            integration_level=IntegrationLevel.ATTACH,
            delegate_session_id="del-001",
            project_id="proj-1",
            status="attached",
        )
        session_dir = persist_delegate_session(tmp_path, session)
        assert (session_dir / "manifest.json").exists()
        assert (session_dir / "trajectory.jsonl").exists()
        assert (session_dir / "steering.ndjson").exists()

        loaded = load_delegate_session(tmp_path, "del-001")
        assert loaded is not None
        assert loaded["delegate_session_id"] == "del-001"
        assert loaded["governance_mode"] == "advisory"

    def test_list_delegate_sessions(self, tmp_path):
        for i in range(3):
            session = SessionHandle(
                session_id=f"sess-{i}",
                adapter_name="openclaw",
                adapter_family=AdapterFamily.DELEGATE_GATEWAY,
                native_session_ref=f"oc-{i}",
                delegate_session_id=f"del-{i}",
                status="attached",
            )
            persist_delegate_session(tmp_path, session)

        sessions = list_delegate_sessions(tmp_path)
        assert len(sessions) == 3

    def test_finalize_delegate_session(self, tmp_path):
        session = SessionHandle(
            session_id="sess-001",
            adapter_name="openclaw",
            adapter_family=AdapterFamily.DELEGATE_GATEWAY,
            native_session_ref="oc-sess-001",
            delegate_session_id="del-fin",
            status="attached",
        )
        persist_delegate_session(tmp_path, session)
        finalize_delegate_session(tmp_path, "del-fin", {"status": "detached"})

        final_path = tmp_path / ".hive" / "delegates" / "del-fin" / "final.json"
        assert final_path.exists()
        final = json.loads(final_path.read_text(encoding="utf-8"))
        assert final["status"] == "detached"

    def test_steering_log_appended(self, tmp_path):
        session = SessionHandle(
            session_id="sess-001",
            adapter_name="openclaw",
            adapter_family=AdapterFamily.DELEGATE_GATEWAY,
            native_session_ref="oc-sess-001",
            delegate_session_id="del-steer",
            status="attached",
        )
        persist_delegate_session(tmp_path, session)
        append_delegate_steering(
            tmp_path, "del-steer", {"action": "pause", "ts": utc_now_iso()}
        )
        append_delegate_steering(
            tmp_path, "del-steer", {"action": "resume", "ts": utc_now_iso()}
        )

        log_path = tmp_path / ".hive" / "delegates" / "del-steer" / "steering.ndjson"
        lines = [
            json.loads(line)
            for line in log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert len(lines) == 2
        assert lines[0]["action"] == "pause"
        assert lines[1]["action"] == "resume"

    def test_adapter_persists_on_attach(self, tmp_path):
        stub = StubBridgeClient()
        adapter = OpenClawGatewayAdapter(bridge=stub, base_path=tmp_path)
        session = adapter.attach_delegate_session(
            "oc-sess-001", GovernanceMode.ADVISORY, project_id="proj-1"
        )

        loaded = load_delegate_session(tmp_path, session.delegate_session_id)
        assert loaded is not None
        assert loaded["native_session_ref"] == "oc-sess-001"
        assert loaded["governance_mode"] == "advisory"

    def test_adapter_persists_steering(self, tmp_path):
        stub = StubBridgeClient()
        adapter = OpenClawGatewayAdapter(bridge=stub, base_path=tmp_path)
        session = adapter.attach_delegate_session(
            "oc-sess-001", GovernanceMode.ADVISORY
        )
        adapter.send_steer(session, SteeringRequest(action="pause", reason="test"))

        log_path = (
            tmp_path
            / ".hive"
            / "delegates"
            / session.delegate_session_id
            / "steering.ndjson"
        )
        lines = log_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["action"] == "pause"

    def test_adapter_finalizes_on_detach(self, tmp_path):
        stub = StubBridgeClient()
        adapter = OpenClawGatewayAdapter(bridge=stub, base_path=tmp_path)
        session = adapter.attach_delegate_session(
            "oc-sess-001", GovernanceMode.ADVISORY
        )
        adapter.detach_delegate_session(session)

        final_path = (
            tmp_path
            / ".hive"
            / "delegates"
            / session.delegate_session_id
            / "final.json"
        )
        assert final_path.exists()
        final = json.loads(final_path.read_text(encoding="utf-8"))
        assert final["status"] == "detached"


# ---------------------------------------------------------------------------
# Hive Link integration
# ---------------------------------------------------------------------------


class TestOpenClawHiveLink:
    """Verify OpenClaw adapter works with the Hive Link server."""

    def test_link_hello_attach_flow(self):
        stub = StubBridgeClient()
        adapter = OpenClawGatewayAdapter(bridge=stub)

        messages = [
            json.dumps(
                LinkHello(
                    harness="openclaw", adapter_family="delegate_gateway"
                ).to_dict()
            ),
            json.dumps(
                LinkAttach(
                    native_session_ref="oc-sess-001",
                    requested_governance="advisory",
                    project_id="proj-1",
                ).to_dict()
            ),
        ]
        input_stream = io.StringIO("\n".join(messages) + "\n")
        output_stream = io.StringIO()

        server = LinkServer(adapter, input_stream, output_stream)
        server.serve()

        output_stream.seek(0)
        responses = [json.loads(line) for line in output_stream if line.strip()]
        assert len(responses) == 2
        # Hello response.
        assert responses[0]["type"] == "attach_ok"
        assert responses[0]["effective_governance"] == "advisory"
        # Attach response.
        assert responses[1]["type"] == "attach_ok"
        assert responses[1]["effective_governance"] == "advisory"
        assert responses[1]["delegate_session_id"] is not None

    def test_link_governed_request_downgraded_to_advisory(self):
        """Even if governed is requested, OpenClaw enforces advisory."""
        stub = StubBridgeClient()
        adapter = OpenClawGatewayAdapter(bridge=stub)

        messages = [
            json.dumps(
                LinkAttach(
                    native_session_ref="oc-sess-001",
                    requested_governance="governed",
                ).to_dict()
            ),
        ]
        input_stream = io.StringIO("\n".join(messages) + "\n")
        output_stream = io.StringIO()

        server = LinkServer(adapter, input_stream, output_stream)
        server.serve()

        output_stream.seek(0)
        responses = [json.loads(line) for line in output_stream if line.strip()]
        assert responses[0]["effective_governance"] == "advisory"

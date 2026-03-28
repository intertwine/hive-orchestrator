"""Tests for the v2.4 OpenClaw Gateway integration (OC-1, OC-2, OC-3)."""

from __future__ import annotations

from argparse import Namespace
import io
import json
from typing import Any, Iterator

import pytest

from src.hive.cli.integrate import _detach_session
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
        sessions_accessible: bool | None = None,
        steering_supported: bool = True,
        connection_scope: str = "local",
        attach_metadata: dict[str, Any] | None = None,
        sessions: list[dict[str, Any]] | None = None,
    ) -> None:
        self._reachable = reachable
        self._gateway_reachable = gateway_reachable
        self._sessions_accessible = (
            gateway_reachable if sessions_accessible is None else sessions_accessible
        )
        self._steering_supported = steering_supported
        self._connection_scope = connection_scope
        self._attach_metadata = dict(attach_metadata or {})
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
            gateway_version="1.2.3-stub",
            gateway_url="http://localhost:3000",
            gateway_reachable=self._gateway_reachable,
            sessions_accessible=self._sessions_accessible,
            attach_supported=True,
            steering_supported=self._steering_supported,
            connection_scope=self._connection_scope,
            session_count=len(self._sessions),
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
        return {
            "ok": True,
            "session_key": session_key,
            "status": "attached",
            **self._attach_metadata,
        }

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

    def test_probe_not_available_when_sessions_inaccessible(self):
        stub = StubBridgeClient(gateway_reachable=True, sessions_accessible=False)
        adapter = OpenClawGatewayAdapter(bridge=stub)
        info = adapter.probe()
        assert info.available is False
        assert "session listing is not accessible" in info.configuration_problems[0]
        assert any("permissions" in step or "auth" in step for step in info.next_steps)

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

    def test_attach_persists_bridge_metadata(self, tmp_path):
        stub = StubBridgeClient(
            attach_metadata={
                "session_owner": "agent-alpha",
                "connection_scope": "remote",
            }
        )
        adapter = OpenClawGatewayAdapter(bridge=stub, base_path=tmp_path)
        session = adapter.attach_delegate_session(
            "oc-sess-001", GovernanceMode.ADVISORY
        )
        assert session.metadata["session_owner"] == "agent-alpha"
        manifest = load_delegate_session(tmp_path, session.delegate_session_id)
        assert manifest is not None
        assert manifest["metadata"]["connection_scope"] == "remote"

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
        assert loaded["metadata"]["sandbox_owner"] == "openclaw"

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


# ---------------------------------------------------------------------------
# Review fix coverage
# ---------------------------------------------------------------------------


class TestReviewFixes:
    """Tests covering P1/P2 fixes from Codex review."""

    def test_attach_fails_when_bridge_unreachable(self):
        """P1-2: attach must fail when bridge is not reachable."""
        stub = StubBridgeClient(reachable=False)
        adapter = OpenClawGatewayAdapter(bridge=stub)
        with pytest.raises(ConnectionError, match="not reachable"):
            adapter.attach_delegate_session("oc-sess-001", GovernanceMode.ADVISORY)

    def test_stream_events_persists_trajectory(self, tmp_path):
        """P1-3: stream_events must write trajectory to disk."""
        stub = StubBridgeClient()
        adapter = OpenClawGatewayAdapter(bridge=stub, base_path=tmp_path)
        session = adapter.attach_delegate_session(
            "oc-sess-001", GovernanceMode.ADVISORY
        )
        events = list(adapter.stream_events(session))
        assert len(events) == 3

        traj_path = (
            tmp_path
            / ".hive"
            / "delegates"
            / session.delegate_session_id
            / "trajectory.jsonl"
        )
        lines = [
            json.loads(line)
            for line in traj_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert len(lines) == 3
        assert [l["kind"] for l in lines] == [
            "session_start",
            "user_message",
            "assistant_delta",
        ]

    def test_collect_artifacts_includes_nonempty_trajectory(self, tmp_path):
        """P1-3: collect_artifacts should surface the trajectory after streaming."""
        stub = StubBridgeClient()
        adapter = OpenClawGatewayAdapter(bridge=stub, base_path=tmp_path)
        session = adapter.attach_delegate_session(
            "oc-sess-001", GovernanceMode.ADVISORY
        )
        list(adapter.stream_events(session))  # populate trajectory
        artifacts = adapter.collect_artifacts(session)
        names = [a["name"] for a in artifacts["artifacts"]]
        assert "trajectory.jsonl" in names

    def test_attach_fails_when_bridge_attach_returns_error(self):
        """P1-1 (PR #167): adapter must check bridge attach response ok field."""
        stub = StubBridgeClient()
        # Override attach to return an error.
        stub.attach = lambda key, **kw: {
            "ok": False,
            "error": "Gateway rejected session.",
        }
        adapter = OpenClawGatewayAdapter(bridge=stub)
        with pytest.raises(ConnectionError, match="Gateway rejected session"):
            adapter.attach_delegate_session("oc-sess-001", GovernanceMode.ADVISORY)

    def test_probe_not_available_when_gateway_unreachable(self):
        """P1-3 (PR #167): probe must not claim available when gateway is down."""
        stub = StubBridgeClient(gateway_reachable=False)
        adapter = OpenClawGatewayAdapter(bridge=stub)
        info = adapter.probe()
        assert info.available is False
        assert info.capability_snapshot is not None
        assert info.capability_snapshot.probed["gateway_reachable"] is False

    def test_attach_fails_when_gateway_unreachable(self):
        """P1-1 (follow-up): attach must fail when gateway is configured but down."""
        stub = StubBridgeClient(gateway_reachable=False)
        adapter = OpenClawGatewayAdapter(bridge=stub)
        with pytest.raises(ConnectionError, match="gateway is not reachable"):
            adapter.attach_delegate_session("oc-sess-001", GovernanceMode.ADVISORY)

    def test_attach_fails_when_sessions_inaccessible(self):
        stub = StubBridgeClient(gateway_reachable=True, sessions_accessible=False)
        adapter = OpenClawGatewayAdapter(bridge=stub)
        with pytest.raises(ConnectionError, match="session listing is not accessible"):
            adapter.attach_delegate_session("oc-sess-001", GovernanceMode.ADVISORY)

    def test_send_steer_raises_on_bridge_failure(self):
        stub = StubBridgeClient()
        stub.send_steer = lambda *args, **kwargs: {"ok": False, "error": "steer denied"}
        adapter = OpenClawGatewayAdapter(bridge=stub)
        session = adapter.attach_delegate_session(
            "oc-sess-001", GovernanceMode.ADVISORY
        )
        with pytest.raises(ConnectionError, match="steer denied"):
            adapter.send_steer(session, SteeringRequest(action="pause", reason="test"))

    def test_publish_note_raises_on_bridge_failure(self):
        stub = StubBridgeClient()
        stub.publish_note = lambda *args, **kwargs: {
            "ok": False,
            "error": "note denied",
        }
        adapter = OpenClawGatewayAdapter(bridge=stub)
        session = adapter.attach_delegate_session(
            "oc-sess-001", GovernanceMode.ADVISORY
        )
        with pytest.raises(ConnectionError, match="note denied"):
            adapter.publish_note(session, "hold position")

    def test_detach_raises_on_bridge_failure(self, tmp_path):
        stub = StubBridgeClient()
        stub.detach = lambda *args, **kwargs: {"ok": False, "error": "detach denied"}
        adapter = OpenClawGatewayAdapter(bridge=stub, base_path=tmp_path)
        session = adapter.attach_delegate_session(
            "oc-sess-001", GovernanceMode.ADVISORY
        )
        with pytest.raises(ConnectionError, match="detach denied"):
            adapter.detach_delegate_session(session)
        final_path = (
            tmp_path
            / ".hive"
            / "delegates"
            / session.delegate_session_id
            / "final.json"
        )
        assert not final_path.exists()


# ---------------------------------------------------------------------------
# Bridge client protocol tests
# ---------------------------------------------------------------------------


class TestBridgeClientProtocol:
    """Verify the real OpenClawBridgeClient speaks NDJSON correctly."""

    def test_send_receive_with_stub_bridge(self, tmp_path):
        """Create a tiny stub bridge script and verify the NDJSON round-trip."""
        # Write a minimal Node script that echoes back a probe response.
        bridge_script = tmp_path / "openclaw-hive-bridge"
        bridge_script.write_text(
            "#!/usr/bin/env node\n"
            'const readline = require("readline");\n'
            "const rl = readline.createInterface({ input: process.stdin });\n"
            'rl.on("line", (line) => {\n'
            "  const msg = JSON.parse(line);\n"
            '  if (msg.type === "probe") {\n'
            "    process.stdout.write(JSON.stringify({\n"
            '      type: "probe_ok",\n'
            '      version: "0.1.0-test",\n'
            '      gateway_url: "http://localhost:3000",\n'
            "      gateway_reachable: true,\n"
            "      sessions_accessible: true,\n"
            "      attach_supported: true,\n"
            "      steering_supported: true,\n"
            '    }) + "\\n");\n'
            '  } else if (msg.type === "list_sessions") {\n'
            "    process.stdout.write(JSON.stringify({\n"
            '      type: "sessions",\n'
            '      items: [{session_key: "s1", status: "active"}],\n'
            '    }) + "\\n");\n'
            '  } else if (msg.type === "attach") {\n'
            "    process.stdout.write(JSON.stringify({\n"
            '      type: "attach_ok", ok: true,\n'
            "      session_key: msg.native_session_ref,\n"
            '      status: "attached",\n'
            '    }) + "\\n");\n'
            '  } else if (msg.type === "stream_events") {\n'
            "    process.stdout.write(JSON.stringify({\n"
            '      type: "stream_events_ok",\n'
            "      events: [\n"
            '        {kind: "session_start", ts: new Date().toISOString(), payload: {}},\n'
            '        {kind: "assistant_delta", ts: new Date().toISOString(), payload: {text: "hi"}},\n'
            "      ],\n"
            '    }) + "\\n");\n'
            "  } else {\n"
            "    process.stdout.write(JSON.stringify({\n"
            '      type: "ok", ok: true,\n'
            '    }) + "\\n");\n'
            "  }\n"
            "  process.exit(0);\n"
            "});\n",
            encoding="utf-8",
        )
        bridge_script.chmod(0o755)

        import shutil

        node_path = shutil.which("node")
        if node_path is None:
            pytest.skip("Node.js not available for bridge protocol test")

        from unittest.mock import patch

        client = OpenClawBridgeClient(gateway_url="http://localhost:3000")
        with patch.object(client, "detect_binary", return_value=str(bridge_script)):
            with patch.object(
                client,
                "_bridge_command",
                return_value=[node_path, str(bridge_script)],
            ):
                # Test probe
                probe = client.probe()
                assert probe.reachable is True
                assert probe.gateway_reachable is True
                assert probe.version == "0.1.0-test"

    def test_send_receive_list_sessions(self, tmp_path):
        """Verify list_sessions parses the bridge response."""
        bridge_script = tmp_path / "openclaw-hive-bridge"
        bridge_script.write_text(
            "#!/usr/bin/env node\n"
            'process.stdout.write(JSON.stringify({type:"sessions",'
            'items:[{session_key:"s1"},{session_key:"s2"}]})'
            '+"\\n");\n'
            "process.exit(0);\n",
            encoding="utf-8",
        )
        bridge_script.chmod(0o755)

        import shutil

        node_path = shutil.which("node")
        if node_path is None:
            pytest.skip("Node.js not available")

        from unittest.mock import patch

        client = OpenClawBridgeClient()
        with patch.object(
            client,
            "_bridge_command",
            return_value=[node_path, str(bridge_script)],
        ):
            with patch.object(client, "detect_binary", return_value=str(bridge_script)):
                sessions = client.list_sessions()
                assert len(sessions) == 2
                assert sessions[0]["session_key"] == "s1"

    def test_stream_events_yields_from_bridge(self, tmp_path):
        """Verify stream_events parses events from bridge response."""
        bridge_script = tmp_path / "openclaw-hive-bridge"
        bridge_script.write_text(
            "#!/usr/bin/env node\n"
            'process.stdout.write(JSON.stringify({type:"stream_events_ok",'
            'events:[{kind:"session_start"},{kind:"assistant_delta",payload:{text:"hi"}}]})'
            '+"\\n");\n'
            "process.exit(0);\n",
            encoding="utf-8",
        )
        bridge_script.chmod(0o755)

        import shutil

        node_path = shutil.which("node")
        if node_path is None:
            pytest.skip("Node.js not available")

        from unittest.mock import patch

        client = OpenClawBridgeClient()
        with patch.object(
            client,
            "_bridge_command",
            return_value=[node_path, str(bridge_script)],
        ):
            with patch.object(client, "detect_binary", return_value=str(bridge_script)):
                events = list(client.stream_events("s1"))
                assert len(events) == 2
                assert events[0]["kind"] == "session_start"
                assert events[1]["payload"]["text"] == "hi"

    def test_stream_receive_closes_process_when_generator_is_closed_early(self):
        class _Writer:
            def write(self, _text):
                return None

            def close(self):
                return None

        class _Reader:
            def __init__(self, lines):
                self._lines = list(lines)

            def __iter__(self):
                return iter(self._lines)

            def close(self):
                return None

        class _Err:
            def read(self):
                return ""

            def close(self):
                return None

        class _Proc:
            def __init__(self):
                self.stdin = _Writer()
                self.stdout = _Reader(
                    ['{"type":"stream_event","event":{"kind":"session_start"}}\n']
                )
                self.stderr = _Err()
                self.killed = False
                self.wait_calls = 0
                self.returncode = None

            def poll(self):
                return self.returncode

            def kill(self):
                self.killed = True
                self.returncode = -9

            def wait(self, timeout=None):
                self.wait_calls += 1
                if self.returncode is None:
                    self.returncode = 0
                return self.returncode

        from unittest.mock import patch

        client = OpenClawBridgeClient()
        proc = _Proc()
        with patch.object(client, "_bridge_command", return_value=["bridge"]):
            with patch("src.hive.integrations.openclaw.subprocess.Popen", return_value=proc):
                stream = client._stream_receive({"type": "stream_events"})
                first = next(stream)
                assert first["type"] == "stream_event"
                stream.close()
        assert proc.killed is True
        assert proc.wait_calls >= 1


class TestRealBridgePackage:
    def _bridge_client(
        self,
        monkeypatch,
        tmp_path,
        *,
        sessions_accessible: bool = True,
        history_events: list[dict[str, Any]] | None = None,
    ):
        import shutil
        from pathlib import Path
        from unittest.mock import patch

        node_path = shutil.which("node")
        if node_path is None:
            pytest.skip("Node.js not available")

        fake_openclaw = tmp_path / "openclaw"
        fake_log = tmp_path / "fake-openclaw-log.jsonl"
        sessions_payload = (
            [
                {"sessionKey": "oc-sess-001", "owner": "agent-alpha"},
                {"sessionKey": "oc-sess-002", "owner": "agent-beta"},
            ]
            if sessions_accessible
            else None
        )
        history_payload = history_events or [
            {"kind": "session_start", "ts": "2026-03-28T00:00:00Z", "payload": {}},
            {
                "kind": "assistant_delta",
                "ts": "2026-03-28T00:00:01Z",
                "payload": {"text": "bridge hi"},
                "id": "evt-1",
            },
        ]
        fake_openclaw.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os, sys\n"
            f"SESSIONS = {sessions_payload!r}\n"
            f"HISTORY = {history_payload!r}\n"
            "args = sys.argv[1:]\n"
            "log_path = os.environ.get('FAKE_OPENCLAW_LOG', '')\n"
            "if log_path:\n"
            "    with open(log_path, 'a', encoding='utf-8') as fh:\n"
                "        fh.write(json.dumps(args) + '\\n')\n"
            "if args and args[0] == 'health':\n"
            "    print(json.dumps({'version': '1.2.3-test'}))\n"
            "    raise SystemExit(0)\n"
            "if args[:3] != ['gateway', 'call', args[2] if len(args) > 2 else '']:\n"
            "    pass\n"
            "method = args[2] if len(args) > 2 else ''\n"
            "params = {}\n"
            "if '--params' in args:\n"
            "    params = json.loads(args[args.index('--params') + 1])\n"
            "if method == 'sessions.list':\n"
            "    if SESSIONS is None:\n"
            "        print(json.dumps({'ok': False, 'error': 'sessions denied'}))\n"
            "        raise SystemExit(1)\n"
            "    print(json.dumps({'items': SESSIONS}))\n"
            "elif method == 'sessions.history':\n"
            "    print(json.dumps({'history': HISTORY}))\n"
            "elif method == 'chat.send':\n"
            "    print(json.dumps({'ok': True, 'echo': params}))\n"
            "elif method == 'chat.inject':\n"
            "    print(json.dumps({'ok': True, 'echo': params}))\n"
            "else:\n"
            "    print(json.dumps({'ok': False, 'error': f'unsupported method: {method}'}))\n"
            "    raise SystemExit(1)\n",
            encoding="utf-8",
        )
        fake_openclaw.chmod(0o755)

        monkeypatch.setenv("OPENCLAW_CLI", str(fake_openclaw))
        monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "test-token")
        monkeypatch.setenv("FAKE_OPENCLAW_LOG", str(fake_log))

        bridge_bin = Path(__file__).resolve().parents[1] / "packages" / "openclaw-hive-bridge" / "bin" / "openclaw-hive-bridge.js"
        client = OpenClawBridgeClient(gateway_url="http://localhost:3000")
        patcher = patch.object(
            client,
            "_bridge_command",
            return_value=[
                node_path,
                str(bridge_bin),
                "--gateway",
                "http://localhost:3000",
                "--token",
                "test-token",
                "--stdio",
            ],
        )
        patcher.start()
        monkeypatch.setattr(client, "detect_binary", lambda: str(bridge_bin))
        return client, fake_log, patcher

    def test_real_bridge_client_uses_actual_package(self, monkeypatch, tmp_path):
        client, fake_log, patcher = self._bridge_client(monkeypatch, tmp_path)
        try:
            probe = client.probe()
            assert probe.gateway_reachable is True
            assert probe.sessions_accessible is True
            assert probe.connection_scope == "local"

            sessions = client.list_sessions()
            assert [item["sessionKey"] for item in sessions] == [
                "oc-sess-001",
                "oc-sess-002",
            ]

            attached = client.attach("oc-sess-001", project_id="proj-1")
            assert attached["ok"] is True
            assert attached["gateway_session"]["owner"] == "agent-alpha"

            events = list(client.stream_events("oc-sess-001"))
            assert [event["kind"] for event in events] == [
                "session_start",
                "assistant_delta",
            ]

            steer = client.send_steer("oc-sess-001", "pause", {"reason": "operator"})
            assert steer["ok"] is True
            note = client.publish_note("oc-sess-001", "observe only")
            assert note["ok"] is True
        finally:
            patcher.stop()

        log_lines = [
            json.loads(line)
            for line in fake_log.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        methods = [line[2] for line in log_lines if len(line) > 2 and line[:2] == ["gateway", "call"]]
        assert "sessions.list" in methods
        assert "sessions.history" in methods
        assert "chat.send" in methods
        assert "chat.inject" in methods

    def test_real_bridge_probe_marks_steering_unavailable_when_sessions_fail(
        self, monkeypatch, tmp_path
    ):
        client, _fake_log, patcher = self._bridge_client(
            monkeypatch,
            tmp_path,
            sessions_accessible=False,
        )
        try:
            probe = client.probe()
            assert probe.gateway_reachable is True
            assert probe.sessions_accessible is False
            assert probe.steering_supported is False
        finally:
            patcher.stop()

    def test_real_bridge_normalizes_payloadless_messages_to_empty_object(
        self, monkeypatch, tmp_path
    ):
        client, _fake_log, patcher = self._bridge_client(
            monkeypatch,
            tmp_path,
            history_events=[
                {"kind": "session_start", "ts": "2026-03-28T00:00:00Z", "payload": {}},
                {"kind": "assistant_delta", "ts": "2026-03-28T00:00:01Z", "id": "evt-2"},
            ],
        )
        try:
            events = list(client.stream_events("oc-sess-001"))
            assert events[1]["payload"] == {}
        finally:
            patcher.stop()

    def test_adapter_streams_and_persists_via_real_bridge(self, monkeypatch, tmp_path):
        client, _fake_log, patcher = self._bridge_client(monkeypatch, tmp_path)
        try:
            adapter = OpenClawGatewayAdapter(bridge=client, base_path=tmp_path)
            session = adapter.attach_delegate_session(
                "oc-sess-001", GovernanceMode.ADVISORY, project_id="proj-1"
            )
            events = list(adapter.stream_events(session))
            assert len(events) == 2
            assert events[1]["raw_ref"] == "evt-1"
            manifest = load_delegate_session(tmp_path, session.delegate_session_id)
            assert manifest is not None
            assert manifest["metadata"]["gateway_session"]["owner"] == "agent-alpha"
        finally:
            patcher.stop()


class TestDetachCli:
    def test_detach_routes_through_adapter(self, tmp_path, monkeypatch, capsys):
        session = SessionHandle(
            session_id="sess-001",
            adapter_name="openclaw",
            adapter_family=AdapterFamily.DELEGATE_GATEWAY,
            native_session_ref="oc-sess-001",
            governance_mode=GovernanceMode.ADVISORY,
            integration_level=IntegrationLevel.ATTACH,
            delegate_session_id="del-cli",
            status="attached",
        )
        persist_delegate_session(tmp_path, session)

        seen: dict[str, Any] = {}

        def _fake_detach(self, handle):
            seen["native_session_ref"] = handle.native_session_ref
            return {"ok": True, "status": "detached"}

        monkeypatch.setattr(
            "src.hive.integrations.openclaw.OpenClawGatewayAdapter.detach_delegate_session",
            _fake_detach,
        )

        rc = _detach_session(Namespace(session_id="del-cli", json=True), tmp_path)
        payload = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert payload["ok"] is True
        assert seen["native_session_ref"] == "oc-sess-001"

    def test_detach_surfaces_adapter_failure(self, tmp_path, monkeypatch, capsys):
        session = SessionHandle(
            session_id="sess-001",
            adapter_name="openclaw",
            adapter_family=AdapterFamily.DELEGATE_GATEWAY,
            native_session_ref="oc-sess-001",
            governance_mode=GovernanceMode.ADVISORY,
            integration_level=IntegrationLevel.ATTACH,
            delegate_session_id="del-cli-fail",
            status="attached",
        )
        persist_delegate_session(tmp_path, session)

        def _fake_detach(self, handle):
            raise ConnectionError("gateway refused detach")

        monkeypatch.setattr(
            "src.hive.integrations.openclaw.OpenClawGatewayAdapter.detach_delegate_session",
            _fake_detach,
        )

        rc = _detach_session(
            Namespace(session_id="del-cli-fail", json=True),
            tmp_path,
        )
        payload = json.loads(capsys.readouterr().out)
        assert rc == 1
        assert payload["ok"] is False
        assert payload["error"] == "gateway refused detach"

    def test_detach_rejects_manifest_missing_required_identifiers(
        self, tmp_path, capsys
    ):
        session = SessionHandle(
            session_id="sess-001",
            adapter_name="openclaw",
            adapter_family=AdapterFamily.DELEGATE_GATEWAY,
            native_session_ref="oc-sess-001",
            governance_mode=GovernanceMode.ADVISORY,
            integration_level=IntegrationLevel.ATTACH,
            delegate_session_id="del-cli-bad",
            status="attached",
        )
        session_dir = persist_delegate_session(tmp_path, session)
        manifest_path = session_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest.pop("native_session_ref", None)
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        rc = _detach_session(
            Namespace(session_id="del-cli-bad", json=True),
            tmp_path,
        )
        payload = json.loads(capsys.readouterr().out)
        assert rc == 1
        assert payload["ok"] is False
        assert "missing required identifiers" in payload["error"]

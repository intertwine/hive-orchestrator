"""Tests for the v2.4 Hermes Gateway integration (HE-1, HE-2, HE-3, HE-4)."""

from __future__ import annotations

import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path

import pytest

from src.hive.drivers.types import SteeringRequest
from src.hive.integrations.base import DelegateGatewayAdapter
from src.hive.integrations.hermes import (
    PRIVATE_MEMORY_FILES,
    HermesGatewayAdapter,
    HermesProbe,
    filter_importable_files,
    import_hermes_trajectory,
    is_private_memory_path,
)
from src.hive.integrations.models import (
    AdapterFamily,
    GovernanceMode,
    IntegrationLevel,
    SessionHandle,
)
from src.hive.integrations.openclaw import (
    load_delegate_session,
)
from src.hive.integrations.registry import get_integration


# ---------------------------------------------------------------------------
# Probe helpers
# ---------------------------------------------------------------------------


@contextmanager
def _serve_json(payload: dict[str, object]):
    body = json.dumps(payload).encode("utf-8")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):  # pragma: no cover - test noise only
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        thread.join(timeout=3)


# ---------------------------------------------------------------------------
# Stub detector for testing without a real Hermes installation
# ---------------------------------------------------------------------------


def _stub_hermes_probe(
    *,
    hermes_found: bool = True,
    gateway_reachable: bool = True,
    skill_installed: bool = True,
    agents_intact: bool = True,
) -> HermesProbe:
    if not hermes_found:
        return HermesProbe(
            hermes_found=False,
            blockers=["Hermes not found."],
        )
    return HermesProbe(
        hermes_found=True,
        hermes_home="/opt/hermes",
        hermes_version="3.2.0",
        gateway_url="http://localhost:4000",
        gateway_reachable=gateway_reachable,
        skill_installed=skill_installed,
        agents_context_intact=agents_intact,
        trajectory_export_available=True,
        notes=["Hermes detected at /opt/hermes."],
        blockers=[]
        if gateway_reachable
        else ["HERMES_GATEWAY_URL not set — gateway attach will be unavailable."],
    )


def _make_adapter(
    tmp_path: Path | None = None,
    *,
    hermes_found: bool = True,
    gateway_reachable: bool = True,
    skill_installed: bool = True,
) -> HermesGatewayAdapter:
    probe = _stub_hermes_probe(
        hermes_found=hermes_found,
        gateway_reachable=gateway_reachable,
        skill_installed=skill_installed,
    )
    return HermesGatewayAdapter(
        base_path=tmp_path,
        detector=lambda _root: probe,
    )


# ---------------------------------------------------------------------------
# HE-1: Install and connect
# ---------------------------------------------------------------------------


class TestHE1InstallAndConnect:
    """Scenario HE-1 — install and connect."""

    def test_probe_with_hermes_available(self):
        adapter = _make_adapter()
        info = adapter.probe()
        assert info.adapter == "hermes"
        assert info.adapter_family == AdapterFamily.DELEGATE_GATEWAY
        assert info.governance_mode == GovernanceMode.ADVISORY
        assert info.integration_level == IntegrationLevel.ATTACH
        assert info.available is True

    def test_probe_with_hermes_unavailable(self):
        adapter = _make_adapter(hermes_found=False)
        info = adapter.probe()
        assert info.available is False
        assert any("blocker" in n for n in info.notes)

    def test_probe_with_gateway_unreachable(self):
        adapter = _make_adapter(gateway_reachable=False)
        info = adapter.probe()
        assert info.available is False
        snap = info.capability_snapshot
        assert snap is not None
        assert snap.probed["gateway_reachable"] is False
        assert snap.confidence["launch_mode"] == "hermes_only"

    def test_real_probe_rejects_generic_http_server(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hermes-home"))
        with _serve_json({"ok": True}) as gateway_url:
            monkeypatch.setenv("HERMES_GATEWAY_URL", gateway_url)
            adapter = HermesGatewayAdapter(base_path=tmp_path)
            info = adapter.probe()

        assert info.available is False
        snap = info.capability_snapshot
        assert snap is not None
        assert snap.probed["gateway_reachable"] is False
        assert snap.probed["gateway_responding"] is True
        assert any(
            "Hive-compatible Hermes attach support" in note for note in info.notes
        )

    def test_real_probe_accepts_hive_compatible_gateway(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hermes-home"))
        with _serve_json(
            {
                "gateway": "hermes",
                "capabilities": {
                    "hive_attach": True,
                    "event_stream": True,
                    "steering": True,
                },
            }
        ) as gateway_url:
            monkeypatch.setenv("HERMES_GATEWAY_URL", gateway_url)
            adapter = HermesGatewayAdapter(base_path=tmp_path)
            info = adapter.probe()

        assert info.available is True
        snap = info.capability_snapshot
        assert snap is not None
        assert snap.probed["gateway_reachable"] is True
        assert snap.probed["gateway_responding"] is True

    def test_probe_capability_snapshot_truthful(self):
        adapter = _make_adapter()
        info = adapter.probe()
        snap = info.capability_snapshot
        assert snap is not None
        d = snap.to_dict()
        assert d["governance_mode"] == "advisory"
        assert d["integration_level"] == "attach"
        assert d["adapter_family"] == "delegate_gateway"
        assert d["effective"]["native_sandbox"] == "external"
        assert d["effective"]["outer_sandbox_required"] is False
        assert (
            d["evidence"]["memory"]
            == "Private Hermes memory (MEMORY.md, USER.md) is never bulk-imported."
        )

    def test_is_delegate_gateway_adapter(self):
        adapter = _make_adapter()
        assert isinstance(adapter, DelegateGatewayAdapter)

    def test_managed_mode_deferred(self):
        adapter = _make_adapter()
        info = adapter.probe()
        assert "Managed mode is deferred from v2.4." in info.notes

    def test_memory_privacy_noted(self):
        adapter = _make_adapter()
        info = adapter.probe()
        assert "Private Hermes memory is never bulk-imported." in info.notes

    def test_skill_installed_detected(self):
        adapter = _make_adapter(skill_installed=True)
        info = adapter.probe()
        snap = info.capability_snapshot
        assert snap is not None
        assert snap.probed["skill_installed"] is True

    def test_agents_context_intact(self):
        adapter = _make_adapter()
        info = adapter.probe()
        snap = info.capability_snapshot
        assert snap is not None
        assert snap.probed["agents_context_intact"] is True

    def test_registry_bootstraps_hermes(self):
        adapter = get_integration("hermes")
        assert isinstance(adapter, HermesGatewayAdapter)


# ---------------------------------------------------------------------------
# HE-2: Attach live Hermes session
# ---------------------------------------------------------------------------


class TestHE2AttachLiveSession:
    """Scenario HE-2 — attach live Hermes session."""

    def test_attach_creates_delegate_session(self, tmp_path):
        adapter = _make_adapter(tmp_path)
        session = adapter.attach_delegate_session(
            "hermes-sess-001", GovernanceMode.ADVISORY, project_id="proj-1"
        )
        assert isinstance(session, SessionHandle)
        assert session.status == "attached"
        assert session.native_session_ref == "hermes-sess-001"
        assert session.delegate_session_id is not None
        assert session.project_id == "proj-1"
        assert session.governance_mode == GovernanceMode.ADVISORY

    def test_attach_always_advisory(self, tmp_path):
        """Hermes sessions are always advisory — Hive never owns the sandbox."""
        adapter = _make_adapter(tmp_path)
        session = adapter.attach_delegate_session(
            "hermes-sess-001", GovernanceMode.GOVERNED
        )
        assert session.governance_mode == GovernanceMode.ADVISORY

    def test_attach_fails_when_hermes_not_found(self):
        adapter = _make_adapter(hermes_found=False)
        with pytest.raises(ConnectionError, match="Hermes not found"):
            adapter.attach_delegate_session("sess", GovernanceMode.ADVISORY)

    def test_attach_fails_when_gateway_unreachable(self):
        adapter = _make_adapter(gateway_reachable=False)
        with pytest.raises(ConnectionError, match="gateway not reachable"):
            adapter.attach_delegate_session("sess", GovernanceMode.ADVISORY)

    def test_stream_events_normalized(self, tmp_path):
        adapter = _make_adapter(tmp_path)
        session = adapter.attach_delegate_session(
            "hermes-sess-001", GovernanceMode.ADVISORY
        )
        events = list(adapter.stream_events(session))
        assert len(events) >= 1
        assert events[0]["kind"] == "session_start"
        assert events[0]["harness"] == "hermes"
        assert events[0]["adapter_family"] == "delegate_gateway"
        assert events[0]["delegate_session_id"] == session.delegate_session_id

    def test_stream_events_persists_trajectory(self, tmp_path):
        adapter = _make_adapter(tmp_path)
        session = adapter.attach_delegate_session(
            "hermes-sess-001", GovernanceMode.ADVISORY
        )
        list(adapter.stream_events(session))

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
        assert len(lines) >= 1
        assert lines[0]["kind"] == "session_start"

    def test_steering_round_trips(self, tmp_path):
        adapter = _make_adapter(tmp_path)
        session = adapter.attach_delegate_session(
            "hermes-sess-001", GovernanceMode.ADVISORY
        )
        result = adapter.send_steer(
            session, SteeringRequest(action="pause", reason="operator check")
        )
        assert result["ok"] is True
        assert result["action"] == "pause"

    def test_steering_persists(self, tmp_path):
        adapter = _make_adapter(tmp_path)
        session = adapter.attach_delegate_session(
            "hermes-sess-001", GovernanceMode.ADVISORY
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

    def test_publish_note_round_trips(self, tmp_path):
        adapter = _make_adapter(tmp_path)
        session = adapter.attach_delegate_session(
            "hermes-sess-001", GovernanceMode.ADVISORY
        )
        result = adapter.publish_note(session, "check the cron output")
        assert result["ok"] is True

    def test_detach_leaves_hermes_session_running(self, tmp_path):
        adapter = _make_adapter(tmp_path)
        session = adapter.attach_delegate_session(
            "hermes-sess-001", GovernanceMode.ADVISORY
        )
        result = adapter.detach_delegate_session(session)
        assert result["ok"] is True
        assert session.status == "detached"

    def test_detach_finalizes_delegate(self, tmp_path):
        adapter = _make_adapter(tmp_path)
        session = adapter.attach_delegate_session(
            "hermes-sess-001", GovernanceMode.ADVISORY
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

    def test_collect_artifacts_after_streaming(self, tmp_path):
        adapter = _make_adapter(tmp_path)
        session = adapter.attach_delegate_session(
            "hermes-sess-001", GovernanceMode.ADVISORY
        )
        list(adapter.stream_events(session))
        artifacts = adapter.collect_artifacts(session)
        names = [a["name"] for a in artifacts["artifacts"]]
        assert "trajectory.jsonl" in names

    def test_delegate_session_persisted_on_attach(self, tmp_path):
        adapter = _make_adapter(tmp_path)
        session = adapter.attach_delegate_session(
            "hermes-sess-001", GovernanceMode.ADVISORY, project_id="proj-1"
        )
        loaded = load_delegate_session(tmp_path, session.delegate_session_id)
        assert loaded is not None
        assert loaded["native_session_ref"] == "hermes-sess-001"
        assert loaded["governance_mode"] == "advisory"


# ---------------------------------------------------------------------------
# HE-3: Trajectory import fallback
# ---------------------------------------------------------------------------


class TestHE3TrajectoryImportFallback:
    """Scenario HE-3 — trajectory import fallback."""

    def _write_hermes_export(self, path: Path) -> Path:
        """Write a sample Hermes trajectory export."""
        export_file = path / "hermes-export.jsonl"
        events = [
            {
                "type": "session.start",
                "session_id": "hermes-42",
                "ts": "2026-03-28T00:00:00Z",
                "data": {},
            },
            {
                "type": "message",
                "session_id": "hermes-42",
                "ts": "2026-03-28T00:00:01Z",
                "data": {"text": "Hello"},
            },
            {
                "type": "assistant",
                "session_id": "hermes-42",
                "ts": "2026-03-28T00:00:02Z",
                "data": {"text": "Hi there"},
            },
            {
                "type": "tool.call",
                "session_id": "hermes-42",
                "ts": "2026-03-28T00:00:03Z",
                "data": {"tool": "search"},
            },
            {
                "type": "tool.result",
                "session_id": "hermes-42",
                "ts": "2026-03-28T00:00:04Z",
                "data": {"result": "found"},
            },
            {
                "type": "session.end",
                "session_id": "hermes-42",
                "ts": "2026-03-28T00:00:05Z",
                "data": {},
            },
        ]
        export_file.write_text(
            "\n".join(json.dumps(e) for e in events) + "\n",
            encoding="utf-8",
        )
        return export_file

    def test_import_maps_to_hive_event_kinds(self, tmp_path):
        export_file = self._write_hermes_export(tmp_path)
        result = import_hermes_trajectory(tmp_path, export_file, project_id="proj-1")
        assert result["ok"] is True
        assert result["event_count"] == 6

        from src.hive.trajectory.writer import load_trajectory

        trajectory = load_trajectory(
            tmp_path, delegate_session_id=result["delegate_session_id"]
        )
        kinds = [e.kind for e in trajectory]
        assert kinds == [
            "session_start",
            "user_message",
            "assistant_delta",
            "tool_call_start",
            "tool_call_end",
            "session_end",
        ]

    def test_import_preserves_raw_provenance(self, tmp_path):
        export_file = self._write_hermes_export(tmp_path)
        result = import_hermes_trajectory(tmp_path, export_file)

        from src.hive.trajectory.writer import load_trajectory

        trajectory = load_trajectory(
            tmp_path, delegate_session_id=result["delegate_session_id"]
        )
        # All events should carry the original Hermes session ref.
        for event in trajectory:
            assert event.native_session_ref == "hermes-42"
            assert event.harness == "hermes"

    def test_import_creates_delegate_session(self, tmp_path):
        export_file = self._write_hermes_export(tmp_path)
        result = import_hermes_trajectory(
            tmp_path, export_file, project_id="proj-1", task_id="task-1"
        )
        loaded = load_delegate_session(tmp_path, result["delegate_session_id"])
        assert loaded is not None
        assert loaded["status"] == "imported"
        assert loaded["governance_mode"] == "advisory"
        assert loaded["project_id"] == "proj-1"

    def test_import_writes_final_json(self, tmp_path):
        export_file = self._write_hermes_export(tmp_path)
        result = import_hermes_trajectory(tmp_path, export_file)

        final_path = (
            tmp_path
            / ".hive"
            / "delegates"
            / result["delegate_session_id"]
            / "final.json"
        )
        assert final_path.exists()
        final = json.loads(final_path.read_text(encoding="utf-8"))
        assert final["status"] == "imported"
        assert final["event_count"] == 6

    def test_import_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            import_hermes_trajectory(tmp_path, tmp_path / "nonexistent.jsonl")

    def test_import_handles_hive_format_passthrough(self, tmp_path):
        """Events already in Hive format should pass through unchanged."""
        export_file = tmp_path / "hive-format.jsonl"
        events = [
            {"kind": "session_start", "session_id": "s1", "ts": "2026-03-28T00:00:00Z"},
            {
                "kind": "assistant_delta",
                "session_id": "s1",
                "ts": "2026-03-28T00:00:01Z",
                "payload": {"text": "hi"},
            },
        ]
        export_file.write_text(
            "\n".join(json.dumps(e) for e in events) + "\n",
            encoding="utf-8",
        )
        result = import_hermes_trajectory(tmp_path, export_file)
        assert result["event_count"] == 2

        from src.hive.trajectory.writer import load_trajectory

        trajectory = load_trajectory(
            tmp_path, delegate_session_id=result["delegate_session_id"]
        )
        assert trajectory[0].kind == "session_start"
        assert trajectory[1].kind == "assistant_delta"


# ---------------------------------------------------------------------------
# HE-4: Memory privacy
# ---------------------------------------------------------------------------


class TestHE4MemoryPrivacy:
    """Scenario HE-4 — memory privacy enforcement."""

    def test_memory_md_is_private(self):
        assert is_private_memory_path("MEMORY.md")
        assert is_private_memory_path("/some/path/MEMORY.md")

    def test_user_md_is_private(self):
        assert is_private_memory_path("USER.md")
        assert is_private_memory_path("/hermes/.user")

    def test_dotmemory_is_private(self):
        assert is_private_memory_path(".memory")

    def test_regular_files_not_private(self):
        assert not is_private_memory_path("README.md")
        assert not is_private_memory_path("trajectory.jsonl")
        assert not is_private_memory_path("AGENTS.md")
        assert not is_private_memory_path("notes.md")

    def test_filter_importable_files_removes_private(self):
        paths = [
            "MEMORY.md",
            "USER.md",
            "trajectory.jsonl",
            "AGENTS.md",
            ".memory",
            "notes.md",
        ]
        filtered = filter_importable_files(paths)
        names = [p.name for p in filtered]
        assert "MEMORY.md" not in names
        assert "USER.md" not in names
        assert ".memory" not in names
        assert "trajectory.jsonl" in names
        assert "AGENTS.md" in names
        assert "notes.md" in names

    def test_private_memory_files_constant(self):
        assert "MEMORY.md" in PRIVATE_MEMORY_FILES
        assert "USER.md" in PRIVATE_MEMORY_FILES
        assert ".memory" in PRIVATE_MEMORY_FILES
        assert ".user" in PRIVATE_MEMORY_FILES

    def test_probe_documents_memory_policy(self):
        adapter = _make_adapter()
        info = adapter.probe()
        snap = info.capability_snapshot
        assert snap is not None
        assert "never bulk-imported" in snap.evidence.get("memory", "")


# ---------------------------------------------------------------------------
# Hive Link integration
# ---------------------------------------------------------------------------


class TestHermesHiveLink:
    """Verify Hermes adapter works with the Hive Link server."""

    def test_link_hello_attach_flow(self):
        import io

        from src.hive.link.protocol import LinkAttach, LinkHello
        from src.hive.link.server import LinkServer

        adapter = _make_adapter()
        messages = [
            json.dumps(
                LinkHello(harness="hermes", adapter_family="delegate_gateway").to_dict()
            ),
            json.dumps(
                LinkAttach(
                    native_session_ref="hermes-sess-001",
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
        assert responses[0]["type"] == "attach_ok"
        assert responses[0]["effective_governance"] == "advisory"
        assert responses[1]["type"] == "attach_ok"
        assert responses[1]["effective_governance"] == "advisory"
        assert responses[1]["delegate_session_id"] is not None

    def test_link_governed_request_downgraded_to_advisory(self):
        import io

        from src.hive.link.protocol import LinkAttach
        from src.hive.link.server import LinkServer

        adapter = _make_adapter()
        messages = [
            json.dumps(
                LinkAttach(
                    native_session_ref="hermes-sess-001",
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

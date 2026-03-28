"""Tests for the v2.4 adapter-family split, registry, and backward compat."""

from __future__ import annotations

from src.hive.constants import ADAPTER_FAMILIES, GOVERNANCE_MODES, INTEGRATION_LEVELS
from src.hive.drivers.registry import get_driver, list_drivers
from src.hive.drivers.types import SteeringRequest
from src.hive.integrations.base import (
    AdapterBase,
    DelegateGatewayAdapter,
    WorkerSessionAdapter,
)
from src.hive.integrations.dummy_gateway import DummyGatewayAdapter
from src.hive.integrations.dummy_worker import DummyWorkerAdapter
from src.hive.integrations.models import (
    AdapterFamily,
    GovernanceMode,
    IntegrationLevel,
    SessionHandle,
)
from src.hive.integrations.registry import (
    list_all_backends,
    register_integration,
    unregister_integration,
)
from src.hive.runtime.capabilities import CapabilitySnapshot


# ---------------------------------------------------------------------------
# Enum and constant tests
# ---------------------------------------------------------------------------


def test_adapter_family_enum_values():
    assert AdapterFamily.WORKER_SESSION == "worker_session"
    assert AdapterFamily.DELEGATE_GATEWAY == "delegate_gateway"
    assert AdapterFamily.LEGACY_DRIVER == "legacy_driver"


def test_integration_level_enum_values():
    assert IntegrationLevel.PACK == "pack"
    assert IntegrationLevel.COMPANION == "companion"
    assert IntegrationLevel.ATTACH == "attach"
    assert IntegrationLevel.MANAGED == "managed"


def test_governance_mode_enum_values():
    assert GovernanceMode.ADVISORY == "advisory"
    assert GovernanceMode.GOVERNED == "governed"


def test_constants_tuples_match_enums():
    assert set(ADAPTER_FAMILIES) == {e.value for e in AdapterFamily}
    assert set(INTEGRATION_LEVELS) == {e.value for e in IntegrationLevel}
    assert set(GOVERNANCE_MODES) == {e.value for e in GovernanceMode}


# ---------------------------------------------------------------------------
# CapabilitySnapshot backward compat
# ---------------------------------------------------------------------------


def test_capability_snapshot_defaults_backward_compat():
    """New fields should default to legacy driver semantics."""
    snap = CapabilitySnapshot(driver="test")
    assert snap.governance_mode == "governed"
    assert snap.integration_level == "managed"
    assert snap.adapter_family == "legacy_driver"


def test_capability_snapshot_to_dict_includes_adapter_fields():
    snap = CapabilitySnapshot(
        driver="test",
        governance_mode="advisory",
        integration_level="attach",
        adapter_family="worker_session",
    )
    d = snap.to_dict()
    assert d["governance_mode"] == "advisory"
    assert d["integration_level"] == "attach"
    assert d["adapter_family"] == "worker_session"


# ---------------------------------------------------------------------------
# WorkerSessionAdapter contract
# ---------------------------------------------------------------------------


def test_worker_session_adapter_is_adapter_base():
    adapter = DummyWorkerAdapter()
    assert isinstance(adapter, WorkerSessionAdapter)
    assert isinstance(adapter, AdapterBase)


def test_worker_session_adapter_probe():
    adapter = DummyWorkerAdapter()
    info = adapter.probe()
    assert info.adapter == "dummy-worker"
    assert info.adapter_family == AdapterFamily.WORKER_SESSION
    assert info.governance_mode == GovernanceMode.ADVISORY
    assert info.integration_level == IntegrationLevel.ATTACH
    assert info.available is True
    assert info.capability_snapshot is not None
    d = info.to_dict()
    assert d["adapter_family"] == "worker_session"


def test_worker_session_open_and_close():
    from src.hive.drivers.types import RunBudget, RunLaunchRequest, RunWorkspace

    adapter = DummyWorkerAdapter()
    request = RunLaunchRequest(
        run_id="run_test_001",
        task_id="task_001",
        project_id="proj_001",
        campaign_id=None,
        driver="dummy-worker",
        model=None,
        budget=RunBudget(max_tokens=1000, max_cost_usd=0.1, max_wall_minutes=5),
        workspace=RunWorkspace(
            repo_root="/tmp", worktree_path="/tmp/wt", base_branch="main"
        ),
        compiled_context_path="/tmp/ctx",
        artifacts_path="/tmp/art",
        program_policy={},
    )
    session = adapter.open_session(request)
    assert isinstance(session, SessionHandle)
    assert session.status == "active"
    assert session.run_id == "run_test_001"

    result = adapter.close_session(session, reason="test-complete")
    assert result["ok"] is True
    assert session.status == "closed"


def test_worker_session_attach():
    adapter = DummyWorkerAdapter()
    session = adapter.attach_session("native-ref-123", GovernanceMode.ADVISORY)
    assert session.native_session_ref == "native-ref-123"
    assert session.governance_mode == GovernanceMode.ADVISORY
    assert session.integration_level == IntegrationLevel.ATTACH


def test_worker_session_stream_events():
    adapter = DummyWorkerAdapter()
    session = adapter.attach_session("ref", GovernanceMode.GOVERNED)
    events = list(adapter.stream_events(session))
    assert len(events) == 3
    kinds = [e["kind"] for e in events]
    assert kinds == ["session_start", "assistant_delta", "session_end"]


def test_worker_session_send_steer():
    adapter = DummyWorkerAdapter()
    session = adapter.attach_session("ref", GovernanceMode.GOVERNED)
    result = adapter.send_steer(
        session, SteeringRequest(action="pause", reason="testing")
    )
    assert result["ok"] is True
    assert result["action"] == "pause"
    assert len(adapter._steers) == 1


# ---------------------------------------------------------------------------
# DelegateGatewayAdapter contract
# ---------------------------------------------------------------------------


def test_delegate_gateway_adapter_is_adapter_base():
    adapter = DummyGatewayAdapter()
    assert isinstance(adapter, DelegateGatewayAdapter)
    assert isinstance(adapter, AdapterBase)


def test_delegate_gateway_probe():
    adapter = DummyGatewayAdapter()
    info = adapter.probe()
    assert info.adapter == "dummy-gateway"
    assert info.adapter_family == AdapterFamily.DELEGATE_GATEWAY
    assert info.governance_mode == GovernanceMode.ADVISORY


def test_delegate_gateway_list_sessions():
    adapter = DummyGatewayAdapter()
    sessions = adapter.list_sessions()
    assert len(sessions) == 2
    assert sessions[0]["native_session_ref"] == "gateway-sess-001"


def test_delegate_gateway_attach_and_detach():
    adapter = DummyGatewayAdapter()
    session = adapter.attach_delegate_session(
        "gateway-sess-001",
        GovernanceMode.ADVISORY,
        project_id="proj_001",
        task_id="task_001",
    )
    assert session.status == "attached"
    assert session.project_id == "proj_001"
    assert session.delegate_session_id is not None

    result = adapter.detach_delegate_session(session)
    assert result["ok"] is True
    assert session.status == "detached"


def test_delegate_gateway_stream_events():
    adapter = DummyGatewayAdapter()
    session = adapter.attach_delegate_session("ref", GovernanceMode.ADVISORY)
    events = list(adapter.stream_events(session))
    assert len(events) == 3
    kinds = [e["kind"] for e in events]
    assert kinds == ["session_start", "user_message", "assistant_delta"]


def test_delegate_gateway_publish_note():
    adapter = DummyGatewayAdapter()
    session = adapter.attach_delegate_session("ref", GovernanceMode.ADVISORY)
    result = adapter.publish_note(session, "steering note from operator")
    assert result["ok"] is True
    assert len(adapter._notes) == 1
    assert adapter._notes[0]["note"] == "steering note from operator"


# ---------------------------------------------------------------------------
# Integration registry
# ---------------------------------------------------------------------------


def test_registry_list_all_backends_includes_legacy_drivers():
    backends = list_all_backends()
    legacy = [b for b in backends if b.get("adapter_type") == "legacy_driver"]
    assert len(legacy) == len(list_drivers())
    driver_names = {b["driver"] for b in legacy}
    assert "local" in driver_names
    assert "codex" in driver_names


def test_registry_with_registered_adapters():
    worker = DummyWorkerAdapter()
    gateway = DummyGatewayAdapter()
    register_integration("dummy-worker", worker)
    register_integration("dummy-gateway", gateway)
    try:
        backends = list_all_backends()
        adapter_types = {b.get("adapter_type") for b in backends}
        assert "worker_session" in adapter_types
        assert "delegate_gateway" in adapter_types
        assert "legacy_driver" in adapter_types
    finally:
        unregister_integration("dummy-worker")
        unregister_integration("dummy-gateway")


# ---------------------------------------------------------------------------
# Existing drivers backward compat
# ---------------------------------------------------------------------------


def test_existing_drivers_probe_with_adapter_metadata():
    """All legacy drivers should return adapter metadata in to_dict()."""
    for driver in list_drivers():
        info = driver.probe()
        d = info.to_dict()
        if info.capability_snapshot is not None:
            assert d.get("governance_mode") == "governed"
            assert d.get("integration_level") == "managed"
            assert d.get("adapter_family") == "legacy_driver"


def test_get_driver_still_works():
    for name in ("local", "manual", "codex", "claude"):
        driver = get_driver(name)
        info = driver.probe()
        assert info.driver == name or info.driver in ("claude",)

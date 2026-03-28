"""Tests for the v2.4 normalized trajectory schema and writer."""

from __future__ import annotations


from src.hive.constants import TRAJECTORY_REQUIRED_KINDS, TRAJECTORY_SCHEMA_VERSION
from src.hive.trajectory.schema import TrajectoryEvent, trajectory_event
from src.hive.trajectory.writer import (
    append_trajectory_event,
    load_trajectory,
    trajectory_file,
)


# ---------------------------------------------------------------------------
# Trajectory vocabulary
# ---------------------------------------------------------------------------


def test_trajectory_required_kinds_complete():
    expected = {
        "session_start",
        "session_end",
        "turn_start",
        "turn_end",
        "assistant_delta",
        "user_message",
        "tool_call_start",
        "tool_call_update",
        "tool_call_end",
        "approval_request",
        "approval_decision",
        "steering_received",
        "artifact_written",
        "compaction",
        "error",
    }
    assert set(TRAJECTORY_REQUIRED_KINDS) == expected
    assert len(TRAJECTORY_REQUIRED_KINDS) == 15


def test_trajectory_schema_version():
    assert TRAJECTORY_SCHEMA_VERSION == "2.4.0"


# ---------------------------------------------------------------------------
# TrajectoryEvent dataclass
# ---------------------------------------------------------------------------


def test_trajectory_event_to_dict():
    event = TrajectoryEvent(
        seq=0,
        kind="session_start",
        harness="pi",
        adapter_family="worker_session",
        native_session_ref="sess-001",
        run_id="run_001",
    )
    d = event.to_dict()
    assert d["seq"] == 0
    assert d["kind"] == "session_start"
    assert d["harness"] == "pi"
    assert d["run_id"] == "run_001"
    assert d["schema_version"] == "2.4.0"


def test_trajectory_event_from_dict():
    d = {
        "seq": 3,
        "kind": "assistant_delta",
        "harness": "hermes",
        "adapter_family": "delegate_gateway",
        "native_session_ref": "gw-1",
        "payload": {"text": "hello"},
        "ts": "2026-03-27T00:00:00Z",
    }
    event = TrajectoryEvent.from_dict(d)
    assert event.seq == 3
    assert event.kind == "assistant_delta"
    assert event.payload == {"text": "hello"}


def test_trajectory_event_round_trip():
    original = trajectory_event(
        seq=5,
        kind="tool_call_start",
        harness="openclaw",
        run_id="run_x",
        payload={"tool": "search"},
    )
    d = original.to_dict()
    restored = TrajectoryEvent.from_dict(d)
    assert restored.seq == original.seq
    assert restored.kind == original.kind
    assert restored.payload == original.payload


# ---------------------------------------------------------------------------
# File path conventions
# ---------------------------------------------------------------------------


def test_trajectory_file_run_path(tmp_path):
    path = trajectory_file(tmp_path, run_id="run_abc")
    assert path == tmp_path / ".hive" / "runs" / "run_abc" / "trajectory.jsonl"


def test_trajectory_file_delegate_path(tmp_path):
    path = trajectory_file(tmp_path, delegate_session_id="del_xyz")
    assert path == tmp_path / ".hive" / "delegates" / "del_xyz" / "trajectory.jsonl"


def test_trajectory_file_requires_id():
    import pytest

    with pytest.raises(ValueError, match="Either run_id or delegate_session_id"):
        trajectory_file("/tmp")


# ---------------------------------------------------------------------------
# Writer and loader
# ---------------------------------------------------------------------------


def test_trajectory_append_and_load(tmp_path):
    events = [
        trajectory_event(seq=i, kind=kind, run_id="run_test", harness="dummy")
        for i, kind in enumerate(
            ["session_start", "assistant_delta", "tool_call_start", "session_end"]
        )
    ]
    for event in events:
        append_trajectory_event(tmp_path, event)

    loaded = load_trajectory(tmp_path, run_id="run_test")
    assert len(loaded) == 4
    assert [e.kind for e in loaded] == [
        "session_start",
        "assistant_delta",
        "tool_call_start",
        "session_end",
    ]
    assert all(e.run_id == "run_test" for e in loaded)


def test_trajectory_load_empty(tmp_path):
    loaded = load_trajectory(tmp_path, run_id="nonexistent")
    assert loaded == []


def test_trajectory_delegate_append_and_load(tmp_path):
    event = trajectory_event(
        seq=0,
        kind="session_start",
        delegate_session_id="del_001",
        harness="hermes",
    )
    append_trajectory_event(tmp_path, event)

    loaded = load_trajectory(tmp_path, delegate_session_id="del_001")
    assert len(loaded) == 1
    assert loaded[0].delegate_session_id == "del_001"

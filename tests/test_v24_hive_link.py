"""Tests for the Hive Link protocol and server stub."""

from __future__ import annotations

import io
import json

from src.hive.integrations.dummy_gateway import DummyGatewayAdapter
from src.hive.integrations.dummy_worker import DummyWorkerAdapter
from src.hive.link.protocol import (
    LINK_MESSAGE_TYPES,
    LinkActions,
    LinkArtifact,
    LinkAttach,
    LinkAttachOk,
    LinkClose,
    LinkEvent,
    LinkHeartbeat,
    LinkHello,
    LinkPollActions,
    parse_link_message,
)
from src.hive.link.server import LinkServer


# ---------------------------------------------------------------------------
# Protocol message round-trips
# ---------------------------------------------------------------------------


def test_link_message_types_tuple():
    assert len(LINK_MESSAGE_TYPES) == 9
    assert "hello" in LINK_MESSAGE_TYPES
    assert "attach" in LINK_MESSAGE_TYPES
    assert "attach_ok" in LINK_MESSAGE_TYPES
    assert "close" in LINK_MESSAGE_TYPES


def test_link_hello_round_trip():
    msg = LinkHello(harness="pi", adapter_family="worker_session", native_version="1.0")
    d = msg.to_dict()
    assert d["type"] == "hello"
    parsed = parse_link_message(d)
    assert isinstance(parsed, LinkHello)
    assert parsed.harness == "pi"


def test_link_attach_round_trip():
    msg = LinkAttach(
        native_session_ref="sess-001",
        project_id="proj",
        requested_governance="advisory",
    )
    d = msg.to_dict()
    parsed = parse_link_message(d)
    assert isinstance(parsed, LinkAttach)
    assert parsed.native_session_ref == "sess-001"
    assert parsed.requested_governance == "advisory"


def test_link_attach_ok_round_trip():
    msg = LinkAttachOk(run_id="run_001", effective_governance="governed")
    d = msg.to_dict()
    parsed = parse_link_message(d)
    assert isinstance(parsed, LinkAttachOk)
    assert parsed.run_id == "run_001"


def test_link_event_round_trip():
    msg = LinkEvent(event={"kind": "assistant_delta", "text": "hi"})
    d = msg.to_dict()
    parsed = parse_link_message(d)
    assert isinstance(parsed, LinkEvent)
    assert parsed.event["kind"] == "assistant_delta"


def test_link_artifact_round_trip():
    msg = LinkArtifact(artifact={"path": "/tmp/out.txt"})
    d = msg.to_dict()
    parsed = parse_link_message(d)
    assert isinstance(parsed, LinkArtifact)


def test_link_poll_actions_round_trip():
    msg = LinkPollActions(native_session_ref="sess-001", since_seq=5)
    d = msg.to_dict()
    parsed = parse_link_message(d)
    assert isinstance(parsed, LinkPollActions)
    assert parsed.since_seq == 5


def test_link_actions_round_trip():
    msg = LinkActions(items=[{"action": "hive_next"}])
    d = msg.to_dict()
    parsed = parse_link_message(d)
    assert isinstance(parsed, LinkActions)
    assert len(parsed.items) == 1


def test_link_heartbeat_round_trip():
    msg = LinkHeartbeat(native_session_ref="sess-001", status="alive")
    d = msg.to_dict()
    parsed = parse_link_message(d)
    assert isinstance(parsed, LinkHeartbeat)
    assert parsed.status == "alive"


def test_link_close_round_trip():
    msg = LinkClose(native_session_ref="sess-001", reason="done")
    d = msg.to_dict()
    parsed = parse_link_message(d)
    assert isinstance(parsed, LinkClose)
    assert parsed.reason == "done"


def test_parse_link_message_unknown_type():
    import pytest

    with pytest.raises(ValueError, match="Unknown Hive Link message type"):
        parse_link_message({"type": "bogus"})


# ---------------------------------------------------------------------------
# LinkServer stdio flow — WorkerSessionAdapter
# ---------------------------------------------------------------------------


def test_link_server_hello_attach_flow_worker():
    adapter = DummyWorkerAdapter()
    messages = [
        json.dumps(LinkHello(harness="pi", adapter_family="worker_session").to_dict()),
        json.dumps(
            LinkAttach(
                native_session_ref="pi-sess-42",
                requested_governance="advisory",
            ).to_dict()
        ),
        json.dumps(LinkClose(native_session_ref="pi-sess-42", reason="done").to_dict()),
    ]
    input_stream = io.StringIO("\n".join(messages) + "\n")
    output_stream = io.StringIO()

    server = LinkServer(adapter, input_stream, output_stream)
    server.serve()

    output_stream.seek(0)
    responses = [json.loads(line) for line in output_stream if line.strip()]
    assert len(responses) == 2  # hello response + attach response
    assert responses[0]["type"] == "attach_ok"
    assert responses[1]["type"] == "attach_ok"
    assert responses[1]["effective_governance"] == "advisory"


# ---------------------------------------------------------------------------
# LinkServer stdio flow — DelegateGatewayAdapter
# ---------------------------------------------------------------------------


def test_link_server_hello_attach_flow_gateway():
    adapter = DummyGatewayAdapter()
    messages = [
        json.dumps(
            LinkHello(harness="openclaw", adapter_family="delegate_gateway").to_dict()
        ),
        json.dumps(
            LinkAttach(
                native_session_ref="gw-sess-1",
                requested_governance="advisory",
                project_id="proj-001",
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
    assert responses[1]["effective_governance"] == "advisory"
    assert responses[1]["delegate_session_id"] is not None


def test_link_server_poll_actions():
    adapter = DummyWorkerAdapter()
    messages = [
        json.dumps(LinkPollActions(native_session_ref="sess-1", since_seq=0).to_dict()),
    ]
    input_stream = io.StringIO("\n".join(messages) + "\n")
    output_stream = io.StringIO()

    server = LinkServer(adapter, input_stream, output_stream)
    server.serve()

    output_stream.seek(0)
    responses = [json.loads(line) for line in output_stream if line.strip()]
    assert len(responses) == 1
    assert responses[0]["type"] == "actions"
    assert responses[0]["items"] == []


# ---------------------------------------------------------------------------
# P1 fix: multi-session close targets the correct session
# ---------------------------------------------------------------------------


def test_link_server_close_targets_correct_session():
    """Attach sess-1 and sess-2, then close sess-1 — sess-2 must survive."""
    adapter = DummyGatewayAdapter()
    messages = [
        json.dumps(
            LinkAttach(
                native_session_ref="sess-1",
                requested_governance="advisory",
            ).to_dict()
        ),
        json.dumps(
            LinkAttach(
                native_session_ref="sess-2",
                requested_governance="advisory",
            ).to_dict()
        ),
        json.dumps(LinkClose(native_session_ref="sess-1", reason="done").to_dict()),
    ]
    input_stream = io.StringIO("\n".join(messages) + "\n")
    output_stream = io.StringIO()

    server = LinkServer(adapter, input_stream, output_stream)
    server.serve()

    # sess-1 should be gone, sess-2 should still be tracked
    assert "sess-1" not in server._sessions
    assert "sess-2" in server._sessions
    assert server._sessions["sess-2"].native_session_ref == "sess-2"


# ---------------------------------------------------------------------------
# P2 fix: invalid governance emits error, doesn't crash server
# ---------------------------------------------------------------------------


def test_link_server_invalid_governance_emits_error():
    """An attach with bogus governance should emit an error, not crash."""
    adapter = DummyWorkerAdapter()
    messages = [
        json.dumps(
            LinkAttach(
                native_session_ref="sess-1",
                requested_governance="bogus",
            ).to_dict()
        ),
        json.dumps(LinkPollActions(native_session_ref="sess-1", since_seq=0).to_dict()),
    ]
    input_stream = io.StringIO("\n".join(messages) + "\n")
    output_stream = io.StringIO()

    server = LinkServer(adapter, input_stream, output_stream)
    server.serve()

    output_stream.seek(0)
    responses = [json.loads(line) for line in output_stream if line.strip()]
    # First response should be an error for the bad governance
    assert responses[0]["type"] == "error"
    assert "bogus" in responses[0]["message"]
    # Server should continue — second message gets a valid response
    assert responses[1]["type"] == "actions"

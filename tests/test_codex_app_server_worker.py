from __future__ import annotations

import argparse
from pathlib import Path

from src.hive.drivers.codex_app_server_worker import CodexAppServerBroker
from src.hive.runs import driver_state as driver_state_module


def _make_broker(tmp_path: Path) -> CodexAppServerBroker:
    prompt_path = tmp_path / "prompt.txt"
    prompt_path.write_text("Test prompt\n", encoding="utf-8")
    args = argparse.Namespace(
        binary=tmp_path / "codex",
        worktree=tmp_path,
        prompt=prompt_path,
        raw_output=tmp_path / "raw.ndjson",
        last_message=tmp_path / "last-message.txt",
        exit_code=tmp_path / "exit-code.txt",
        stderr=tmp_path / "stderr.log",
        approval_channel=tmp_path / "approval-channel.ndjson",
        state=tmp_path / "state.json",
        model=None,
    )
    return CodexAppServerBroker(args)


def test_duplicate_alias_requests_resolve_by_server_request_id(tmp_path: Path) -> None:
    broker = _make_broker(tmp_path)
    sent: list[dict] = []
    broker._send = sent.append  # type: ignore[method-assign]

    broker._handle_server_request(
        {
            "jsonrpc": "2.0",
            "id": 101,
            "method": "item/commandExecution/requestApproval",
            "params": {"approvalId": "appr_1", "command": "git status"},
        }
    )
    broker._handle_server_request(
        {
            "jsonrpc": "2.0",
            "id": 102,
            "method": "item/commandExecution/requestApproval",
            "params": {"approvalId": "appr_1", "command": "git diff"},
        }
    )

    broker._respond_to_pending_request(
        {
            "resolution": "approved",
            "payload": {"approval_id": "appr_1", "server_request_id": "102"},
        }
    )
    broker._respond_to_pending_request(
        {
            "resolution": "rejected",
            "payload": {"approval_id": "appr_1", "server_request_id": "101"},
        }
    )

    assert [payload["id"] for payload in sent] == [102, 101]
    assert sent[0]["result"] == {"decision": "accept"}
    assert sent[1]["result"] == {"decision": "decline"}
    assert broker.pending_requests == {}


def test_interrupt_is_dropped_once_turn_is_terminal(tmp_path: Path) -> None:
    broker = _make_broker(tmp_path)
    sent: list[dict] = []
    broker._send = sent.append  # type: ignore[method-assign]
    broker.pending_interrupt = True
    broker.state["thread_id"] = "thread_1"
    broker.state["turn_id"] = "turn_1"
    broker.state["turn_status"] = "completed"

    broker._send_interrupt()

    assert sent == []
    assert broker.pending_interrupt is False


def test_command_approval_imports_dedupe_by_server_request_id(
    tmp_path: Path,
    monkeypatch,
) -> None:
    requested: list[dict] = []

    def fake_request_approval(root, run_id, **kwargs):
        approval = {
            "approval_id": f"approval_{len(requested) + 1}",
            "kind": kwargs["kind"],
            "payload": dict(kwargs["payload"]),
        }
        requested.append({"root": root, "run_id": run_id, **kwargs})
        return approval

    monkeypatch.setattr(driver_state_module, "request_approval", fake_request_approval)
    metadata = {"id": "run_1", "metadata_json": {}}

    first = driver_state_module._request_codex_app_server_command_approval(
        tmp_path,
        metadata,
        request_id=101,
        payload={"approvalId": "appr_1", "itemId": "cmd_1", "command": "git status"},
    )
    second = driver_state_module._request_codex_app_server_command_approval(
        tmp_path,
        metadata,
        request_id=102,
        payload={"approvalId": "appr_1", "itemId": "cmd_1", "command": "git diff"},
    )

    assert first is not None
    assert second is not None
    assert len(requested) == 2
    assert requested[0]["payload"]["server_request_id"] == "101"
    assert requested[1]["payload"]["server_request_id"] == "102"
    assert metadata["metadata_json"]["driver_imports"]["app_server_command_approval_ids"] == [
        "101",
        "102",
    ]


def test_file_approval_imports_dedupe_by_server_request_id(
    tmp_path: Path,
    monkeypatch,
) -> None:
    requested: list[dict] = []

    def fake_request_approval(root, run_id, **kwargs):
        approval = {
            "approval_id": f"approval_{len(requested) + 1}",
            "kind": kwargs["kind"],
            "payload": dict(kwargs["payload"]),
        }
        requested.append({"root": root, "run_id": run_id, **kwargs})
        return approval

    monkeypatch.setattr(driver_state_module, "request_approval", fake_request_approval)
    metadata = {"id": "run_1", "metadata_json": {}}

    first = driver_state_module._request_codex_app_server_file_approval(
        tmp_path,
        metadata,
        request_id=201,
        payload={"callId": "patch_1", "itemId": "item_1", "grantRoot": "."},
    )
    second = driver_state_module._request_codex_app_server_file_approval(
        tmp_path,
        metadata,
        request_id=202,
        payload={"callId": "patch_1", "itemId": "item_1", "grantRoot": "."},
    )

    assert first is not None
    assert second is not None
    assert len(requested) == 2
    assert requested[0]["payload"]["server_request_id"] == "201"
    assert requested[1]["payload"]["server_request_id"] == "202"
    assert metadata["metadata_json"]["driver_imports"]["app_server_file_approval_ids"] == [
        "201",
        "202",
    ]

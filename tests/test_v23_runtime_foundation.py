"""Foundation checks for the staged v2.3 runtime implementation."""

# pylint: disable=missing-function-docstring,unused-argument,duplicate-code

from __future__ import annotations

import json
from pathlib import Path
import subprocess

from fastapi.testclient import TestClient

from hive.cli.main import main as hive_main
from src.hive.console.api import app
from src.hive.drivers import RunBudgetUsage, RunHandle, RunLinks, RunProgress, RunStatus, get_driver
from src.hive.drivers import SteeringRequest
from src.hive.runtime import request_approval
from src.hive.runs.engine import accept_run, eval_run, run_artifacts, start_run, steer_run
from src.hive.scheduler.query import ready_tasks
from src.hive.store.task_files import create_task
from tests.conftest import init_git_repo, write_safe_program


def _invoke_cli_json(capsys, argv: list[str]) -> dict:
    exit_code = hive_main(argv)
    captured = capsys.readouterr()
    assert exit_code == 0, captured.err
    return json.loads(captured.out)


def _bootstrap_workspace(temp_hive_dir: str, capsys) -> None:
    root = Path(temp_hive_dir)
    init_git_repo(root)
    _invoke_cli_json(
        capsys, ["--path", temp_hive_dir, "--json", "onboard", "demo", "--title", "Demo"]
    )
    write_safe_program(root, "demo")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Bootstrap workspace"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )


def test_driver_doctor_reports_truthful_staged_capabilities(capsys, temp_hive_dir):
    payload = _invoke_cli_json(capsys, ["--path", temp_hive_dir, "--json", "driver", "doctor"])
    drivers = {driver["driver"]: driver for driver in payload["drivers"]}

    codex = drivers["codex"]
    assert codex["declared"]["launch_mode"] == "app_server"
    assert codex["effective"]["launch_mode"] == "staged"
    assert codex["effective"]["event_stream"] == "none"
    assert codex["capabilities"]["streaming"] is False
    assert codex["capabilities"]["subagents"] is False

    claude = drivers["claude-code"]
    assert claude["declared"]["launch_mode"] == "sdk"
    assert claude["effective"]["launch_mode"] == "staged"


def test_driver_doctor_surfaces_binary_backed_probe_details(monkeypatch, capsys, temp_hive_dir):
    codex_driver = get_driver("codex")
    claude_driver = get_driver("claude")

    def fake_binary_details(self):
        if self.name == "codex":
            return "codex", "/tmp/codex"
        return "claude", "/tmp/claude"

    def fake_command_output(self, *args):
        if self.name == "codex":
            if args == ("--version",):
                return "codex 1.2.3"
            if args == ("--help",):
                return "Commands: exec app-server sandbox features"
            if args == ("exec", "--help"):
                return "--json --output-schema --output-last-message"
            if args == ("app-server", "--help"):
                return "generate-ts generate-json-schema --listen"
        if self.name == "claude-code":
            if args == ("--version",):
                return "claude 2.1.78 (Claude Code)"
            if args == ("--help",):
                return (
                    "--print --output-format json stream-json --input-format stream-json "
                    "--resume --continue --session-id --permission-mode --tools "
                    "--mcp-config --no-session-persistence"
                )
        return None

    monkeypatch.setattr(type(codex_driver), "_detected_binary_details", fake_binary_details)
    monkeypatch.setattr(type(codex_driver), "_command_output", fake_command_output)
    monkeypatch.setattr(type(claude_driver), "_detected_binary_details", fake_binary_details)
    monkeypatch.setattr(type(claude_driver), "_command_output", fake_command_output)

    payload = _invoke_cli_json(capsys, ["--path", temp_hive_dir, "--json", "driver", "doctor"])
    drivers = {driver["driver"]: driver for driver in payload["drivers"]}

    codex = drivers["codex"]
    assert codex["version"] == "codex 1.2.3"
    assert codex["probed"]["binary_name"] == "codex"
    assert codex["probed"]["exec_available"] is True
    assert codex["probed"]["app_server_available"] is True
    assert codex["probed"]["exec_json_output"] is True
    assert codex["probed"]["app_server_listen"] is True

    claude = drivers["claude-code"]
    assert claude["version"] == "claude 2.1.78 (Claude Code)"
    assert claude["probed"]["binary_name"] == "claude"
    assert claude["probed"]["resume"] is True
    assert claude["probed"]["session_id"] is True
    assert claude["probed"]["permission_mode"] is True
    assert claude["probed"]["mcp_config"] is True


def test_live_session_contract_fields_round_trip():
    handle = RunHandle(
        run_id="run_live",
        driver="codex",
        driver_handle="codex:run_live",
        status="running",
        launched_at="2026-03-17T00:00:00Z",
        launch_mode="app_server",
        transport="ws",
        session_id="sess_123",
        thread_id="thread_456",
        resume_token="resume_789",
        event_cursor="cursor_001",
        approval_channel="approvals/live",
        metadata={"protocol": "json-rpc"},
    )
    status = RunStatus(
        run_id="run_live",
        state="running",
        health="healthy",
        driver="codex",
        progress=RunProgress(phase="implementing", message="Live session attached.", percent=30),
        waiting_on=None,
        last_event_at="2026-03-17T00:01:00Z",
        budget=RunBudgetUsage(spent_tokens=100, spent_cost_usd=0.12, wall_minutes=1),
        links=RunLinks(driver_ui="https://example.invalid/runs/run_live"),
        pending_approvals=[{"approval_id": "approval_1", "kind": "command"}],
        event_cursor="cursor_001",
        session={"session_id": "sess_123", "transport": "ws"},
        artifacts={"transcript_raw_dir": "/tmp/run_live/raw"},
    )

    handle_payload = handle.to_dict()
    status_payload = status.to_dict()

    assert handle_payload["session_id"] == "sess_123"
    assert handle_payload["thread_id"] == "thread_456"
    assert handle_payload["approval_channel"] == "approvals/live"
    assert handle_payload["metadata"]["protocol"] == "json-rpc"
    assert status_payload["event_cursor"] == "cursor_001"
    assert status_payload["pending_approvals"][0]["approval_id"] == "approval_1"
    assert status_payload["session"]["transport"] == "ws"
    assert status_payload["artifacts"]["transcript_raw_dir"] == "/tmp/run_live/raw"


def test_sandbox_doctor_lists_scaffolded_backends(capsys, temp_hive_dir):
    payload = _invoke_cli_json(capsys, ["--path", temp_hive_dir, "--json", "sandbox", "doctor"])
    backends = [backend["backend"] for backend in payload["backends"]]

    assert backends == ["podman", "docker-rootless", "asrt", "e2b", "daytona", "cloudflare"]
    assert payload["backends"][0]["supported_profiles"] == ["local-safe"]
    assert payload["backends"][-1]["experimental"] is True


def test_start_run_writes_v23_foundation_artifacts(temp_hive_dir, capsys):
    _bootstrap_workspace(temp_hive_dir, capsys)
    task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
    run = start_run(temp_hive_dir, task_id, driver_name="codex")
    run_root = Path(temp_hive_dir) / ".hive" / "runs" / run.id

    manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
    snapshot = json.loads((run_root / "capability-snapshot.json").read_text(encoding="utf-8"))
    sandbox = json.loads((run_root / "sandbox-policy.json").read_text(encoding="utf-8"))
    eval_results = json.loads((run_root / "eval" / "results.json").read_text(encoding="utf-8"))
    final_state = json.loads((run_root / "final.json").read_text(encoding="utf-8"))

    assert (run_root / "events.ndjson").exists()
    assert (run_root / "approvals.ndjson").exists()
    assert (run_root / "transcript.ndjson").exists()
    assert (run_root / "retrieval" / "trace.json").exists()
    assert (run_root / "scheduler" / "decision.json").exists()
    assert (run_root / "final.json").exists()
    assert manifest["driver"] == "codex"
    assert snapshot["effective"]["launch_mode"] == "staged"
    assert sandbox["backend"] == "legacy-host"
    assert eval_results["status"] == "awaiting_input"
    assert final_state["run_id"] == run.id
    assert final_state["status"] == "awaiting_input"
    assert final_state["task_status"] == "in_progress"


def test_runtime_artifacts_track_eval_accept_and_cancel(temp_hive_dir, capsys):
    _bootstrap_workspace(temp_hive_dir, capsys)
    task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
    run = start_run(temp_hive_dir, task_id, driver_name="local")
    run_root = Path(temp_hive_dir) / ".hive" / "runs" / run.id

    initial_eval = json.loads((run_root / "eval" / "results.json").read_text(encoding="utf-8"))
    initial_final = json.loads((run_root / "final.json").read_text(encoding="utf-8"))
    assert initial_eval["status"] == "running"
    assert initial_eval["results"] == []
    assert initial_final["status"] == "running"
    assert initial_final["task_status"] == "in_progress"

    evaluated = eval_run(temp_hive_dir, run.id)
    eval_results = json.loads((run_root / "eval" / "results.json").read_text(encoding="utf-8"))
    final_after_eval = json.loads((run_root / "final.json").read_text(encoding="utf-8"))
    artifacts = run_artifacts(temp_hive_dir, run.id)

    assert evaluated["promotion_decision"]["decision"] == "accept"
    assert eval_results["status"] == "awaiting_review"
    assert eval_results["promotion_decision"]["decision"] == "accept"
    assert eval_results["results"][0]["status"] == "pass"
    assert final_after_eval["status"] == "awaiting_review"
    assert final_after_eval["promotion_decision"]["decision"] == "accept"
    assert Path(str(artifacts["artifacts"]["eval_results"])).resolve() == (
        run_root / "eval" / "results.json"
    ).resolve()

    accepted = accept_run(temp_hive_dir, run.id)
    final_after_accept = json.loads((run_root / "final.json").read_text(encoding="utf-8"))
    assert accepted["status"] == "accepted"
    assert final_after_accept["status"] == "accepted"
    assert final_after_accept["task_status"] == "review"
    assert final_after_accept["finished_at"] is not None

    cancel_task = create_task(temp_hive_dir, "demo", "Cancelled slice", status="ready", priority=1)
    cancelled = start_run(temp_hive_dir, cancel_task.id, driver_name="local")
    cancelled_root = Path(temp_hive_dir) / ".hive" / "runs" / cancelled.id
    steer_run(
        temp_hive_dir,
        cancelled.id,
        SteeringRequest(action="cancel", reason="operator stopped this run"),
        actor="operator",
    )
    final_after_cancel = json.loads((cancelled_root / "final.json").read_text(encoding="utf-8"))
    assert final_after_cancel["status"] == "cancelled"
    assert final_after_cancel["task_status"] == "ready"
    assert final_after_cancel["exit_reason"] == "operator stopped this run"


def test_console_event_stream_emits_sse_snapshot(temp_hive_dir, capsys):
    _bootstrap_workspace(temp_hive_dir, capsys)

    client = TestClient(app)
    response = client.get("/events/stream", params={"path": temp_hive_dir, "once": True})

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "event: snapshot" in response.text


def test_approval_request_surfaces_in_inbox_and_can_be_resolved(temp_hive_dir, capsys):
    _bootstrap_workspace(temp_hive_dir, capsys)
    task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
    run = start_run(temp_hive_dir, task_id, driver_name="codex")
    approval = request_approval(
        temp_hive_dir,
        run.id,
        kind="command",
        title="Approve git status",
        summary="Driver wants to run `git status` in the worktree.",
        requested_by="driver:codex",
        payload={"command": "git status"},
    )

    client = TestClient(app)
    inbox = client.get("/inbox", params={"path": temp_hive_dir})
    approvals = client.get(f"/runs/{run.id}/approvals", params={"path": temp_hive_dir})
    resolution = client.post(
        f"/runs/{run.id}/approvals/{approval['approval_id']}/approve",
        params={"path": temp_hive_dir},
        json={"actor": "operator", "note": "safe command"},
    )

    assert inbox.status_code == 200
    assert any(item["kind"] == "approval-request" for item in inbox.json()["items"])
    assert approvals.status_code == 200
    assert approvals.json()["approvals"][0]["status"] == "pending"
    assert resolution.status_code == 200
    assert resolution.json()["approval"]["status"] == "approved"

"""Foundation checks for the staged v2.3 runtime implementation."""

# pylint: disable=missing-function-docstring,unused-argument,duplicate-code

from __future__ import annotations

import json
from pathlib import Path
import subprocess

from fastapi.testclient import TestClient

from hive.cli.main import main as hive_main
from src.hive.console.api import app
from src.hive.runtime import request_approval
from src.hive.runs.engine import start_run
from src.hive.scheduler.query import ready_tasks
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

    assert (run_root / "events.ndjson").exists()
    assert (run_root / "approvals.ndjson").exists()
    assert (run_root / "transcript.ndjson").exists()
    assert (run_root / "retrieval" / "trace.json").exists()
    assert (run_root / "scheduler" / "decision.json").exists()
    assert (run_root / "final.json").exists()
    assert manifest["driver"] == "codex"
    assert snapshot["effective"]["launch_mode"] == "staged"
    assert sandbox["backend"] == "legacy-host"


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

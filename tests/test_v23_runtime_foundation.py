"""Foundation checks for the staged v2.3 runtime implementation."""

# pylint: disable=missing-function-docstring,unused-argument,duplicate-code

from __future__ import annotations

import json
from pathlib import Path
import subprocess

from fastapi.testclient import TestClient
import pytest

from hive.cli.main import main as hive_main
from src.hive.codemode.execute import execute_code
from src.hive.console.api import app
from src.hive.drivers import RunBudgetUsage, RunHandle, RunLinks, RunProgress, RunStatus, get_driver
from src.hive.drivers import SteeringRequest
from src.hive.runs.evaluators import run_evaluator
from src.hive.runs.executors import LocalExecutor
from src.hive.runtime import list_approvals, pending_approvals, request_approval
from src.hive.runtime.runpack import SandboxPolicy
from src.hive.runs.engine import accept_run, eval_run, load_run, run_artifacts, start_run, steer_run
from src.hive.scheduler.query import ready_tasks
from src.hive.sandbox import get_backend
from src.hive.sandbox.base import SandboxProbe
from src.hive.sandbox.runtime import resolve_sandbox_policy
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
    assert codex["probed"]["exec_approval_flag"] is False
    assert codex["probed"]["exec_json_output"] is True
    assert codex["probed"]["exec_output_last_message"] is True
    assert codex["probed"]["app_server_listen"] is True

    claude = drivers["claude-code"]
    assert claude["version"] == "claude 2.1.78 (Claude Code)"
    assert claude["probed"]["binary_name"] == "claude"
    assert claude["probed"]["resume"] is True
    assert claude["probed"]["session_id"] is True
    assert claude["probed"]["permission_mode"] is True
    assert claude["probed"]["mcp_config"] is True


def test_driver_doctor_surfaces_claude_live_exec_when_enabled(monkeypatch, capsys, temp_hive_dir):
    driver = get_driver("claude-code")

    def fake_live_exec_enabled(self):
        return True

    def fake_binary_details(self):
        return "claude", "/tmp/claude"

    def fake_command_output(self, *args):
        if args == ("--version",):
            return "claude 2.1.78 (Claude Code)"
        if args == ("--help",):
            return (
                "--print --output-format json --input-format stream-json "
                "--resume --continue --session-id --permission-mode "
                "--mcp-config --max-budget-usd"
            )
        return None

    monkeypatch.setattr(type(driver), "_live_exec_enabled", fake_live_exec_enabled)
    monkeypatch.setattr(type(driver), "_detected_binary_details", fake_binary_details)
    monkeypatch.setattr(type(driver), "_command_output", fake_command_output)

    payload = _invoke_cli_json(
        capsys,
        ["--path", temp_hive_dir, "--json", "driver", "doctor", "claude-code"],
    )
    driver_payload = payload["drivers"][0]

    assert driver_payload["driver"] == "claude-code"
    assert driver_payload["effective"]["launch_mode"] == "exec"
    assert driver_payload["effective"]["session_persistence"] == "ephemeral"


def test_driver_doctor_surfaces_codex_app_server_when_enabled(monkeypatch, capsys, temp_hive_dir):
    driver = get_driver("codex")

    def fake_detected_binary_details(self):
        return ("codex", "/tmp/codex")

    def fake_command_output(self, *args):
        if args == ("--help",):
            return "Commands:\n  exec\n  app-server\n"
        if args == ("app-server", "--help"):
            return "Usage: codex app-server --listen <URL>\n  --listen <URL>\n"
        if args == ("exec", "--help"):
            return "Usage: codex exec --json\n"
        if args in {("--version",), ("version",)}:
            return "codex 0.0.0-test"
        return ""

    monkeypatch.setattr(type(driver), "_detected_binary_details", fake_detected_binary_details)
    monkeypatch.setattr(type(driver), "_command_output", fake_command_output)
    monkeypatch.setenv("HIVE_CODEX_LIVE_APP_SERVER", "1")
    monkeypatch.delenv("HIVE_CODEX_LIVE_EXEC", raising=False)

    payload = _invoke_cli_json(capsys, ["--path", temp_hive_dir, "--json", "driver", "doctor", "codex"])

    driver_payload = payload["drivers"][0]
    assert driver_payload["effective"]["launch_mode"] == "app_server"
    assert driver_payload["effective"]["session_persistence"] == "thread"
    assert driver_payload["confidence"]["effective"] == "verified"
    assert "live interactive Codex run" in driver_payload["notes"][-1]


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
    assert "configured" in payload["backends"][0]
    assert payload["backends"][-1]["experimental"] is True


def test_e2b_probe_reports_auth_unverified_without_env(monkeypatch):
    backend = get_backend("e2b")

    def fake_find_binary(self):
        return "/tmp/e2b"

    def fake_command_output(self, *args):
        if args == ("--version",):
            return "e2b 0.1.0"
        return None

    monkeypatch.setattr(type(backend), "_find_binary", fake_find_binary)
    monkeypatch.setattr(type(backend), "_command_output", fake_command_output)
    monkeypatch.setattr(type(backend), "_sdk_available", staticmethod(lambda: True))
    monkeypatch.delenv("E2B_API_KEY", raising=False)
    monkeypatch.delenv("E2B_ACCESS_TOKEN", raising=False)

    probe = backend.probe()

    assert probe.available is True
    assert probe.configured is False
    assert probe.warnings
    assert probe.evidence["env"]["E2B_API_KEY"] is False
    assert probe.evidence["env"]["E2B_ACCESS_TOKEN"] is False


def test_e2b_probe_requires_python_sdk_for_hosted_execution(monkeypatch):
    backend = get_backend("e2b")

    def fake_find_binary(self):
        return "/tmp/e2b"

    def fake_command_output(self, *args):
        if args == ("--version",):
            return "e2b 0.1.0"
        return None

    monkeypatch.setattr(type(backend), "_find_binary", fake_find_binary)
    monkeypatch.setattr(type(backend), "_command_output", fake_command_output)
    monkeypatch.setattr(type(backend), "_sdk_available", staticmethod(lambda: False))
    monkeypatch.setenv("E2B_API_KEY", "token")
    monkeypatch.delenv("E2B_ACCESS_TOKEN", raising=False)

    probe = backend.probe()

    assert probe.available is True
    assert probe.configured is False
    assert probe.evidence["python_sdk"] is False
    assert any("sandbox-e2b" in blocker for blocker in probe.blockers)


def test_daytona_probe_requires_api_url_for_self_hosted(monkeypatch):
    backend = get_backend("daytona")

    def fake_find_binary(self):
        return "/tmp/daytona"

    def fake_command_output(self, *args):
        if args == ("--version",):
            return "daytona 0.1.0"
        return None

    monkeypatch.setattr(type(backend), "_find_binary", fake_find_binary)
    monkeypatch.setattr(type(backend), "_command_output", fake_command_output)
    monkeypatch.setenv("DAYTONA_API_KEY", "token")
    monkeypatch.delenv("DAYTONA_API_URL", raising=False)
    monkeypatch.delenv("DAYTONA_JWT_TOKEN", raising=False)
    monkeypatch.delenv("DAYTONA_ORGANIZATION_ID", raising=False)

    probe = backend.probe()

    assert probe.available is True
    assert probe.configured is False
    assert "DAYTONA_API_KEY" in probe.evidence["auth_source"]
    assert any("DAYTONA_API_URL" in blocker for blocker in probe.blockers)


def test_cloudflare_probe_detects_api_token_configuration(monkeypatch):
    backend = get_backend("cloudflare")

    def fake_find_binary(self):
        return "/tmp/wrangler"

    def fake_command_output(self, *args):
        if args == ("--version",):
            return "wrangler 0.1.0"
        return None

    monkeypatch.setattr(type(backend), "_find_binary", fake_find_binary)
    monkeypatch.setattr(type(backend), "_command_output", fake_command_output)
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "token")
    monkeypatch.delenv("CLOUDFLARE_API_KEY", raising=False)
    monkeypatch.delenv("CLOUDFLARE_EMAIL", raising=False)

    probe = backend.probe()

    assert probe.available is True
    assert probe.configured is True
    assert probe.experimental is True
    assert probe.evidence["auth_source"] == ["CLOUDFLARE_API_TOKEN"]


def test_start_run_writes_v23_foundation_artifacts(temp_hive_dir, capsys):
    _bootstrap_workspace(temp_hive_dir, capsys)
    create_task(
        temp_hive_dir,
        "demo",
        "Sandbox policy evaluator guardrails",
        status="ready",
        priority=1,
        summary_md="Update PROGRAM budget and sandbox approval rules.",
    )
    task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
    run = start_run(temp_hive_dir, task_id, driver_name="codex")
    run_root = Path(temp_hive_dir) / ".hive" / "runs" / run.id

    manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
    snapshot = json.loads((run_root / "capability-snapshot.json").read_text(encoding="utf-8"))
    sandbox = json.loads((run_root / "sandbox-policy.json").read_text(encoding="utf-8"))
    retrieval_trace = json.loads((run_root / "retrieval" / "trace.json").read_text(encoding="utf-8"))
    retrieval_hits = json.loads((run_root / "retrieval" / "hits.json").read_text(encoding="utf-8"))
    eval_results = json.loads((run_root / "eval" / "results.json").read_text(encoding="utf-8"))
    final_state = json.loads((run_root / "final.json").read_text(encoding="utf-8"))

    assert (run_root / "events.ndjson").exists()
    assert (run_root / "approvals.ndjson").exists()
    assert (run_root / "driver" / "approval-channel.ndjson").exists()
    assert (run_root / "transcript.ndjson").exists()
    assert (run_root / "retrieval" / "trace.json").exists()
    assert (run_root / "scheduler" / "decision.json").exists()
    assert (run_root / "final.json").exists()
    assert manifest["driver"] == "codex"
    assert snapshot["effective"]["launch_mode"] == "staged"
    assert sandbox["backend"] == "legacy-host"
    assert retrieval_trace["intent"] == "policy"
    assert retrieval_trace["selected_context"]
    assert all(item["provenance"] for item in retrieval_trace["selected_context"])
    assert all(item["explanation"] for item in retrieval_trace["selected_context"])
    assert retrieval_hits["candidate_count"] >= retrieval_hits["selected_count"]
    assert manifest["compiled_context_manifest"].endswith("context/manifest.json")
    assert eval_results["status"] == "awaiting_input"
    assert final_state["run_id"] == run.id
    assert final_state["status"] == "awaiting_input"
    assert final_state["task_status"] == "in_progress"


def test_start_run_selects_local_safe_sandbox_backend_when_available(
    temp_hive_dir, capsys, monkeypatch
):
    _bootstrap_workspace(temp_hive_dir, capsys)
    podman = get_backend("podman")
    docker = get_backend("docker-rootless")

    def fake_podman_probe(self):
        return SandboxProbe(
            backend="podman",
            available=True,
            isolation_class="container",
            supported_profiles=["local-safe"],
            notes=["Detected rootless Podman."],
            evidence={"binary": "/tmp/podman"},
        )

    def fake_docker_probe(self):
        return SandboxProbe(
            backend="docker-rootless",
            available=False,
            isolation_class="container",
            supported_profiles=["local-safe"],
            notes=["Docker unavailable."],
            evidence={},
        )

    monkeypatch.setattr(type(podman), "probe", fake_podman_probe)
    monkeypatch.setattr(type(docker), "probe", fake_docker_probe)

    task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
    run = start_run(temp_hive_dir, task_id, driver_name="local", profile="local-safe")
    run_root = Path(temp_hive_dir) / ".hive" / "runs" / run.id
    sandbox = json.loads((run_root / "sandbox-policy.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))

    assert sandbox["backend"] == "podman"
    assert sandbox["isolation_class"] == "container"
    assert sandbox["network"]["mode"] == "deny"
    assert sandbox["profile"] == "local-safe"
    assert manifest["sandbox_backend"] == "podman"
    assert manifest["sandbox_profile"] == "local-safe"


def test_start_run_selects_local_fast_asrt_backend_when_available(
    temp_hive_dir, capsys, monkeypatch
):
    _bootstrap_workspace(temp_hive_dir, capsys)
    asrt = get_backend("asrt")

    def fake_asrt_probe(self):
        return SandboxProbe(
            backend="asrt",
            available=True,
            isolation_class="process-wrapper",
            supported_profiles=["local-fast"],
            notes=["Detected Anthropic Sandbox Runtime."],
            evidence={"binary": "/tmp/srt", "version": "srt 0.1.0"},
        )

    monkeypatch.setattr(type(asrt), "probe", fake_asrt_probe)

    task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
    run = start_run(temp_hive_dir, task_id, driver_name="local", profile="local-fast")
    run_root = Path(temp_hive_dir) / ".hive" / "runs" / run.id
    sandbox = json.loads((run_root / "sandbox-policy.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))

    assert sandbox["backend"] == "asrt"
    assert sandbox["isolation_class"] == "process-wrapper"
    assert sandbox["profile"] == "local-fast"
    assert manifest["sandbox_backend"] == "asrt"
    assert manifest["sandbox_profile"] == "local-fast"


def test_start_run_emits_sandbox_selected_event(temp_hive_dir, capsys, monkeypatch):
    _bootstrap_workspace(temp_hive_dir, capsys)
    podman = get_backend("podman")
    docker = get_backend("docker-rootless")

    def fake_podman_probe(self):
        return SandboxProbe(
            backend="podman",
            available=True,
            isolation_class="container",
            supported_profiles=["local-safe"],
            notes=["Detected rootless Podman."],
            evidence={"binary": "/tmp/podman", "rootless": True},
        )

    def fake_docker_probe(self):
        return SandboxProbe(
            backend="docker-rootless",
            available=False,
            isolation_class="container",
            supported_profiles=["local-safe"],
            notes=["Docker unavailable."],
            evidence={},
        )

    monkeypatch.setattr(type(podman), "probe", fake_podman_probe)
    monkeypatch.setattr(type(docker), "probe", fake_docker_probe)

    task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
    run = start_run(temp_hive_dir, task_id, driver_name="local", profile="local-safe")
    events = list((Path(temp_hive_dir) / ".hive" / "runs" / run.id / "events.ndjson").read_text(
        encoding="utf-8"
    ).splitlines())
    final_state = json.loads(
        (Path(temp_hive_dir) / ".hive" / "runs" / run.id / "final.json").read_text(
            encoding="utf-8"
        )
    )

    sandbox_events = [json.loads(line) for line in events if line.strip()]
    selected = [event for event in sandbox_events if event["type"] == "sandbox.selected"]
    assert selected
    assert selected[0]["payload"]["backend"] == "podman"
    assert final_state["sandbox_backend"] == "podman"
    assert final_state["sandbox_profile"] == "local-safe"


def test_start_run_rejects_local_safe_when_no_backend_is_available(
    temp_hive_dir, capsys, monkeypatch
):
    _bootstrap_workspace(temp_hive_dir, capsys)
    podman = get_backend("podman")
    docker = get_backend("docker-rootless")

    def fake_unavailable_probe(self):
        return SandboxProbe(
            backend=self.name,
            available=False,
            isolation_class="container",
            supported_profiles=["local-safe"],
            notes=["Unavailable."],
            evidence={},
        )

    monkeypatch.setattr(type(podman), "probe", fake_unavailable_probe)
    monkeypatch.setattr(type(docker), "probe", fake_unavailable_probe)

    task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
    with pytest.raises(ValueError, match="local-safe"):
        start_run(temp_hive_dir, task_id, driver_name="local", profile="local-safe")

    runs_root = Path(temp_hive_dir) / ".hive" / "runs"
    assert list(runs_root.iterdir()) == []


def test_local_executor_wraps_commands_for_container_sandbox(monkeypatch, tmp_path):
    calls: list[dict[str, object]] = []
    worktree = tmp_path / "worktree"
    artifacts = tmp_path / "artifacts"
    worktree.mkdir()
    artifacts.mkdir()

    def fake_run(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})

        class Result:
            returncode = 0
            stdout = "ok\n"
            stderr = ""

        return Result()

    monkeypatch.setattr("src.hive.runs.executors.subprocess.run", fake_run)
    executor = LocalExecutor(
        SandboxPolicy(
            backend="podman",
            isolation_class="container",
            network={"mode": "deny", "allowlist": []},
            mounts={
                "read_only": [],
                "read_write": [str(worktree), str(artifacts)],
                "container_worktree": "/workspace",
                "container_artifacts": "/artifacts",
            },
            resources={"cpu": None, "memory_mb": None, "disk_mb": None, "wall_clock_sec": None},
            env={"inherit": False, "allowlist": ["LANG"], "passthrough": []},
            snapshot=False,
            resume=False,
            profile="local-safe",
            provenance="sandbox_v2_backend:podman",
        )
    )

    result = executor.run_command("python -c \"print('ok')\"", cwd=worktree, timeout_seconds=30)

    argv = list(calls[0]["args"][0])
    assert result.returncode == 0
    assert result.sandbox is not None
    assert result.sandbox["backend"] == "podman"
    assert result.sandbox["network_mode"] == "deny"
    assert calls[0]["kwargs"]["shell"] is False
    assert argv[:4] == ["podman", "run", "--rm", "--interactive"]
    assert "--network" in argv
    assert "none" in argv
    assert "/workspace" in " ".join(argv)


def test_local_executor_wraps_commands_for_asrt_local_fast(monkeypatch, tmp_path):
    calls: list[dict[str, object]] = []
    worktree = tmp_path / "worktree"
    artifacts = tmp_path / "artifacts"
    worktree.mkdir()
    artifacts.mkdir()

    def fake_run(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})

        class Result:
            returncode = 0
            stdout = "ok\n"
            stderr = ""

        return Result()

    monkeypatch.setattr("src.hive.runs.executors.subprocess.run", fake_run)
    executor = LocalExecutor(
        SandboxPolicy(
            backend="asrt",
            isolation_class="process-wrapper",
            network={"mode": "deny", "allowlist": []},
            mounts={
                "read_only": [],
                "read_write": [str(worktree), str(artifacts)],
                "container_worktree": "/workspace",
                "container_artifacts": "/artifacts",
            },
            resources={"cpu": None, "memory_mb": None, "disk_mb": None, "wall_clock_sec": None},
            env={"inherit": False, "allowlist": ["LANG"], "passthrough": []},
            snapshot=False,
            resume=False,
            profile="local-fast",
            provenance="sandbox_v2_backend:asrt",
        )
    )

    result = executor.run_command("python -c \"print('ok')\"", cwd=worktree, timeout_seconds=30)

    argv = list(calls[0]["args"][0])
    settings_path = Path(argv[2])
    settings = json.loads(settings_path.read_text(encoding="utf-8"))

    assert result.returncode == 0
    assert result.sandbox is not None
    assert result.sandbox["backend"] == "asrt"
    assert result.sandbox["network_mode"] == "deny"
    assert calls[0]["kwargs"]["shell"] is False
    assert argv[:4] == ["srt", "--settings", str(settings_path), "sh"]
    assert settings["filesystem"]["allowWrite"][:2] == [str(worktree), str(artifacts)]
    assert settings["network"]["allowedDomains"] == []


def test_local_executor_reports_unwired_daytona_backend_as_failed_command(tmp_path):
    worktree = tmp_path / "worktree"
    artifacts = tmp_path / "artifacts"
    worktree.mkdir()
    artifacts.mkdir()
    executor = LocalExecutor(
        SandboxPolicy(
            backend="daytona",
            isolation_class="remote-sandbox",
            network={"mode": "deny", "allowlist": []},
            mounts={
                "read_only": [],
                "read_write": [str(worktree), str(artifacts)],
                "container_worktree": "/workspace",
                "container_artifacts": "/artifacts",
            },
            resources={"cpu": None, "memory_mb": None, "disk_mb": None, "wall_clock_sec": None},
            env={"inherit": False, "allowlist": ["LANG"], "passthrough": []},
            snapshot=False,
            resume=False,
            profile="team-self-hosted",
            provenance="sandbox_v2_backend:daytona",
        )
    )

    result = executor.run_command("python -c \"print('ok')\"", cwd=worktree, timeout_seconds=30)

    assert result.returncode == 1
    assert result.timed_out is False
    assert "not wired into the local executor yet" in result.stderr


def test_resolve_hosted_managed_requires_configured_backend(monkeypatch, tmp_path):
    backend = get_backend("e2b")
    worktree = tmp_path / "worktree"
    artifacts = tmp_path / "artifacts"
    worktree.mkdir()
    artifacts.mkdir()

    def fake_probe(self):
        return SandboxProbe(
            backend="e2b",
            available=True,
            configured=False,
            isolation_class="managed-sandbox",
            supported_profiles=["hosted-managed"],
            blockers=["Missing E2B_API_KEY"],
            warnings=["CLI login is not enough for automation"],
            notes=[],
            evidence={},
        )

    monkeypatch.setattr(type(backend), "probe", fake_probe)

    with pytest.raises(ValueError) as excinfo:
        resolve_sandbox_policy(
            worktree_path=str(worktree),
            artifacts_path=str(artifacts),
            profile="hosted-managed",
        )

    assert "e2b:" in str(excinfo.value)
    assert "Missing E2B_API_KEY" in str(excinfo.value)


def test_local_executor_runs_commands_via_e2b_sdk(monkeypatch, tmp_path):
    worktree = tmp_path / "worktree"
    artifacts = tmp_path / "artifacts"
    worktree.mkdir()
    artifacts.mkdir()
    (worktree / "README.md").write_text("hello\n", encoding="utf-8")
    calls: dict[str, object] = {}

    class FakeCommandResult:
        exit_code = 0
        stdout = "ok\n"
        stderr = ""

    class FakeCommands:
        def run(self, cmd, **kwargs):
            calls.setdefault("commands", []).append({"cmd": cmd, "kwargs": kwargs})
            return FakeCommandResult()

    class FakeFiles:
        def make_dir(self, path):
            calls.setdefault("dirs", []).append(path)
            return True

        def write(self, path, data):
            calls["write"] = {"path": path, "size": len(data)}
            return {"path": path}

    class FakeSandbox:
        sandbox_id = "sbx_123"

        def __init__(self):
            self.files = FakeFiles()
            self.commands = FakeCommands()

        def kill(self):
            calls["killed"] = True
            return True

        @classmethod
        def create(cls, **kwargs):
            calls["create"] = kwargs
            return cls()

    monkeypatch.setattr("src.hive.runs.executors._load_e2b_sdk", lambda: FakeSandbox)

    executor = LocalExecutor(
        SandboxPolicy(
            backend="e2b",
            isolation_class="managed-sandbox",
            network={"mode": "deny", "allowlist": []},
            mounts={
                "read_only": [],
                "read_write": [str(worktree), str(artifacts)],
                "container_worktree": "/workspace",
                "container_artifacts": "/artifacts",
            },
            resources={"cpu": None, "memory_mb": None, "disk_mb": None, "wall_clock_sec": None},
            env={"inherit": False, "allowlist": ["LANG"], "passthrough": []},
            snapshot=False,
            resume=False,
            profile="hosted-managed",
            provenance="sandbox_v2_backend:e2b",
        )
    )

    result = executor.run_command("pytest -q", cwd=worktree, timeout_seconds=45)

    sync_command = calls["commands"][0]
    run_command = calls["commands"][1]

    assert result.returncode == 0
    assert result.stdout == "ok\n"
    assert result.sandbox is not None
    assert result.sandbox["backend"] == "e2b"
    assert result.sandbox["workspace_sync"] == "upload_only"
    assert result.sandbox["remote_sandbox_id"] == "sbx_123"
    assert calls["create"]["allow_internet_access"] is False
    assert calls["write"]["path"] == "/tmp/hive-mounts.tar.gz"
    assert sync_command["cmd"].startswith("mkdir -p /workspace /artifacts && tar -xzf")
    assert run_command["kwargs"]["cwd"] == "/workspace"
    assert calls["killed"] is True


def test_local_executor_reports_missing_e2b_sdk(monkeypatch, tmp_path):
    worktree = tmp_path / "worktree"
    artifacts = tmp_path / "artifacts"
    worktree.mkdir()
    artifacts.mkdir()
    monkeypatch.setattr(
        "src.hive.runs.executors._load_e2b_sdk",
        lambda: (_ for _ in ()).throw(ImportError("sandbox-e2b missing")),
    )

    executor = LocalExecutor(
        SandboxPolicy(
            backend="e2b",
            isolation_class="managed-sandbox",
            network={"mode": "deny", "allowlist": []},
            mounts={
                "read_only": [],
                "read_write": [str(worktree), str(artifacts)],
                "container_worktree": "/workspace",
                "container_artifacts": "/artifacts",
            },
            resources={"cpu": None, "memory_mb": None, "disk_mb": None, "wall_clock_sec": None},
            env={"inherit": False, "allowlist": [], "passthrough": []},
            snapshot=False,
            resume=False,
            profile="hosted-managed",
            provenance="sandbox_v2_backend:e2b",
        )
    )

    result = executor.run_command("pytest -q", cwd=worktree, timeout_seconds=45)

    assert result.returncode == 1
    assert "sandbox-e2b" in result.stderr
    assert result.sandbox is not None
    assert result.sandbox["backend"] == "e2b"


def test_execute_local_safe_wraps_python_runner_in_container(monkeypatch, tmp_path):
    calls: list[dict[str, object]] = []
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    podman = get_backend("podman")
    docker = get_backend("docker-rootless")

    def fake_podman_probe(self):
        return SandboxProbe(
            backend="podman",
            available=True,
            isolation_class="container",
            supported_profiles=["local-safe"],
            notes=["Detected rootless Podman."],
            evidence={"binary": "/tmp/podman"},
        )

    def fake_docker_probe(self):
        return SandboxProbe(
            backend="docker-rootless",
            available=False,
            isolation_class="container",
            supported_profiles=["local-safe"],
            notes=["Docker unavailable."],
            evidence={},
        )

    def fake_run(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})

        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return Result()

    monkeypatch.setattr(type(podman), "probe", fake_podman_probe)
    monkeypatch.setattr(type(docker), "probe", fake_docker_probe)
    monkeypatch.setattr("src.hive.codemode.execute.subprocess.run", fake_run)

    payload = execute_code(
        workspace,
        language="python",
        code="result = {'ok': True}",
        profile="local-safe",
        timeout_seconds=10,
    )

    argv = list(calls[0]["args"][0])
    assert payload["ok"] is True
    assert payload["sandbox_backend"] == "podman"
    assert payload["sandbox_profile"] == "local-safe"
    assert payload["sandbox_network_mode"] == "deny"
    assert calls[0]["kwargs"]["shell"] is False
    assert calls[0]["kwargs"]["env"] is None
    assert argv[0] == "podman"
    assert "python -m src.hive.codemode.python_runner" in argv[-1]
    assert "/artifacts/payload.json" in argv[-1]


def test_execute_local_fast_wraps_python_runner_with_asrt(monkeypatch, tmp_path):
    calls: list[dict[str, object]] = []
    settings_payload: dict[str, object] = {}
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    asrt = get_backend("asrt")

    def fake_asrt_probe(self):
        return SandboxProbe(
            backend="asrt",
            available=True,
            isolation_class="process-wrapper",
            supported_profiles=["local-fast"],
            notes=["Detected Anthropic Sandbox Runtime."],
            evidence={"binary": "/tmp/srt"},
        )

    def fake_run(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
        argv = list(args[0])
        settings_path = Path(argv[2])
        settings_payload.update(json.loads(settings_path.read_text(encoding="utf-8")))

        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return Result()

    monkeypatch.setattr(type(asrt), "probe", fake_asrt_probe)
    monkeypatch.setattr("src.hive.codemode.execute.subprocess.run", fake_run)

    payload = execute_code(
        workspace,
        language="python",
        code="result = {'ok': True}",
        profile="local-fast",
        timeout_seconds=10,
    )

    argv = list(calls[0]["args"][0])

    assert payload["ok"] is True
    assert payload["sandbox_backend"] == "asrt"
    assert payload["sandbox_profile"] == "local-fast"
    assert payload["sandbox_network_mode"] == "deny"
    assert calls[0]["kwargs"]["shell"] is False
    assert calls[0]["kwargs"]["env"] is None
    assert argv[:4] == ["srt", "--settings", argv[2], "sh"]
    assert "python -m src.hive.codemode.python_runner" in argv[-1]
    assert settings_payload["filesystem"]["allowRead"][0] == str(workspace)


def test_execute_local_safe_returns_error_when_backend_is_unavailable(monkeypatch, tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    podman = get_backend("podman")
    docker = get_backend("docker-rootless")

    def fake_unavailable_probe(self):
        return SandboxProbe(
            backend=self.name,
            available=False,
            isolation_class="container",
            supported_profiles=["local-safe"],
            notes=["Unavailable."],
            evidence={},
        )

    monkeypatch.setattr(type(podman), "probe", fake_unavailable_probe)
    monkeypatch.setattr(type(docker), "probe", fake_unavailable_probe)

    payload = execute_code(
        workspace,
        language="python",
        code="result = {'ok': True}",
        profile="local-safe",
        timeout_seconds=10,
    )

    assert payload["ok"] is False
    assert "Sandbox profile 'local-safe' requires one of" in payload["error"]


def test_docker_rootless_probe_requires_rootless_daemon(monkeypatch):
    backend = get_backend("docker-rootless")

    def fake_find_binary(self):
        return "/tmp/docker"

    def fake_command_output(self, *args):
        if args == ("--version",):
            return "Docker version 28.3.3"
        if args == ("info", "--format", "{{json .SecurityOptions}}"):
            return '["name=rootless","name=seccomp"]'
        return None

    monkeypatch.setattr(type(backend), "_find_binary", fake_find_binary)
    monkeypatch.setattr(type(backend), "_command_output", fake_command_output)

    probe = backend.probe()

    assert probe.available is True
    assert probe.evidence["rootless"] is True
    assert "rootless" in probe.notes[-1]


def test_asrt_probe_prefers_srt_binary(monkeypatch):
    backend = get_backend("asrt")

    def fake_find_binary(self):
        return "/tmp/srt"

    def fake_command_output(self, *args):
        if args == ("--version",):
            return "srt 0.1.0"
        return None

    monkeypatch.setattr(type(backend), "_find_binary", fake_find_binary)
    monkeypatch.setattr(type(backend), "_command_output", fake_command_output)

    probe = backend.probe()

    assert backend.binaries[0] == "srt"
    assert probe.available is True
    assert probe.evidence["binary"] == "/tmp/srt"
    assert probe.evidence["version"] == "srt 0.1.0"


def test_run_evaluator_records_sandbox_metadata(monkeypatch, tmp_path):
    calls: list[dict[str, object]] = []
    worktree = tmp_path / "worktree"
    artifacts = tmp_path / "artifacts"
    output_dir = tmp_path / "eval"
    command_log = tmp_path / "command-log.ndjson"
    worktree.mkdir()
    artifacts.mkdir()

    def fake_run(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})

        class Result:
            returncode = 0
            stdout = "ok\n"
            stderr = ""

        return Result()

    monkeypatch.setattr("src.hive.runs.executors.subprocess.run", fake_run)
    executor = LocalExecutor(
        SandboxPolicy(
            backend="podman",
            isolation_class="container",
            network={"mode": "deny", "allowlist": []},
            mounts={
                "read_only": [],
                "read_write": [str(worktree), str(artifacts)],
                "container_worktree": "/workspace",
                "container_artifacts": "/artifacts",
            },
            resources={"cpu": None, "memory_mb": None, "disk_mb": None, "wall_clock_sec": None},
            env={"inherit": False, "allowlist": ["LANG"], "passthrough": []},
            snapshot=False,
            resume=False,
            profile="local-safe",
            provenance="sandbox_v2_backend:podman",
        )
    )

    result = run_evaluator(
        executor,
        "python -c \"print('ok')\"",
        worktree,
        output_dir,
        "sandbox-check",
        True,
        command_log_path=command_log,
        seq=1,
        timeout_seconds=30,
    )

    command_entry = json.loads(command_log.read_text(encoding="utf-8").splitlines()[0])
    assert result["metadata_json"]["sandbox"]["backend"] == "podman"
    assert command_entry["metadata_json"]["sandbox"]["network_mode"] == "deny"


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


def test_console_approval_resolution_targets_requested_item(temp_hive_dir, capsys):
    _bootstrap_workspace(temp_hive_dir, capsys)
    task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
    run = start_run(temp_hive_dir, task_id, driver_name="codex")
    first = request_approval(
        temp_hive_dir,
        run.id,
        kind="command",
        title="Approve git status",
        summary="Driver wants to run `git status`.",
        requested_by="driver:codex",
        payload={"command": "git status"},
    )
    second = request_approval(
        temp_hive_dir,
        run.id,
        kind="command",
        title="Approve git diff",
        summary="Driver wants to run `git diff`.",
        requested_by="driver:codex",
        payload={"command": "git diff"},
    )

    client = TestClient(app)
    resolution = client.post(
        f"/runs/{run.id}/approvals/{first['approval_id']}/approve",
        params={"path": temp_hive_dir},
        json={"actor": "operator", "note": "approve the first request"},
    )
    approvals = client.get(f"/runs/{run.id}/approvals", params={"path": temp_hive_dir})
    broker_path = Path(temp_hive_dir) / ".hive" / "runs" / run.id / "driver" / "approval-channel.ndjson"
    broker_records = [
        json.loads(line) for line in broker_path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]

    assert resolution.status_code == 200
    assert resolution.json()["approval"]["approval_id"] == first["approval_id"]
    statuses = {item["approval_id"]: item["status"] for item in approvals.json()["approvals"]}
    assert statuses[first["approval_id"]] == "approved"
    assert statuses[second["approval_id"]] == "pending"
    assert broker_records[-1]["approval_id"] == first["approval_id"]
    assert broker_records[-1]["resolution"] == "approved"


def test_run_status_surfaces_session_and_pending_approvals(capsys, temp_hive_dir):
    _bootstrap_workspace(temp_hive_dir, capsys)
    task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
    run = start_run(temp_hive_dir, task_id, driver_name="local")
    request_approval(
        temp_hive_dir,
        run.id,
        kind="command",
        title="Approve git diff",
        summary="Driver wants to inspect the current diff.",
        requested_by="driver:local",
        payload={"command": "git diff"},
    )

    payload = _invoke_cli_json(capsys, ["--path", temp_hive_dir, "--json", "run", "status", run.id])

    assert payload["status"]["health"] == "healthy"
    assert payload["status"]["session"]["launch_mode"] == "local"
    assert payload["status"]["session"]["transport"] == "process"
    assert payload["status"]["progress"]["phase"] == "implementing"
    assert payload["status"]["pending_approvals"][0]["title"] == "Approve git diff"
    assert payload["pending_approvals"][0]["payload"]["command"] == "git diff"


def test_cancel_run_rejects_pending_approvals(capsys, temp_hive_dir):
    _bootstrap_workspace(temp_hive_dir, capsys)
    task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
    run = start_run(temp_hive_dir, task_id, driver_name="local")
    first = request_approval(
        temp_hive_dir,
        run.id,
        kind="command",
        title="Approve git status",
        summary="Driver wants to inspect the repo status.",
        requested_by="driver:local",
        payload={"command": "git status"},
    )
    second = request_approval(
        temp_hive_dir,
        run.id,
        kind="command",
        title="Approve git diff",
        summary="Driver wants to inspect the current diff.",
        requested_by="driver:local",
        payload={"command": "git diff"},
    )

    payload = steer_run(
        temp_hive_dir,
        run.id,
        SteeringRequest(action="cancel", reason="Operator stopped the run"),
        actor="operator",
    )
    approvals = {item["approval_id"]: item for item in list_approvals(temp_hive_dir, run.id)}

    assert payload["run"]["status"] == "cancelled"
    assert pending_approvals(temp_hive_dir, run.id) == []
    assert approvals[first["approval_id"]]["status"] == "rejected"
    assert approvals[second["approval_id"]]["status"] == "rejected"
    assert approvals[first["approval_id"]]["resolution_note"] == "Operator stopped the run"
    assert approvals[second["approval_id"]]["resolved_by"] == "operator"


def test_run_status_refresh_surfaces_live_codex_session_payload(temp_hive_dir, capsys, monkeypatch):
    _bootstrap_workspace(temp_hive_dir, capsys)
    driver = get_driver("codex")
    calls = {"count": 0}

    def fake_live_exec_enabled(self):
        return True

    def fake_launch_live_exec(self, request):
        return RunHandle(
            run_id=request.run_id,
            driver="codex",
            driver_handle=f"codex:exec:{request.run_id}",
            status="running",
            launched_at="2026-03-18T06:00:00Z",
            launch_mode="exec",
            transport="subprocess",
            session_id="pid-7000",
            event_cursor="0",
            metadata={"pid": 7000, "last_message_path": "/tmp/codex-last.txt"},
        )

    def fake_status(self, handle):
        calls["count"] += 1
        cursor = "2" if calls["count"] == 1 else "9"
        return RunStatus(
            run_id=handle.run_id,
            state="running",
            health="healthy",
            driver="codex",
            progress=RunProgress(
                phase="implementing",
                message="Codex live exec is active.",
                percent=40,
            ),
            waiting_on=None,
            last_event_at="2026-03-18T06:02:00Z",
            event_cursor=cursor,
            session={"launch_mode": "exec", "transport": "subprocess", "session_id": "pid-7000"},
            artifacts={
                "last_message_path": "/tmp/codex-last.txt",
                "raw_output_path": "/tmp/codex.jsonl",
            },
        )

    monkeypatch.setattr(type(driver), "_live_exec_enabled", fake_live_exec_enabled)
    monkeypatch.setattr(type(driver), "_launch_live_exec", fake_launch_live_exec)
    monkeypatch.setattr(type(driver), "status", fake_status)

    task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
    run = start_run(temp_hive_dir, task_id, driver_name="codex")
    payload = _invoke_cli_json(
        capsys,
        ["--path", temp_hive_dir, "--json", "run", "status", run.id],
    )

    assert payload["status"]["session"]["launch_mode"] == "exec"
    assert payload["status"]["session"]["session_id"] == "pid-7000"
    assert payload["status"]["event_cursor"] == "9"
    assert payload["status"]["artifacts"]["raw_output_path"] == "/tmp/codex.jsonl"


def test_run_status_refresh_surfaces_live_claude_session_payload(temp_hive_dir, capsys, monkeypatch):
    _bootstrap_workspace(temp_hive_dir, capsys)
    driver = get_driver("claude-code")
    calls = {"count": 0}

    def fake_live_exec_enabled(self):
        return True

    def fake_launch_live_exec(self, request):
        return RunHandle(
            run_id=request.run_id,
            driver="claude-code",
            driver_handle=f"claude-code:exec:{request.run_id}",
            status="running",
            launched_at="2026-03-18T06:00:00Z",
            launch_mode="exec",
            transport="subprocess",
            session_id="sess-7000",
            event_cursor="0",
            metadata={"pid": 7000, "last_message_path": "/tmp/claude-last.txt"},
        )

    def fake_status(self, handle):
        calls["count"] += 1
        cursor = "2" if calls["count"] == 1 else "8"
        return RunStatus(
            run_id=handle.run_id,
            state="running",
            health="healthy",
            driver="claude-code",
            progress=RunProgress(
                phase="implementing",
                message="Claude live exec is active.",
                percent=40,
            ),
            waiting_on=None,
            last_event_at="2026-03-18T06:02:00Z",
            event_cursor=cursor,
            budget=RunBudgetUsage(spent_tokens=123, spent_cost_usd=0.45, wall_minutes=3),
            session={
                "launch_mode": "exec",
                "transport": "subprocess",
                "session_id": "sess-7000",
            },
            artifacts={
                "last_message_path": "/tmp/claude-last.txt",
                "raw_output_path": "/tmp/claude.json",
            },
        )

    monkeypatch.setattr(type(driver), "_live_exec_enabled", fake_live_exec_enabled)
    monkeypatch.setattr(type(driver), "_launch_live_exec", fake_launch_live_exec)
    monkeypatch.setattr(type(driver), "status", fake_status)

    task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
    run = start_run(temp_hive_dir, task_id, driver_name="claude-code")
    payload = _invoke_cli_json(
        capsys,
        ["--path", temp_hive_dir, "--json", "run", "status", run.id],
    )
    metadata = load_run(temp_hive_dir, run.id)

    assert payload["status"]["session"]["launch_mode"] == "exec"
    assert payload["status"]["session"]["session_id"] == "sess-7000"
    assert payload["status"]["event_cursor"] == "8"
    assert payload["status"]["artifacts"]["raw_output_path"] == "/tmp/claude.json"
    assert metadata["tokens_out"] == 123
    assert metadata["cost_usd"] == 0.45


def test_run_status_imports_live_codex_events_into_runtime_artifacts(
    temp_hive_dir, capsys, monkeypatch
):
    _bootstrap_workspace(temp_hive_dir, capsys)
    driver = get_driver("codex")

    def fake_live_exec_enabled(self):
        return True

    def fake_launch_live_exec(self, request):
        raw_output_path = (
            Path(request.artifacts_path) / "transcript" / "raw" / "codex-exec-events.jsonl"
        )
        raw_output_path.parent.mkdir(parents=True, exist_ok=True)
        raw_output_path.write_text(
            "\n".join(
                [
                    json.dumps({"type": "thread.started", "thread_id": "thread_123"}),
                    json.dumps(
                        {
                            "id": "evt_1",
                            "msg": {
                                "type": "agent_message_delta",
                                "text": "Working through the requested patch.",
                            },
                        }
                    ),
                    json.dumps(
                        {
                            "type": "item.completed",
                            "item": {"type": "todo_list", "items": ["inspect", "patch"]},
                        }
                    ),
                    json.dumps(
                        {
                            "type": "item.completed",
                            "item": {"type": "file_change", "path": "README.md"},
                        }
                    ),
                    json.dumps(
                        {
                            "id": "evt_2",
                            "msg": {
                                "type": "exec_approval_request",
                                "call_id": "call_123",
                                "command": ["bash", "-lc", "git status"],
                                "cwd": request.workspace.worktree_path,
                            },
                        }
                    ),
                    json.dumps(
                        {
                            "type": "turn.completed",
                            "usage": {"input_tokens": 10, "output_tokens": 5},
                        }
                    ),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        return RunHandle(
            run_id=request.run_id,
            driver="codex",
            driver_handle=f"codex:exec:{request.run_id}",
            status="running",
            launched_at="2026-03-18T06:00:00Z",
            launch_mode="exec",
            transport="subprocess",
            session_id="pid-7200",
            event_cursor="0",
            metadata={"pid": 7200, "raw_output_path": str(raw_output_path)},
        )

    def fake_status(self, handle):
        raw_output_path = str(handle.metadata["raw_output_path"])
        return RunStatus(
            run_id=handle.run_id,
            state="running",
            health="healthy",
            driver="codex",
            progress=RunProgress(
                phase="implementing",
                message="Codex live exec is active.",
                percent=45,
            ),
            waiting_on=None,
            last_event_at="2026-03-18T06:04:00Z",
            event_cursor="6",
            session={"launch_mode": "exec", "transport": "subprocess", "session_id": "pid-7200"},
            artifacts={"raw_output_path": raw_output_path},
        )

    monkeypatch.setattr(type(driver), "_live_exec_enabled", fake_live_exec_enabled)
    monkeypatch.setattr(type(driver), "_launch_live_exec", fake_launch_live_exec)
    monkeypatch.setattr(type(driver), "status", fake_status)

    task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
    run = start_run(temp_hive_dir, task_id, driver_name="codex")
    payload = _invoke_cli_json(
        capsys,
        ["--path", temp_hive_dir, "--json", "run", "status", run.id],
    )
    metadata = load_run(temp_hive_dir, run.id)
    run_root = Path(temp_hive_dir) / ".hive" / "runs" / run.id
    transcript = (run_root / "transcript.ndjson").read_text(encoding="utf-8")
    event_types = [
        json.loads(line)["type"]
        for line in (run_root / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert payload["status"]["health"] == "blocked"
    assert payload["status"]["waiting_on"] == "approval"
    assert payload["status"]["pending_approvals"][0]["payload"]["command"] == [
        "bash",
        "-lc",
        "git status",
    ]
    assert payload["status"]["budget"]["spent_tokens"] == 15
    assert metadata["metadata_json"]["driver_usage"]["spent_tokens"] == 15
    assert metadata["metadata_json"]["budget_rollup"]["input_tokens"] == 10
    assert metadata["metadata_json"]["budget_rollup"]["output_tokens"] == 5
    assert metadata["tokens_in"] == 10
    assert metadata["tokens_out"] == 5
    assert metadata["cost_usd"] == 0.0
    assert "Working through the requested patch." in transcript
    assert "driver.output.delta" in event_types
    assert "driver.status" in event_types
    assert "plan.updated" in event_types
    assert "diff.updated" in event_types
    assert "approval.requested" in event_types


def test_run_status_imports_live_claude_output_into_runtime_artifacts(
    temp_hive_dir, capsys, monkeypatch
):
    _bootstrap_workspace(temp_hive_dir, capsys)
    driver = get_driver("claude-code")

    def fake_live_exec_enabled(self):
        return True

    def fake_launch_live_exec(self, request):
        raw_output_path = (
            Path(request.artifacts_path) / "transcript" / "raw" / "claude-print-result.json"
        )
        raw_output_path.parent.mkdir(parents=True, exist_ok=True)
        raw_output_path.write_text(
            json.dumps(
                {
                    "session_id": "sess-7200",
                    "total_cost_usd": 0.45,
                    "duration_ms": 90_000,
                    "usage": {
                        "input_tokens": 100,
                        "cache_creation_input_tokens": 0,
                        "cache_read_input_tokens": 0,
                        "output_tokens": 23,
                    },
                    "result": "Delivered the requested implementation.",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return RunHandle(
            run_id=request.run_id,
            driver="claude-code",
            driver_handle=f"claude-code:exec:{request.run_id}",
            status="running",
            launched_at="2026-03-18T06:00:00Z",
            launch_mode="exec",
            transport="subprocess",
            session_id="sess-7200",
            event_cursor="0",
            metadata={"pid": 7200, "raw_output_path": str(raw_output_path)},
        )

    def fake_status(self, handle):
        raw_output_path = str(handle.metadata["raw_output_path"])
        return RunStatus(
            run_id=handle.run_id,
            state="completed_candidate",
            health="healthy",
            driver="claude-code",
            progress=RunProgress(
                phase="completed",
                message="Claude live exec finished.",
                percent=100,
            ),
            waiting_on="review",
            last_event_at="2026-03-18T06:04:00Z",
            event_cursor="1",
            session={
                "launch_mode": "exec",
                "transport": "subprocess",
                "session_id": "sess-7200",
            },
            artifacts={"raw_output_path": raw_output_path},
        )

    monkeypatch.setattr(type(driver), "_live_exec_enabled", fake_live_exec_enabled)
    monkeypatch.setattr(type(driver), "_launch_live_exec", fake_launch_live_exec)
    monkeypatch.setattr(type(driver), "status", fake_status)

    task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
    run = start_run(temp_hive_dir, task_id, driver_name="claude-code")
    first_payload = _invoke_cli_json(
        capsys,
        ["--path", temp_hive_dir, "--json", "run", "status", run.id],
    )
    second_payload = _invoke_cli_json(
        capsys,
        ["--path", temp_hive_dir, "--json", "run", "status", run.id],
    )
    metadata = load_run(temp_hive_dir, run.id)
    run_root = Path(temp_hive_dir) / ".hive" / "runs" / run.id
    transcript = (run_root / "transcript.ndjson").read_text(encoding="utf-8")
    event_types = [
        json.loads(line)["type"]
        for line in (run_root / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert first_payload["status"]["state"] == "completed_candidate"
    assert second_payload["status"]["budget"]["spent_tokens"] == 123
    assert metadata["metadata_json"]["driver_usage"]["spent_tokens"] == 123
    assert metadata["tokens_in"] == 100
    assert metadata["tokens_out"] == 23
    assert metadata["cost_usd"] == 0.45
    assert metadata["metadata_json"]["driver_imports"]["claude_exec_raw_output_path"].endswith(
        "claude-print-result.json"
    )
    assert transcript.count("Delivered the requested implementation.") == 1
    assert "driver.output.delta" in event_types
    assert "driver.status" in event_types


def test_eval_run_refreshes_live_codex_state_before_review(temp_hive_dir, capsys, monkeypatch):
    _bootstrap_workspace(temp_hive_dir, capsys)
    driver = get_driver("codex")
    calls = {"count": 0}

    def fake_live_exec_enabled(self):
        return True

    def fake_launch_live_exec(self, request):
        return RunHandle(
            run_id=request.run_id,
            driver="codex",
            driver_handle=f"codex:exec:{request.run_id}",
            status="running",
            launched_at="2026-03-18T06:00:00Z",
            launch_mode="exec",
            transport="subprocess",
            session_id="pid-7100",
            event_cursor="0",
            metadata={"pid": 7100, "last_message_path": str(last_message_path)},
        )

    def fake_status(self, handle):
        calls["count"] += 1
        state = "running" if calls["count"] == 1 else "completed_candidate"
        return RunStatus(
            run_id=handle.run_id,
            state=state,
            health="healthy",
            driver="codex",
            progress=RunProgress(
                phase="implementing" if state == "running" else "completed",
                message="Codex live exec is active.",
                percent=50 if state == "running" else 100,
            ),
            waiting_on=None if state == "running" else "review",
            last_event_at="2026-03-18T06:03:00Z",
            event_cursor="5",
            session={"launch_mode": "exec", "transport": "subprocess", "session_id": "pid-7100"},
            artifacts={"last_message_path": str(last_message_path)},
        )

    monkeypatch.setattr(type(driver), "_live_exec_enabled", fake_live_exec_enabled)
    monkeypatch.setattr(type(driver), "_launch_live_exec", fake_launch_live_exec)
    monkeypatch.setattr(type(driver), "status", fake_status)

    task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
    last_message_path = Path(temp_hive_dir).parent / "codex-last-message.txt"
    last_message_path.write_text("Implemented the requested change.\n", encoding="utf-8")
    run = start_run(temp_hive_dir, task_id, driver_name="codex")
    evaluated = eval_run(temp_hive_dir, run.id)
    transcript_path = Path(temp_hive_dir) / ".hive" / "runs" / run.id / "transcript.ndjson"

    assert evaluated["run"]["status"] == "awaiting_review"
    assert "Implemented the requested change." in transcript_path.read_text(encoding="utf-8")


def test_eval_run_refreshes_live_claude_state_before_review(temp_hive_dir, capsys, monkeypatch):
    _bootstrap_workspace(temp_hive_dir, capsys)
    driver = get_driver("claude-code")
    calls = {"count": 0}

    def fake_live_exec_enabled(self):
        return True

    def fake_launch_live_exec(self, request):
        return RunHandle(
            run_id=request.run_id,
            driver="claude-code",
            driver_handle=f"claude-code:exec:{request.run_id}",
            status="running",
            launched_at="2026-03-18T06:00:00Z",
            launch_mode="exec",
            transport="subprocess",
            session_id="sess-7100",
            event_cursor="0",
            metadata={"pid": 7100, "last_message_path": str(last_message_path)},
        )

    def fake_status(self, handle):
        calls["count"] += 1
        state = "running" if calls["count"] == 1 else "completed_candidate"
        return RunStatus(
            run_id=handle.run_id,
            state=state,
            health="healthy",
            driver="claude-code",
            progress=RunProgress(
                phase="implementing" if state == "running" else "completed",
                message="Claude live exec is active.",
                percent=50 if state == "running" else 100,
            ),
            waiting_on=None if state == "running" else "review",
            last_event_at="2026-03-18T06:03:00Z",
            event_cursor="5",
            session={
                "launch_mode": "exec",
                "transport": "subprocess",
                "session_id": "sess-7100",
            },
            artifacts={"last_message_path": str(last_message_path)},
        )

    monkeypatch.setattr(type(driver), "_live_exec_enabled", fake_live_exec_enabled)
    monkeypatch.setattr(type(driver), "_launch_live_exec", fake_launch_live_exec)
    monkeypatch.setattr(type(driver), "status", fake_status)

    task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
    last_message_path = Path(temp_hive_dir).parent / "claude-last-message.txt"
    last_message_path.write_text("Delivered the requested implementation.\n", encoding="utf-8")
    run = start_run(temp_hive_dir, task_id, driver_name="claude-code")
    evaluated = eval_run(temp_hive_dir, run.id)
    transcript_path = Path(temp_hive_dir) / ".hive" / "runs" / run.id / "transcript.ndjson"

    assert evaluated["run"]["status"] == "awaiting_review"
    assert "Delivered the requested implementation." in transcript_path.read_text(
        encoding="utf-8"
    )

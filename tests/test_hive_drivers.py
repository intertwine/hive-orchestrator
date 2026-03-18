"""Driver and run-contract tests for Hive 2.2 foundations."""

# pylint: disable=missing-function-docstring,missing-class-docstring,unused-argument
# pylint: disable=import-error,no-name-in-module,line-too-long,too-few-public-methods
# pylint: disable=duplicate-code

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import time

import pytest

from tests.conftest import init_git_repo, write_safe_program
from hive.cli.main import main as hive_main
from src.hive.drivers import (
    RunBudget,
    RunHandle,
    RunLaunchRequest,
    RunProgress,
    RunStatus,
    RunWorkspace,
    SteeringRequest,
    get_driver,
)
from src.hive.runtime import list_approvals, request_approval
from src.hive.runs.program import _build_reroute_launch_request
from src.hive.runs.engine import (
    _refresh_workspace_state,
    accept_run,
    eval_run,
    load_run,
    start_run,
    steer_run,
)
from src.hive.scheduler.query import ready_tasks
from src.hive.store.task_files import create_task, update_task


def _invoke_cli_json(capsys, argv: list[str]) -> dict:
    exit_code = hive_main(argv)
    captured = capsys.readouterr()
    assert exit_code == 0
    return json.loads(captured.out)


def _write_fake_codex_binary(base_dir: str) -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="fake-codex-"))
    target = temp_dir / "fake-codex.py"
    target.write_text(
        """#!/usr/bin/env python3
import json
import sys


def send(payload):
    sys.stdout.write(json.dumps(payload, sort_keys=True) + "\\n")
    sys.stdout.flush()


def main():
    args = sys.argv[1:]
    if args == ["--help"]:
        sys.stdout.write("Codex CLI\\nCommands:\\n  exec\\n  app-server\\n")
        return 0
    if args == ["--version"]:
        sys.stdout.write("codex 0.0.0-test\\n")
        return 0
    if args[:2] == ["app-server", "--help"]:
        sys.stdout.write("Usage: codex app-server --listen <URL>\\n  --listen <URL>\\n")
        return 0
    if args[:3] != ["app-server", "--listen", "stdio://"]:
        return 2

    thread_id = "thread_test"
    turn_id = "turn_test"
    approval_request_id = 9001
    approval_request_kind = None

    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        message = json.loads(line)
        method = message.get("method")
        if method == "initialize":
            send({"id": message["id"], "result": {"userAgent": "fake-codex"}})
        elif method == "thread/start":
            send(
                {
                    "id": message["id"],
                    "result": {
                        "thread": {"id": thread_id, "status": {"type": "idle"}},
                        "model": "gpt-5.4",
                        "modelProvider": "openai",
                        "cwd": ".",
                        "approvalPolicy": "on-request",
                        "sandbox": {"type": "workspaceWrite"},
                    },
                }
            )
            send({"method": "thread/started", "params": {"thread": {"id": thread_id, "status": {"type": "idle"}}}})
            send({"method": "thread/status/changed", "params": {"threadId": thread_id, "status": {"type": "idle"}}})
        elif method == "turn/start":
            prompt = " ".join(
                item.get("text", "")
                for item in message.get("params", {}).get("input", [])
                if isinstance(item, dict)
            )
            send(
                {
                    "id": message["id"],
                    "result": {"turn": {"id": turn_id, "items": [], "status": "inProgress", "error": None}},
                }
            )
            send(
                {
                    "method": "turn/started",
                    "params": {"threadId": thread_id, "turn": {"id": turn_id, "items": [], "status": "inProgress", "error": None}},
                }
            )
            send({"method": "thread/status/changed", "params": {"threadId": thread_id, "status": {"type": "active", "activeFlags": []}}})
            if "WAIT_FOR_INTERRUPT" in prompt:
                continue
            send({"method": "item/agentMessage/delta", "params": {"threadId": thread_id, "turnId": turn_id, "itemId": "msg_1", "delta": "Working"}})
            if "REQUEST_FILE_APPROVAL_CALL_ID_ONLY" in prompt:
                approval_request_kind = "file_call_id_only"
                send(
                    {
                        "method": "item/fileChange/requestApproval",
                        "id": approval_request_id,
                        "params": {
                            "threadId": thread_id,
                            "turnId": turn_id,
                            "callId": "patch_1",
                            "grantRoot": ".",
                            "reason": "Need to update README",
                            "fileChanges": [{"path": "README.md", "kind": "update"}],
                        },
                    }
                )
                continue
            approval_request_kind = "command"
            send({"method": "turn/plan/updated", "params": {"threadId": thread_id, "turnId": turn_id, "explanation": "Inspect repo", "plan": [{"step": "Inspect repo", "status": "inProgress"}]}})
            send(
                {
                    "method": "item/commandExecution/requestApproval",
                    "id": approval_request_id,
                    "params": {
                        "threadId": thread_id,
                        "turnId": turn_id,
                        "itemId": "cmd_1",
                        "approvalId": "appr_1",
                        "command": "git status",
                        "cwd": ".",
                        "reason": "Need repo status",
                    },
                }
            )
        elif method == "turn/interrupt":
            send({"id": message["id"], "result": {}})
            send({"method": "thread/status/changed", "params": {"threadId": thread_id, "status": {"type": "idle"}}})
            send(
                {
                    "method": "thread/tokenUsage/updated",
                    "params": {
                        "threadId": thread_id,
                        "turnId": turn_id,
                        "tokenUsage": {
                            "total": {
                                "totalTokens": 7,
                                "inputTokens": 3,
                                "cachedInputTokens": 0,
                                "outputTokens": 4,
                                "reasoningOutputTokens": 0,
                            }
                        },
                    },
                }
            )
            send(
                {
                    "method": "turn/completed",
                    "params": {"threadId": thread_id, "turn": {"id": turn_id, "items": [], "status": "interrupted", "error": None}},
                }
            )
            return 0
        elif message.get("id") == approval_request_id and "result" in message:
            if approval_request_kind == "file_call_id_only":
                send({"method": "item/agentMessage/delta", "params": {"threadId": thread_id, "turnId": turn_id, "itemId": "msg_1", "delta": " file approved"}})
                send({"method": "turn/diff/updated", "params": {"threadId": thread_id, "turnId": turn_id, "diff": "diff --git a/README.md b/README.md"}})
                send(
                    {
                        "method": "item/completed",
                        "params": {
                            "threadId": thread_id,
                            "turnId": turn_id,
                            "item": {"type": "agentMessage", "id": "msg_1", "text": "Working file approved", "phase": "final_answer"},
                        },
                    }
                )
                send(
                    {
                        "method": "thread/tokenUsage/updated",
                        "params": {
                            "threadId": thread_id,
                            "turnId": turn_id,
                            "tokenUsage": {
                                "total": {
                                    "totalTokens": 12,
                                    "inputTokens": 5,
                                    "cachedInputTokens": 1,
                                    "outputTokens": 6,
                                    "reasoningOutputTokens": 0,
                                }
                            },
                        },
                    }
                )
                send({"method": "thread/status/changed", "params": {"threadId": thread_id, "status": {"type": "idle"}}})
                send(
                    {
                        "method": "turn/completed",
                        "params": {"threadId": thread_id, "turn": {"id": turn_id, "items": [], "status": "completed", "error": None}},
                    }
                )
                return 0
            send({"method": "item/agentMessage/delta", "params": {"threadId": thread_id, "turnId": turn_id, "itemId": "msg_1", "delta": " approved"}})
            send({"method": "turn/diff/updated", "params": {"threadId": thread_id, "turnId": turn_id, "diff": "diff --git a/README.md b/README.md"}})
            send(
                {
                    "method": "item/completed",
                    "params": {
                        "threadId": thread_id,
                        "turnId": turn_id,
                        "item": {"type": "agentMessage", "id": "msg_1", "text": "Working approved", "phase": "final_answer"},
                    },
                }
            )
            send(
                {
                    "method": "thread/tokenUsage/updated",
                    "params": {
                        "threadId": thread_id,
                        "turnId": turn_id,
                        "tokenUsage": {
                            "total": {
                                "totalTokens": 9,
                                "inputTokens": 4,
                                "cachedInputTokens": 1,
                                "outputTokens": 5,
                                "reasoningOutputTokens": 0,
                            }
                        },
                    },
                }
            )
            send({"method": "thread/status/changed", "params": {"threadId": thread_id, "status": {"type": "idle"}}})
            send(
                {
                    "method": "turn/completed",
                    "params": {"threadId": thread_id, "turn": {"id": turn_id, "items": [], "status": "completed", "error": None}},
                }
            )
            return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
""",
        encoding="utf-8",
    )
    target.chmod(0o755)
    return target


def _poll_run_status(temp_hive_dir: str, capsys, run_id: str, *, attempts: int = 20) -> dict:
    payload: dict = {}
    for _ in range(attempts):
        payload = _invoke_cli_json(capsys, ["--path", temp_hive_dir, "--json", "run", "status", run_id])
        if payload.get("status"):
            return payload
        time.sleep(0.1)
    return payload


def _wait_for_run_status(
    temp_hive_dir: str,
    capsys,
    run_id: str,
    *,
    predicate,
    attempts: int = 80,
    sleep_seconds: float = 0.1,
) -> dict:
    payload: dict = {}
    for _ in range(attempts):
        payload = _invoke_cli_json(capsys, ["--path", temp_hive_dir, "--json", "run", "status", run_id])
        status = payload.get("status")
        if isinstance(status, dict) and predicate(status):
            return payload
        time.sleep(sleep_seconds)
    pytest.fail(
        "Timed out waiting for run status predicate for "
        f"{run_id}. Last payload: {json.dumps(payload, sort_keys=True)}"
    )


class TestHiveDrivers:
    """Conformance tests for the v2.2 driver layer."""

    def test_cli_drivers_list_shows_all_supported_drivers(self, temp_hive_dir, capsys):
        payload = _invoke_cli_json(capsys, ["--path", temp_hive_dir, "--json", "drivers", "list"])

        # This one is intentionally order-sensitive: the CLI surface should present drivers in a
        # stable, predictable order for operators and downstream tooling.
        assert [driver["driver"] for driver in payload["drivers"]] == [
            "local",
            "manual",
            "codex",
            "claude-code",
        ]

    def test_run_start_for_external_harness_drivers_writes_normalized_artifacts(
        self, temp_hive_dir, capsys
    ):
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
        create_task(temp_hive_dir, "demo", "Codex slice", status="ready", priority=1)
        create_task(temp_hive_dir, "demo", "Claude slice", status="ready", priority=1)
        subprocess.run(["git", "add", "-A"], cwd=temp_hive_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Bootstrap workspace"],
            cwd=temp_hive_dir,
            check=True,
            capture_output=True,
            text=True,
        )

        for driver_name in ("codex", "claude-code"):
            task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
            run = start_run(temp_hive_dir, task_id, driver_name=driver_name)
            metadata = load_run(temp_hive_dir, run.id)
            run_root = Path(temp_hive_dir) / ".hive" / "runs" / run.id

            assert metadata["driver"] == driver_name
            assert metadata["status"] == "awaiting_input"
            assert (run_root / "launch.json").exists()
            assert (run_root / "context" / "manifest.json").exists()
            assert (run_root / "context" / "compiled" / "run-brief.md").exists()
            assert (run_root / "transcript" / "normalized.jsonl").exists()
            assert (run_root / "workspace" / "patch.diff").exists()
            assert (run_root / "workspace" / "changed_files.json").exists()
            assert (run_root / "driver" / "driver-metadata.json").exists()
            assert (run_root / "driver" / "handles.json").exists()
            assert (run_root / "driver" / "approval-channel.ndjson").exists()
            assert (run_root / "review" / "summary.md").exists()
            assert (run_root / "review" / "review.md").exists()
            assert (run_root / "plan" / "plan.md").exists()
            assert (run_root / "plan" / "plan.json").exists()
            assert (run_root / "logs" / "stdout.txt").exists()
            assert (run_root / "logs" / "stderr.txt").exists()
            assert (run_root / "events.jsonl").exists()

    def test_local_run_start_records_v22_event_sequence_and_status(self, temp_hive_dir, capsys):
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
        subprocess.run(["git", "add", "-A"], cwd=temp_hive_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Bootstrap workspace"],
            cwd=temp_hive_dir,
            check=True,
            capture_output=True,
            text=True,
        )

        task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
        run = start_run(temp_hive_dir, task_id, driver_name="local")
        payload = _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "run", "status", run.id],
        )
        events_path = Path(temp_hive_dir) / ".hive" / "runs" / run.id / "events.jsonl"
        event_types = [
            json.loads(line)["type"]
            for line in events_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

        assert payload["status"]["state"] == "running"
        assert payload["status"]["driver"] == "local"
        assert event_types[:5] == [
            "run.queued",
            "run.context_compiled",
            "context.compiled",
            "run.launch_started",
            "run.launched",
        ]
        assert "run.status.changed" in event_types

    def test_cli_steer_reroute_preserves_lineage_and_updates_driver(self, temp_hive_dir, capsys):
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
        subprocess.run(["git", "add", "-A"], cwd=temp_hive_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Bootstrap workspace"],
            cwd=temp_hive_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
        run = start_run(temp_hive_dir, task_id, driver_name="local")

        payload = _invoke_cli_json(
            capsys,
            [
                "--path",
                temp_hive_dir,
                "--json",
                "steer",
                "reroute",
                run.id,
                "--driver",
                "codex",
                "--reason",
                "Use Codex for a broader repo pass",
            ],
        )
        metadata = load_run(temp_hive_dir, run.id)
        handles_path = Path(temp_hive_dir) / ".hive" / "runs" / run.id / "driver" / "handles.json"
        handles = json.loads(handles_path.read_text(encoding="utf-8"))
        timeline = (
            Path(temp_hive_dir) / ".hive" / "runs" / run.id / "events.jsonl"
        ).read_text(encoding="utf-8")

        assert payload["run"]["driver"] == "codex"
        assert metadata["driver"] == "codex"
        assert metadata["status"] == "awaiting_input"
        assert handles["active"]["driver"] == "codex"
        assert len(handles["history"]) >= 2
        assert "steering.reroute_requested" in timeline
        assert "steering.rerouted" in timeline

    def test_codex_live_launch_persists_exec_handle(self, temp_hive_dir, capsys, monkeypatch):
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
        subprocess.run(["git", "add", "-A"], cwd=temp_hive_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Bootstrap workspace"],
            cwd=temp_hive_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        driver = get_driver("codex")

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
                session_id="pid-4242",
                event_cursor="0",
                approval_channel=str(request.metadata.get("approval_channel") or "") or None,
                metadata={"pid": 4242, "last_message_path": "/tmp/codex-last.txt"},
            )

        def fake_status(self, handle):
            return RunStatus(
                run_id=handle.run_id,
                state="running",
                health="healthy",
                driver="codex",
                progress=RunProgress(
                    phase="implementing",
                    message="Codex live exec is active.",
                    percent=20,
                ),
                waiting_on=None,
                last_event_at="2026-03-18T06:00:01Z",
                event_cursor="1",
                session={"launch_mode": "exec", "transport": "subprocess", "session_id": "pid-4242"},
                artifacts={"last_message_path": "/tmp/codex-last.txt"},
            )

        monkeypatch.setattr(type(driver), "_live_exec_enabled", fake_live_exec_enabled)
        monkeypatch.setattr(type(driver), "_launch_live_exec", fake_launch_live_exec)
        monkeypatch.setattr(type(driver), "status", fake_status)

        task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
        run = start_run(temp_hive_dir, task_id, driver_name="codex")
        metadata = load_run(temp_hive_dir, run.id)
        handles = json.loads(
            (
                Path(temp_hive_dir) / ".hive" / "runs" / run.id / "driver" / "handles.json"
            ).read_text(encoding="utf-8")
        )

        assert metadata["status"] == "running"
        assert handles["active"]["launch_mode"] == "exec"
        assert handles["active"]["transport"] == "subprocess"
        assert handles["active"]["session_id"] == "pid-4242"
        assert handles["active"]["approval_channel"] == metadata["approval_channel_path"]
        assert handles["active"]["metadata"]["pid"] == 4242

    def test_codex_live_launch_falls_back_to_config_override_when_flag_is_missing(
        self, monkeypatch, tmp_path
    ):
        driver = get_driver("codex")
        captured: dict[str, object] = {}
        worktree = tmp_path / "worktree"
        artifacts = tmp_path / "run"
        worktree.mkdir()
        (artifacts / "driver").mkdir(parents=True)
        (artifacts / "logs").mkdir(parents=True)

        class FakeStdin:
            def __init__(self):
                self.buffer = ""
                self.closed = False

            def write(self, data):
                self.buffer += data
                return len(data)

            def close(self):
                self.closed = True

        class FakeProcess:
            def __init__(self, argv, **kwargs):
                captured["argv"] = argv
                captured["cwd"] = kwargs.get("cwd")
                self.pid = 4242
                self.stdin = FakeStdin()
                captured["stdin"] = self.stdin

        def fake_live_exec_enabled(self):
            return True

        def fake_detected_binary_details(self):
            return "codex", "/tmp/codex"

        def fake_command_output(self, *args):
            if args == ("--help",):
                return "Commands: exec app-server sandbox"
            if args == ("exec", "--help"):
                return "--json --ephemeral --sandbox --output-last-message --cd"
            if args == ("app-server", "--help"):
                return "--listen"
            return None

        def fake_build_exec_prompt(self, request):
            return "run the task"

        monkeypatch.setattr(type(driver), "_live_exec_enabled", fake_live_exec_enabled)
        monkeypatch.setattr(
            type(driver),
            "_detected_binary_details",
            fake_detected_binary_details,
        )
        monkeypatch.setattr(type(driver), "_command_output", fake_command_output)
        monkeypatch.setattr(type(driver), "_build_exec_prompt", fake_build_exec_prompt)
        monkeypatch.setattr("src.hive.drivers.codex.subprocess.Popen", FakeProcess)

        handle = driver._launch_live_exec(
            RunLaunchRequest(
                run_id="run_live",
                task_id="task_live",
                project_id="demo",
                campaign_id=None,
                driver="codex",
                model="gpt-5.3-codex",
                budget=RunBudget(max_tokens=1000, max_cost_usd=1.0, max_wall_minutes=5),
                workspace=RunWorkspace(
                    repo_root=str(tmp_path),
                    worktree_path=str(worktree),
                    base_branch="main",
                ),
                compiled_context_path=str(artifacts / "context" / "compiled"),
                artifacts_path=str(artifacts),
                program_policy={},
            )
        )

        command_text = (artifacts / "driver" / "codex-exec-command.txt").read_text(
            encoding="utf-8"
        )
        assert handle is not None
        assert handle.status == "running"
        assert "approval_policy=" in command_text
        assert "--ask-for-approval" not in command_text
        assert "--sandbox workspace-write" in command_text
        assert "--cd" in command_text
        assert captured["cwd"] == str(worktree)
        assert "run the task" in captured["stdin"].buffer
        assert captured["stdin"].closed is True

    def test_codex_live_launch_prefers_native_approval_flag_when_available(
        self, monkeypatch, tmp_path
    ):
        driver = get_driver("codex")
        worktree = tmp_path / "worktree"
        artifacts = tmp_path / "run"
        worktree.mkdir()
        (artifacts / "driver").mkdir(parents=True)
        (artifacts / "logs").mkdir(parents=True)

        class FakeStdin:
            def write(self, data):
                return len(data)

            def close(self):
                return None

        class FakeProcess:
            def __init__(self, *args, **kwargs):
                self.pid = 4343
                self.stdin = FakeStdin()

        def fake_live_exec_enabled(self):
            return True

        def fake_detected_binary_details(self):
            return "codex", "/tmp/codex"

        def fake_command_output(self, *args):
            if args == ("--help",):
                return "Commands: exec app-server sandbox"
            if args == ("exec", "--help"):
                return (
                    "--json --ephemeral --sandbox --ask-for-approval "
                    "--output-last-message --cd"
                )
            if args == ("app-server", "--help"):
                return "--listen"
            return None

        def fake_build_exec_prompt(self, request):
            return "run the task"

        monkeypatch.setattr(type(driver), "_live_exec_enabled", fake_live_exec_enabled)
        monkeypatch.setattr(
            type(driver),
            "_detected_binary_details",
            fake_detected_binary_details,
        )
        monkeypatch.setattr(type(driver), "_command_output", fake_command_output)
        monkeypatch.setattr(type(driver), "_build_exec_prompt", fake_build_exec_prompt)
        monkeypatch.setattr("src.hive.drivers.codex.subprocess.Popen", FakeProcess)

        handle = driver._launch_live_exec(
            RunLaunchRequest(
                run_id="run_live",
                task_id="task_live",
                project_id="demo",
                campaign_id=None,
                driver="codex",
                model=None,
                budget=RunBudget(max_tokens=1000, max_cost_usd=1.0, max_wall_minutes=5),
                workspace=RunWorkspace(
                    repo_root=str(tmp_path),
                    worktree_path=str(worktree),
                    base_branch="main",
                ),
                compiled_context_path=str(artifacts / "context" / "compiled"),
                artifacts_path=str(artifacts),
                program_policy={},
            )
        )

        command_text = (artifacts / "driver" / "codex-exec-command.txt").read_text(
            encoding="utf-8"
        )
        assert handle is not None
        assert handle.status == "running"
        assert "--ask-for-approval never" in command_text
        assert "approval_policy=" not in command_text

    def test_run_status_refreshes_live_codex_driver_status(
        self, temp_hive_dir, capsys, monkeypatch
    ):
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
        subprocess.run(["git", "add", "-A"], cwd=temp_hive_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Bootstrap workspace"],
            cwd=temp_hive_dir,
            check=True,
            capture_output=True,
            text=True,
        )
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
                session_id="pid-9000",
                event_cursor="0",
                metadata={"pid": 9000, "last_message_path": "/tmp/codex-last.txt"},
            )

        def fake_status(self, handle):
            calls["count"] += 1
            cursor = "1" if calls["count"] == 1 else "7"
            return RunStatus(
                run_id=handle.run_id,
                state="running",
                health="healthy",
                driver="codex",
                progress=RunProgress(
                    phase="implementing",
                    message="Codex live exec is active.",
                    percent=35,
                ),
                waiting_on=None,
                last_event_at="2026-03-18T06:00:30Z",
                event_cursor=cursor,
                session={"launch_mode": "exec", "transport": "subprocess", "session_id": "pid-9000"},
                artifacts={"last_message_path": "/tmp/codex-last.txt", "raw_output_path": "/tmp/codex.jsonl"},
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
        handles = json.loads(
            (
                Path(temp_hive_dir) / ".hive" / "runs" / run.id / "driver" / "handles.json"
            ).read_text(encoding="utf-8")
        )

        assert payload["status"]["state"] == "running"
        assert payload["status"]["event_cursor"] == "7"
        assert payload["status"]["session"]["session_id"] == "pid-9000"
        assert metadata["metadata_json"]["driver_status"]["event_cursor"] == "7"
        assert handles["active"]["event_cursor"] == "7"

    def test_codex_cancel_interrupts_live_session(self, temp_hive_dir, capsys, monkeypatch):
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
        subprocess.run(["git", "add", "-A"], cwd=temp_hive_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Bootstrap workspace"],
            cwd=temp_hive_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        driver = get_driver("codex")
        interrupt_calls: list[str] = []

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
                session_id="pid-8128",
                metadata={"pid": 8128},
            )

        def fake_status(self, handle):
            return RunStatus(
                run_id=handle.run_id,
                state="running",
                health="healthy",
                driver="codex",
                progress=RunProgress(
                    phase="implementing",
                    message="Codex live exec is active.",
                    percent=10,
                ),
                waiting_on=None,
                last_event_at="2026-03-18T06:00:30Z",
                session={"launch_mode": "exec", "transport": "subprocess", "session_id": "pid-8128"},
            )

        def fake_interrupt(self, handle, mode):
            interrupt_calls.append(mode)
            return {"ok": True, "driver": "codex", "mode": mode, "pid": 8128}

        monkeypatch.setattr(type(driver), "_live_exec_enabled", fake_live_exec_enabled)
        monkeypatch.setattr(type(driver), "_launch_live_exec", fake_launch_live_exec)
        monkeypatch.setattr(type(driver), "status", fake_status)
        monkeypatch.setattr(type(driver), "interrupt", fake_interrupt)

        task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
        run = start_run(temp_hive_dir, task_id, driver_name="codex")
        payload = _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "steer", "cancel", run.id, "--reason", "Stop"],
        )
        metadata = load_run(temp_hive_dir, run.id)

        assert interrupt_calls == ["cancel"]
        assert payload["driver_ack"]["ok"] is True
        assert metadata["status"] == "cancelled"

    def test_codex_interrupt_targets_process_group(self, monkeypatch):
        driver = get_driver("codex")
        handle = RunHandle(
            run_id="run_codex_pg",
            driver="codex",
            driver_handle="codex:exec:4242",
            status="running",
            launched_at="2026-03-18T06:00:00Z",
            launch_mode="exec",
            transport="subprocess",
            metadata={"pid": 4242},
        )
        calls: list[tuple[int, object]] = []

        monkeypatch.setattr("src.hive.drivers.codex.os.getpgid", lambda pid: pid + 1000)
        monkeypatch.setattr(
            "src.hive.drivers.codex.os.killpg",
            lambda pgid, sig: calls.append((pgid, sig)),
        )

        payload = driver.interrupt(handle, "cancel")

        assert payload["ok"] is True
        assert calls and calls[0][0] == 5242

    def test_claude_live_launch_persists_exec_handle(self, temp_hive_dir, capsys, monkeypatch):
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
        subprocess.run(["git", "add", "-A"], cwd=temp_hive_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Bootstrap workspace"],
            cwd=temp_hive_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        driver = get_driver("claude-code")

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
                session_id="sess-4242",
                event_cursor="0",
                approval_channel=str(request.metadata.get("approval_channel") or "") or None,
                metadata={"pid": 4242, "last_message_path": "/tmp/claude-last.txt"},
            )

        def fake_status(self, handle):
            return RunStatus(
                run_id=handle.run_id,
                state="running",
                health="healthy",
                driver="claude-code",
                progress=RunProgress(
                    phase="implementing",
                    message="Claude live exec is active.",
                    percent=20,
                ),
                waiting_on=None,
                last_event_at="2026-03-18T06:00:01Z",
                event_cursor="1",
                session={
                    "launch_mode": "exec",
                    "transport": "subprocess",
                    "session_id": "sess-4242",
                },
                artifacts={"last_message_path": "/tmp/claude-last.txt"},
            )

        monkeypatch.setattr(type(driver), "_live_exec_enabled", fake_live_exec_enabled)
        monkeypatch.setattr(type(driver), "_launch_live_exec", fake_launch_live_exec)
        monkeypatch.setattr(type(driver), "status", fake_status)

        task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
        run = start_run(temp_hive_dir, task_id, driver_name="claude-code")
        metadata = load_run(temp_hive_dir, run.id)
        handles = json.loads(
            (
                Path(temp_hive_dir) / ".hive" / "runs" / run.id / "driver" / "handles.json"
            ).read_text(encoding="utf-8")
        )

        assert metadata["status"] == "running"
        assert handles["active"]["launch_mode"] == "exec"
        assert handles["active"]["transport"] == "subprocess"
        assert handles["active"]["session_id"] == "sess-4242"
        assert handles["active"]["approval_channel"] == metadata["approval_channel_path"]
        assert handles["active"]["metadata"]["pid"] == 4242

    def test_approval_resolution_forwards_to_live_driver_channel(
        self, temp_hive_dir, capsys, monkeypatch
    ):
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
        subprocess.run(["git", "add", "-A"], cwd=temp_hive_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Bootstrap workspace"],
            cwd=temp_hive_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        driver = get_driver("codex")

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
                session_id="pid-7331",
                event_cursor="0",
                approval_channel=str(request.metadata.get("approval_channel") or "") or None,
                metadata={"pid": 7331},
            )

        def fake_status(self, handle):
            return RunStatus(
                run_id=handle.run_id,
                state="running",
                health="healthy",
                driver="codex",
                progress=RunProgress(
                    phase="implementing",
                    message="Codex live exec is active.",
                    percent=20,
                ),
                waiting_on=None,
                last_event_at="2026-03-18T06:00:01Z",
                event_cursor="1",
                session={
                    "launch_mode": "exec",
                    "transport": "subprocess",
                    "session_id": "pid-7331",
                },
            )

        monkeypatch.setattr(type(driver), "_live_exec_enabled", fake_live_exec_enabled)
        monkeypatch.setattr(type(driver), "_launch_live_exec", fake_launch_live_exec)
        monkeypatch.setattr(type(driver), "status", fake_status)

        task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
        run = start_run(temp_hive_dir, task_id, driver_name="codex")
        approval = request_approval(
            temp_hive_dir,
            run.id,
            kind="command",
            title="Approve git status",
            summary="Codex wants to inspect the repo status.",
            requested_by="driver:codex",
            payload={"command": "git status"},
        )

        payload = steer_run(
            temp_hive_dir,
            run.id,
            SteeringRequest(action="approve", note="safe"),
            actor="operator",
        )
        metadata = load_run(temp_hive_dir, run.id)
        channel_path = Path(str(metadata["approval_channel_path"]))
        broker_records = [
            json.loads(line)
            for line in channel_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        event_types = [
            json.loads(line)["type"]
            for line in (Path(temp_hive_dir) / ".hive" / "runs" / run.id / "events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]

        assert payload["approval"]["status"] == "approved"
        assert payload["driver_ack"]["ok"] is True
        assert broker_records[-1]["approval_id"] == approval["approval_id"]
        assert broker_records[-1]["resolution"] == "approved"
        assert broker_records[-1]["payload"]["command"] == "git status"
        assert metadata["metadata_json"]["steering_history"][-1]["action"] == "approve"
        assert metadata["metadata_json"]["approval_forwarding"][-1]["driver_ack"]["channel"] == str(
            channel_path
        )
        assert "approval.forwarded" in event_types

    def test_cli_steer_approve_targets_explicit_approval_id(self, temp_hive_dir, capsys, monkeypatch):
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
        subprocess.run(["git", "add", "-A"], cwd=temp_hive_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Bootstrap workspace"],
            cwd=temp_hive_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        driver = get_driver("codex")

        def fake_live_exec_enabled(self):
            return True

        def fake_launch_live_exec(self, request):
            return RunHandle(
                run_id=request.run_id,
                driver=self.name,
                driver_handle="codex:exec:pid-7331",
                status="running",
                launched_at="2026-03-18T06:00:00Z",
                launch_mode="exec",
                transport="subprocess",
                session_id="pid-7331",
                event_cursor="0",
                approval_channel=str(request.metadata.get("approval_channel") or ""),
            )

        def fake_status(self, handle):
            return RunStatus(
                run_id=handle.run_id,
                state="running",
                health="blocked",
                driver=self.name,
                progress=RunProgress(
                    phase="waiting",
                    message="Codex live exec is waiting on approval.",
                    percent=0,
                ),
                waiting_on="approval",
                last_event_at="2026-03-18T06:00:01Z",
                pending_approvals=[],
            )

        monkeypatch.setattr(type(driver), "_live_exec_enabled", fake_live_exec_enabled)
        monkeypatch.setattr(type(driver), "_launch_live_exec", fake_launch_live_exec)
        monkeypatch.setattr(type(driver), "status", fake_status)

        task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
        run = start_run(temp_hive_dir, task_id, driver_name="codex")
        first = request_approval(
            temp_hive_dir,
            run.id,
            kind="command",
            title="Approve git status",
            summary="Codex wants to inspect the repo status.",
            requested_by="driver:codex",
            payload={"command": "git status"},
        )
        second = request_approval(
            temp_hive_dir,
            run.id,
            kind="command",
            title="Approve git diff",
            summary="Codex wants to inspect the current diff.",
            requested_by="driver:codex",
            payload={"command": "git diff"},
        )

        payload = _invoke_cli_json(
            capsys,
            [
                "--path",
                temp_hive_dir,
                "--json",
                "steer",
                "approve",
                run.id,
                "--approval-id",
                second["approval_id"],
                "--owner",
                "operator",
            ],
        )

        approvals = {item["approval_id"]: item["status"] for item in list_approvals(temp_hive_dir, run.id)}

        assert payload["approval"]["approval_id"] == second["approval_id"]
        assert approvals[first["approval_id"]] == "pending"
        assert approvals[second["approval_id"]] == "approved"

    def test_multiple_pending_approvals_require_explicit_target(
        self, temp_hive_dir, capsys, monkeypatch
    ):
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
        subprocess.run(["git", "add", "-A"], cwd=temp_hive_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Bootstrap workspace"],
            cwd=temp_hive_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        driver = get_driver("codex")

        def fake_live_exec_enabled(self):
            return True

        def fake_launch_live_exec(self, request):
            return RunHandle(
                run_id=request.run_id,
                driver=self.name,
                driver_handle="codex:exec:pid-7331",
                status="running",
                launched_at="2026-03-18T06:00:00Z",
                launch_mode="exec",
                transport="subprocess",
                session_id="pid-7331",
                event_cursor="0",
                approval_channel=str(request.metadata.get("approval_channel") or ""),
            )

        def fake_status(self, handle):
            return RunStatus(
                run_id=handle.run_id,
                state="running",
                health="blocked",
                driver=self.name,
                progress=RunProgress(
                    phase="waiting",
                    message="Codex live exec is waiting on approval.",
                    percent=0,
                ),
                waiting_on="approval",
                last_event_at="2026-03-18T06:00:01Z",
                pending_approvals=[],
            )

        monkeypatch.setattr(type(driver), "_live_exec_enabled", fake_live_exec_enabled)
        monkeypatch.setattr(type(driver), "_launch_live_exec", fake_launch_live_exec)
        monkeypatch.setattr(type(driver), "status", fake_status)

        task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
        run = start_run(temp_hive_dir, task_id, driver_name="codex")
        request_approval(
            temp_hive_dir,
            run.id,
            kind="command",
            title="Approve git status",
            summary="Codex wants to inspect the repo status.",
            requested_by="driver:codex",
            payload={"command": "git status"},
        )
        request_approval(
            temp_hive_dir,
            run.id,
            kind="command",
            title="Approve git diff",
            summary="Codex wants to inspect the current diff.",
            requested_by="driver:codex",
            payload={"command": "git diff"},
        )

        with pytest.raises(ValueError, match="Multiple pending approvals require an explicit approval_id"):
            steer_run(
                temp_hive_dir,
                run.id,
                SteeringRequest(action="approve"),
                actor="operator",
            )

    def test_codex_app_server_launches_live_run_and_round_trips_approval(
        self, temp_hive_dir, capsys, monkeypatch
    ):
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
        subprocess.run(["git", "add", "-A"], cwd=temp_hive_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Bootstrap workspace"],
            cwd=temp_hive_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        driver = get_driver("codex")
        fake_binary = _write_fake_codex_binary(temp_hive_dir)

        def fake_detected_binary_details(self):
            return ("codex", str(fake_binary))

        monkeypatch.setattr(type(driver), "_detected_binary_details", fake_detected_binary_details)
        monkeypatch.setenv("HIVE_CODEX_LIVE_APP_SERVER", "1")
        monkeypatch.delenv("HIVE_CODEX_LIVE_EXEC", raising=False)

        task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
        run = start_run(temp_hive_dir, task_id, driver_name="codex")

        pending_payload = _wait_for_run_status(
            temp_hive_dir,
            capsys,
            run.id,
            predicate=lambda status: bool(status.get("pending_approvals")),
            attempts=200,
        )

        approval_id = pending_payload["status"]["pending_approvals"][0]["approval_id"]
        resolution = steer_run(
            temp_hive_dir,
            run.id,
            SteeringRequest(action="approve", target={"approval_id": approval_id}),
            actor="operator",
        )

        completed_payload = _wait_for_run_status(
            temp_hive_dir,
            capsys,
            run.id,
            predicate=lambda status: status.get("state") == "completed_candidate",
        )

        metadata = load_run(temp_hive_dir, run.id)
        run_root = Path(temp_hive_dir) / ".hive" / "runs" / run.id
        handles = json.loads((run_root / "driver" / "handles.json").read_text(encoding="utf-8"))
        transcript = (run_root / "transcript.ndjson").read_text(encoding="utf-8")

        assert resolution["driver_ack"]["ok"] is True
        assert pending_payload["status"]["session"]["launch_mode"] == "app_server"
        assert pending_payload["status"]["session"]["transport"] == "stdio-jsonrpc"
        assert pending_payload["status"]["waiting_on"] == "approval"
        assert pending_payload["status"]["pending_approvals"][0]["payload"]["command"] == "git status"
        assert completed_payload["status"]["state"] == "completed_candidate"
        assert completed_payload["status"]["session"]["thread_id"] == "thread_test"
        assert handles["active"]["launch_mode"] == "app_server"
        assert handles["active"]["thread_id"] == "thread_test"
        assert metadata["metadata_json"]["budget_rollup"]["spent_tokens"] == 9
        assert "Working" in transcript
        assert "approved" in transcript

    def test_codex_app_server_cancel_routes_interrupt_request(
        self, temp_hive_dir, capsys, monkeypatch
    ):
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
        subprocess.run(["git", "add", "-A"], cwd=temp_hive_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Bootstrap workspace"],
            cwd=temp_hive_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        driver = get_driver("codex")
        fake_binary = _write_fake_codex_binary(temp_hive_dir)

        def fake_detected_binary_details(self):
            return ("codex", str(fake_binary))

        def fake_prompt(self, request):
            return "WAIT_FOR_INTERRUPT"

        monkeypatch.setattr(type(driver), "_detected_binary_details", fake_detected_binary_details)
        monkeypatch.setattr(type(driver), "_build_exec_prompt", fake_prompt)
        monkeypatch.setenv("HIVE_CODEX_LIVE_APP_SERVER", "1")
        monkeypatch.delenv("HIVE_CODEX_LIVE_EXEC", raising=False)

        task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
        run = start_run(temp_hive_dir, task_id, driver_name="codex")

        interrupt_payload = steer_run(
            temp_hive_dir,
            run.id,
            SteeringRequest(action="cancel"),
            actor="operator",
        )

        cancelled_payload = _wait_for_run_status(
            temp_hive_dir,
            capsys,
            run.id,
            predicate=lambda status: status.get("state") == "cancelled",
            attempts=200,
        )

        assert interrupt_payload["driver_ack"]["ok"] is True
        assert cancelled_payload["status"]["state"] == "cancelled"
        assert cancelled_payload["status"]["session"]["launch_mode"] == "app_server"

    def test_codex_app_server_file_approval_supports_call_id_only_requests(
        self, temp_hive_dir, capsys, monkeypatch
    ):
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
        subprocess.run(["git", "add", "-A"], cwd=temp_hive_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Bootstrap workspace"],
            cwd=temp_hive_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        driver = get_driver("codex")
        fake_binary = _write_fake_codex_binary(temp_hive_dir)

        def fake_detected_binary_details(self):
            return ("codex", str(fake_binary))

        def fake_prompt(self, request):
            return "REQUEST_FILE_APPROVAL_CALL_ID_ONLY"

        monkeypatch.setattr(type(driver), "_detected_binary_details", fake_detected_binary_details)
        monkeypatch.setattr(type(driver), "_build_exec_prompt", fake_prompt)
        monkeypatch.setenv("HIVE_CODEX_LIVE_APP_SERVER", "1")
        monkeypatch.delenv("HIVE_CODEX_LIVE_EXEC", raising=False)

        task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
        run = start_run(temp_hive_dir, task_id, driver_name="codex")

        pending_payload = _wait_for_run_status(
            temp_hive_dir,
            capsys,
            run.id,
            predicate=lambda status: bool(status.get("pending_approvals")),
            attempts=200,
        )

        pending_approval = pending_payload["status"]["pending_approvals"][0]
        resolution = steer_run(
            temp_hive_dir,
            run.id,
            SteeringRequest(action="approve", target={"approval_id": pending_approval["approval_id"]}),
            actor="operator",
        )

        completed_payload = _wait_for_run_status(
            temp_hive_dir,
            capsys,
            run.id,
            predicate=lambda status: status.get("state") == "completed_candidate",
        )

        metadata = load_run(temp_hive_dir, run.id)
        transcript = (
            Path(temp_hive_dir) / ".hive" / "runs" / run.id / "transcript.ndjson"
        ).read_text(encoding="utf-8")

        assert pending_approval["kind"] == "file"
        assert pending_approval["payload"]["call_id"] == "patch_1"
        assert pending_approval["payload"]["grant_root"] == "."
        assert resolution["driver_ack"]["ok"] is True
        assert completed_payload["status"]["state"] == "completed_candidate"
        assert metadata["metadata_json"]["budget_rollup"]["spent_tokens"] == 12
        assert "file approved" in transcript

    def test_codex_app_server_recovers_completed_turn_without_exit_marker(self, tmp_path, monkeypatch):
        driver = get_driver("codex")
        raw_output_path = tmp_path / "codex-events.jsonl"
        raw_output_path.write_text("", encoding="utf-8")
        state_path = tmp_path / "codex-state.json"
        state_path.write_text(
            json.dumps(
                {
                    "thread_id": "thread_1",
                    "thread_status": "idle",
                    "turn_id": "turn_1",
                    "turn_status": "completed",
                    "token_usage": {"total": {"totalTokens": 12, "inputTokens": 5, "outputTokens": 7}},
                }
            ),
            encoding="utf-8",
        )

        monkeypatch.setattr(type(driver), "_pid_is_running", staticmethod(lambda pid: False))

        status = driver.status(
            RunHandle(
                run_id="run_1",
                driver="codex",
                driver_handle="codex:app-server:7000",
                status="running",
                launched_at="2026-03-18T06:00:00Z",
                launch_mode="app_server",
                transport="stdio-jsonrpc",
                session_id="7000",
                event_cursor="0",
                metadata={
                    "pid": 7000,
                    "raw_output_path": str(raw_output_path),
                    "state_path": str(state_path),
                    "exit_code_path": str(tmp_path / "missing-exit.txt"),
                },
            )
        )

        assert status.state == "completed_candidate"
        assert status.health == "needs_attention"
        assert status.waiting_on == "review"
        assert status.budget.spent_tokens == 12

    def test_claude_live_exec_recovers_result_without_exit_marker(self, tmp_path, monkeypatch):
        driver = get_driver("claude-code")
        raw_output_path = tmp_path / "claude-print-result.json"
        raw_output_path.write_text(
            json.dumps(
                {
                    "session_id": "sess_1",
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

        monkeypatch.setattr(type(driver), "_pid_is_running", staticmethod(lambda pid: False))

        status = driver.status(
            RunHandle(
                run_id="run_1",
                driver="claude-code",
                driver_handle="claude-code:exec:7000",
                status="running",
                launched_at="2026-03-18T06:00:00Z",
                launch_mode="exec",
                transport="subprocess",
                session_id="sess_1",
                event_cursor="0",
                metadata={
                    "pid": 7000,
                    "raw_output_path": str(raw_output_path),
                    "last_message_path": str(tmp_path / "last-message.txt"),
                    "exit_code_path": str(tmp_path / "missing-exit.txt"),
                },
            )
        )

        assert status.state == "completed_candidate"
        assert status.health == "needs_attention"
        assert status.waiting_on == "review"
        assert status.budget.spent_tokens == 123
        assert status.budget.spent_cost_usd == pytest.approx(0.45)

    def test_run_status_refreshes_live_claude_driver_status(
        self, temp_hive_dir, capsys, monkeypatch
    ):
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
        subprocess.run(["git", "add", "-A"], cwd=temp_hive_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Bootstrap workspace"],
            cwd=temp_hive_dir,
            check=True,
            capture_output=True,
            text=True,
        )
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
                session_id="sess-9000",
                event_cursor="0",
                metadata={"pid": 9000, "last_message_path": "/tmp/claude-last.txt"},
            )

        def fake_status(self, handle):
            calls["count"] += 1
            cursor = "1" if calls["count"] == 1 else "6"
            return RunStatus(
                run_id=handle.run_id,
                state="running",
                health="healthy",
                driver="claude-code",
                progress=RunProgress(
                    phase="implementing",
                    message="Claude live exec is active.",
                    percent=35,
                ),
                waiting_on=None,
                last_event_at="2026-03-18T06:00:30Z",
                event_cursor=cursor,
                session={
                    "launch_mode": "exec",
                    "transport": "subprocess",
                    "session_id": "sess-9000",
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
        handles = json.loads(
            (
                Path(temp_hive_dir) / ".hive" / "runs" / run.id / "driver" / "handles.json"
            ).read_text(encoding="utf-8")
        )

        assert payload["status"]["state"] == "running"
        assert payload["status"]["event_cursor"] == "6"
        assert payload["status"]["session"]["session_id"] == "sess-9000"
        assert metadata["metadata_json"]["driver_status"]["event_cursor"] == "6"
        assert handles["active"]["event_cursor"] == "6"

    def test_claude_cancel_interrupts_live_session(self, temp_hive_dir, capsys, monkeypatch):
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
        subprocess.run(["git", "add", "-A"], cwd=temp_hive_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Bootstrap workspace"],
            cwd=temp_hive_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        driver = get_driver("claude-code")
        interrupt_calls: list[str] = []

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
                session_id="sess-8128",
                metadata={"pid": 8128},
            )

        def fake_status(self, handle):
            return RunStatus(
                run_id=handle.run_id,
                state="running",
                health="healthy",
                driver="claude-code",
                progress=RunProgress(
                    phase="implementing",
                    message="Claude live exec is active.",
                    percent=10,
                ),
                waiting_on=None,
                last_event_at="2026-03-18T06:00:30Z",
                session={
                    "launch_mode": "exec",
                    "transport": "subprocess",
                    "session_id": "sess-8128",
                },
            )

        def fake_interrupt(self, handle, mode):
            interrupt_calls.append(mode)
            return {"ok": True, "driver": "claude-code", "mode": mode, "pid": 8128}

        monkeypatch.setattr(type(driver), "_live_exec_enabled", fake_live_exec_enabled)
        monkeypatch.setattr(type(driver), "_launch_live_exec", fake_launch_live_exec)
        monkeypatch.setattr(type(driver), "status", fake_status)
        monkeypatch.setattr(type(driver), "interrupt", fake_interrupt)

        task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
        run = start_run(temp_hive_dir, task_id, driver_name="claude-code")
        payload = _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "steer", "cancel", run.id, "--reason", "Stop"],
        )
        metadata = load_run(temp_hive_dir, run.id)

        assert interrupt_calls == ["cancel"]
        assert payload["driver_ack"]["ok"] is True
        assert metadata["status"] == "cancelled"

    def test_claude_interrupt_targets_process_group(self, monkeypatch):
        driver = get_driver("claude-code")
        handle = RunHandle(
            run_id="run_claude_pg",
            driver="claude-code",
            driver_handle="claude-code:exec:3131",
            status="running",
            launched_at="2026-03-18T06:00:00Z",
            launch_mode="exec",
            transport="subprocess",
            metadata={"pid": 3131},
        )
        calls: list[tuple[int, object]] = []

        monkeypatch.setattr("src.hive.drivers.claude_code.os.getpgid", lambda pid: pid + 2000)
        monkeypatch.setattr(
            "src.hive.drivers.claude_code.os.killpg",
            lambda pgid, sig: calls.append((pgid, sig)),
        )

        payload = driver.interrupt(handle, "cancel")

        assert payload["ok"] is True
        assert calls and calls[0][0] == 5131

    def test_same_run_can_move_from_local_to_codex_to_claude_code(self, temp_hive_dir, capsys):
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
        subprocess.run(["git", "add", "-A"], cwd=temp_hive_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Bootstrap workspace"],
            cwd=temp_hive_dir,
            check=True,
            capture_output=True,
            text=True,
        )

        task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
        run = start_run(temp_hive_dir, task_id, driver_name="local")

        _invoke_cli_json(
            capsys,
            [
                "--path",
                temp_hive_dir,
                "--json",
                "steer",
                "reroute",
                run.id,
                "--driver",
                "codex",
                "--reason",
                "Use Codex for stronger repo-wide reasoning",
            ],
        )
        _invoke_cli_json(
            capsys,
            [
                "--path",
                temp_hive_dir,
                "--json",
                "steer",
                "reroute",
                run.id,
                "--driver",
                "claude-code",
                "--reason",
                "Use Claude Code for broader synthesis",
            ],
        )

        metadata = load_run(temp_hive_dir, run.id)
        run_root = Path(temp_hive_dir) / ".hive" / "runs" / run.id
        handles = json.loads((run_root / "driver" / "handles.json").read_text(encoding="utf-8"))
        driver_history = [entry["driver"] for entry in handles["history"]]
        event_types = [
            json.loads(line)["type"]
            for line in (run_root / "events.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

        assert metadata["driver"] == "claude-code"
        assert metadata["status"] == "awaiting_input"
        assert handles["active"]["driver"] == "claude-code"
        assert driver_history, "expected non-empty driver history"
        assert driver_history[0] == "local"
        assert "codex" in driver_history
        assert driver_history[-1] == "claude-code"
        assert (run_root / "transcript" / "normalized.jsonl").exists()
        assert event_types.count("steering.reroute_requested") == 2
        assert event_types.count("steering.rerouted") == 2

    def test_cli_steer_pause_resume_and_cancel_update_run_timeline(self, temp_hive_dir, capsys):
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
        subprocess.run(["git", "add", "-A"], cwd=temp_hive_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Bootstrap workspace"],
            cwd=temp_hive_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
        run = start_run(temp_hive_dir, task_id, driver_name="local")

        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "steer", "pause", run.id, "--reason", "Wait"],
        )
        paused = load_run(temp_hive_dir, run.id)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "steer", "resume", run.id, "--reason", "Go"],
        )
        resumed = load_run(temp_hive_dir, run.id)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "steer", "cancel", run.id, "--reason", "Stop"],
        )
        cancelled = load_run(temp_hive_dir, run.id)
        task = ready_tasks(temp_hive_dir, project_id="demo")[0]
        timeline = (
            Path(temp_hive_dir) / ".hive" / "runs" / run.id / "events.jsonl"
        ).read_text(encoding="utf-8")

        assert paused["health"] == "paused"
        assert resumed["health"] == "healthy"
        assert cancelled["status"] == "cancelled"
        assert task["id"] == run.task_id
        assert "steering.pause" in timeline
        assert "steering.resume" in timeline
        assert "steering.cancel" in timeline
        assert "run.cancelled" in timeline

    def test_launch_request_records_actual_base_branch(self, temp_hive_dir, capsys):
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
        subprocess.run(["git", "add", "-A"], cwd=temp_hive_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Bootstrap workspace"],
            cwd=temp_hive_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(["git", "branch", "-m", "release/demo"], cwd=temp_hive_dir, check=True)

        task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
        run = start_run(temp_hive_dir, task_id, driver_name="codex")
        launch = json.loads(
            (Path(temp_hive_dir) / ".hive" / "runs" / run.id / "launch.json").read_text(
                encoding="utf-8"
            )
        )

        assert launch["workspace"]["base_branch"] == "release/demo"

    def test_reroute_launch_request_preserves_recorded_base_branch(self, temp_hive_dir, capsys):
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
        subprocess.run(["git", "add", "-A"], cwd=temp_hive_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Bootstrap workspace"],
            cwd=temp_hive_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(["git", "branch", "-m", "release/demo"], cwd=temp_hive_dir, check=True)

        task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
        run = start_run(temp_hive_dir, task_id, driver_name="local")
        metadata = load_run(temp_hive_dir, run.id)
        request = _build_reroute_launch_request(
            Path(temp_hive_dir),
            metadata,
            driver_name="codex",
        )

        assert request.workspace.base_branch == "release/demo"

    def test_reroute_launch_request_handles_null_metadata_json(self, temp_hive_dir, capsys):
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
        subprocess.run(["git", "add", "-A"], cwd=temp_hive_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Bootstrap workspace"],
            cwd=temp_hive_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(["git", "branch", "-m", "release/demo"], cwd=temp_hive_dir, check=True)

        task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
        run = start_run(temp_hive_dir, task_id, driver_name="local")
        metadata = load_run(temp_hive_dir, run.id)
        metadata["metadata_json"] = None

        request = _build_reroute_launch_request(
            Path(temp_hive_dir),
            metadata,
            driver_name="codex",
        )

        assert request.workspace.base_branch == "release/demo"
        assert request.metadata["task_title"] == run.task_id

    def test_reroute_launch_request_materializes_explicit_handoff_bundle(
        self, temp_hive_dir, capsys
    ):
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
        subprocess.run(["git", "add", "-A"], cwd=temp_hive_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Bootstrap workspace"],
            cwd=temp_hive_dir,
            check=True,
            capture_output=True,
            text=True,
        )

        task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
        run = start_run(temp_hive_dir, task_id, driver_name="local")
        request_approval(
            temp_hive_dir,
            run.id,
            kind="command",
            title="Approve network access",
            summary="Codex requested network access.",
            requested_by="codex",
        )
        metadata = load_run(temp_hive_dir, run.id)
        request = _build_reroute_launch_request(
            Path(temp_hive_dir),
            metadata,
            driver_name="codex",
        )
        bundle_path = Path(str(request.metadata["reroute_bundle_path"]))
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

        assert bundle_path.exists()
        assert request.metadata["reroute_summary_path"]
        assert bundle["source_driver"] == "local"
        assert bundle["target_driver"] == "codex"
        assert bundle["artifacts"]["transcript"] == metadata["transcript_path"]
        assert bundle["pending_approvals"]
        assert request.metadata["reroute_bundle"]["run_id"] == run.id

    def test_start_run_compiles_dependency_handoff_artifacts(self, temp_hive_dir, capsys):
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
        dependency_task = create_task(
            temp_hive_dir,
            "demo",
            "Dependency task",
            status="ready",
            priority=1,
            summary_md="Land the prerequisite slice.",
        )
        follow_up_task = create_task(
            temp_hive_dir,
            "demo",
            "Follow-up task",
            status="ready",
            priority=1,
            summary_md="Consume the prerequisite artifact handoff.",
        )
        subprocess.run(["git", "add", "-A"], cwd=temp_hive_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Bootstrap workspace"],
            cwd=temp_hive_dir,
            check=True,
            capture_output=True,
            text=True,
        )

        dependency_task_id = dependency_task.id
        follow_up_task_id = follow_up_task.id
        dependency_run = start_run(temp_hive_dir, dependency_task_id, driver_name="local")
        eval_run(temp_hive_dir, dependency_run.id)
        accept_run(temp_hive_dir, dependency_run.id)
        update_task(
            temp_hive_dir,
            dependency_task_id,
            {
                "edges": {
                    **dependency_task.edges,
                    "blocks": [follow_up_task_id],
                }
            },
        )

        run = start_run(temp_hive_dir, follow_up_task_id, driver_name="codex")
        metadata = load_run(temp_hive_dir, run.id)
        handoff_path = Path(str(metadata["handoff_manifest_path"]))
        handoffs = json.loads(handoff_path.read_text(encoding="utf-8"))
        launch = json.loads(
            (Path(temp_hive_dir) / ".hive" / "runs" / run.id / "launch.json").read_text(
                encoding="utf-8"
            )
        )

        assert handoff_path.exists()
        assert handoffs["runs"][0]["run_id"] == dependency_run.id
        assert handoffs["runs"][0]["task_id"] == dependency_task_id
        assert launch["metadata"]["handoff_manifest_path"] == str(handoff_path)

    def test_workspace_refresh_keeps_legacy_patch_inside_run_directory(
        self, temp_hive_dir, capsys
    ):
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
        subprocess.run(["git", "add", "-A"], cwd=temp_hive_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Bootstrap workspace"],
            cwd=temp_hive_dir,
            check=True,
            capture_output=True,
            text=True,
        )

        task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
        run = start_run(temp_hive_dir, task_id, driver_name="local")
        metadata = load_run(temp_hive_dir, run.id)
        run_root = Path(temp_hive_dir) / ".hive" / "runs" / run.id
        legacy_patch = run_root / "patch.diff"
        shared_patch = run_root.parent / "patch.diff"
        worktree_docs = Path(metadata["worktree_path"]) / "docs"
        worktree_docs.mkdir(parents=True, exist_ok=True)
        (worktree_docs / "legacy-note.md").write_text(
            "# Legacy patch note\n",
            encoding="utf-8",
        )
        metadata["patch_path"] = str(legacy_patch)

        _refresh_workspace_state(Path(temp_hive_dir), metadata)

        assert legacy_patch.exists()
        assert "legacy-note.md" in legacy_patch.read_text(encoding="utf-8")
        assert not shared_patch.exists()

"""Codex harness driver."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import time
from typing import Any

from src.hive.drivers.base import HarnessDriver
from src.hive.drivers.types import (
    DriverInfo,
    RunBudgetUsage,
    RunHandle,
    RunLaunchRequest,
    RunProgress,
    RunStatus,
)
from src.hive.runtime.capabilities import capability_surface
from src.hive.clock import utc_now_iso


class CodexDriver(HarnessDriver):
    """Driver that stages runs for Codex."""

    name = "codex"
    binary_names = ("codex",)
    display_name = "Codex"
    cli_label = "Codex CLI"
    declared_launch_mode = "app_server"
    declared_session_persistence = "thread"
    declared_event_stream = "structured_deltas"
    declared_approvals = ("command", "file")
    declared_skills = "explicit_invoke"
    declared_subagents = "native"
    declared_native_sandbox = "policy"
    declared_artifacts = ("diff", "transcript", "plan")
    declared_reroute_export = "transcript_plus_context"

    def _live_exec_enabled(self) -> bool:
        raw = os.environ.get("HIVE_CODEX_LIVE_EXEC")
        if raw is None:
            return False
        return raw.strip().lower() in {"1", "true", "yes", "on"}

    def _live_app_server_enabled(self) -> bool:
        raw = os.environ.get("HIVE_CODEX_LIVE_APP_SERVER")
        if raw is None:
            return False
        return raw.strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _pid_is_running(pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True

    @staticmethod
    def _read_exit_code(path_value: str | None) -> int | None:
        if not path_value:
            return None
        path = Path(path_value)
        if not path.exists():
            return None
        try:
            return int(path.read_text(encoding="utf-8").strip() or "0")
        except ValueError:
            return None

    @staticmethod
    def _load_state(path_value: str | None) -> dict[str, Any]:
        if not path_value:
            return {}
        path = Path(path_value)
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _event_cursor(path_value: str | None) -> str | None:
        if not path_value:
            return None
        path = Path(path_value)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as handle:
            line_count = sum(1 for line in handle if line.strip())
        return str(line_count)

    @staticmethod
    def _last_event_timestamp(*paths: str | None) -> str | None:
        candidates = [Path(path) for path in paths if path and Path(path).exists()]
        if not candidates:
            return None
        latest = max(candidate.stat().st_mtime for candidate in candidates)
        return datetime.fromtimestamp(latest, tz=timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _wait_for_startup_artifact(
        path: Path,
        *,
        process: subprocess.Popen[str],
        timeout_seconds: float = 1.0,
        poll_seconds: float = 0.05,
    ) -> bool:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if path.exists():
                return True
            if process.poll() is not None:
                return False
            time.sleep(poll_seconds)
        return path.exists()

    @staticmethod
    def _terminate_process(process: subprocess.Popen[str]) -> None:
        if process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)

    @staticmethod
    def _budget_usage_from_state(state: dict[str, Any]) -> RunBudgetUsage:
        token_usage = state.get("token_usage")
        if not isinstance(token_usage, dict):
            return RunBudgetUsage()
        total = token_usage.get("total")
        if not isinstance(total, dict):
            return RunBudgetUsage()
        return RunBudgetUsage(
            spent_tokens=int(total.get("totalTokens") or 0),
            spent_cost_usd=0.0,
            wall_minutes=0,
        )

    def _build_exec_prompt(self, request: RunLaunchRequest) -> str:
        run_brief_path = Path(request.artifacts_path) / "context" / "compiled" / "run-brief.md"
        run_brief = run_brief_path.read_text(encoding="utf-8")
        return "\n\n".join(
            [
                "You are Codex running inside a governed Hive v2.3 run.",
                "Read the run brief below, follow the recorded PROGRAM.md policy, make the "
                "needed repository changes inside the current worktree, and finish with a concise "
                "summary of what changed and any remaining risks.",
                run_brief.strip(),
            ]
        )

    def _launch_live_app_server(self, request: RunLaunchRequest) -> RunHandle | None:
        binary_name, binary_path = self._detected_binary_details()
        if not self._live_app_server_enabled() or not binary_path:
            return None

        help_text = self._command_output("--help") or ""
        app_server_help = self._command_output("app-server", "--help") or ""
        if "app-server" not in help_text or "--listen" not in app_server_help:
            return None

        run_root = Path(request.artifacts_path)
        raw_output_path = run_root / "transcript" / "raw" / "codex-app-server-events.jsonl"
        last_message_path = run_root / "transcript" / "raw" / "codex-app-server-last-message.txt"
        exit_code_path = run_root / "driver" / "codex-app-server-exit.txt"
        state_path = run_root / "driver" / "codex-app-server-state.json"
        prompt_path = run_root / "driver" / "codex-app-server-prompt.txt"
        command_path = run_root / "driver" / "codex-app-server-command.txt"
        stderr_path = run_root / "logs" / "stderr.txt"
        worker_stderr_path = run_root / "logs" / "codex-app-server-worker-stderr.txt"
        raw_output_path.parent.mkdir(parents=True, exist_ok=True)
        worker_stderr_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            prompt = self._build_exec_prompt(request)
        except OSError as exc:
            return RunHandle(
                run_id=request.run_id,
                driver=self.name,
                driver_handle=f"{self.name}:app-server:{request.run_id}",
                status="failed",
                launched_at=utc_now_iso(),
                launch_mode="app_server",
                transport="stdio-jsonrpc",
                metadata={"launch_error": str(exc)},
            )

        prompt_path.write_text(prompt, encoding="utf-8")
        worker_path = Path(__file__).with_name("codex_app_server_worker.py")
        command = [
            sys.executable,
            str(worker_path),
            "--binary",
            binary_path,
            "--worktree",
            request.workspace.worktree_path,
            "--prompt",
            str(prompt_path),
            "--raw-output",
            str(raw_output_path),
            "--last-message",
            str(last_message_path),
            "--exit-code",
            str(exit_code_path),
            "--stderr",
            str(stderr_path),
            "--approval-channel",
            str(request.metadata.get("approval_channel") or ""),
            "--state",
            str(state_path),
        ]
        if request.model:
            command.extend(["--model", request.model])
        command_path.write_text(" ".join(shlex.quote(part) for part in command), encoding="utf-8")
        try:
            with open(worker_stderr_path, "a", encoding="utf-8") as worker_stderr_handle:
                process = subprocess.Popen(
                    command,
                    cwd=request.workspace.worktree_path,
                    stdout=subprocess.DEVNULL,
                    stderr=worker_stderr_handle,
                    text=True,
                    start_new_session=True,
                )
        except OSError as exc:
            return RunHandle(
                run_id=request.run_id,
                driver=self.name,
                driver_handle=f"{self.name}:app-server:{request.run_id}",
                status="failed",
                launched_at=utc_now_iso(),
                launch_mode="app_server",
                transport="stdio-jsonrpc",
                metadata={"launch_error": str(exc)},
            )
        if not self._wait_for_startup_artifact(state_path, process=process):
            launch_error = "Codex app-server broker did not initialize its state file."
            if process.poll() is not None:
                launch_error = (
                    "Codex app-server broker exited before initializing its state file."
                )
            self._terminate_process(process)
            return RunHandle(
                run_id=request.run_id,
                driver=self.name,
                driver_handle=f"{self.name}:app-server:{request.run_id}",
                status="failed",
                launched_at=utc_now_iso(),
                launch_mode="app_server",
                transport="stdio-jsonrpc",
                metadata={
                    "launch_error": launch_error,
                    "binary_name": binary_name,
                    "binary_path": binary_path,
                    "worker_stderr_path": str(worker_stderr_path),
                    "stderr_path": str(stderr_path),
                    "raw_output_path": str(raw_output_path),
                    "last_message_path": str(last_message_path),
                    "exit_code_path": str(exit_code_path),
                    "state_path": str(state_path),
                    "prompt_path": str(prompt_path),
                    "command_path": str(command_path),
                },
            )
        return RunHandle(
            run_id=request.run_id,
            driver=self.name,
            driver_handle=f"{self.name}:app-server:{process.pid}",
            status="running",
            launched_at=utc_now_iso(),
            launch_mode="app_server",
            transport="stdio-jsonrpc",
            session_id=str(process.pid),
            event_cursor="0",
            approval_channel=str(request.metadata.get("approval_channel") or "") or None,
            metadata={
                "binary_name": binary_name,
                "binary_path": binary_path,
                "pid": process.pid,
                "worker_stderr_path": str(worker_stderr_path),
                "stderr_path": str(stderr_path),
                "raw_output_path": str(raw_output_path),
                "last_message_path": str(last_message_path),
                "exit_code_path": str(exit_code_path),
                "state_path": str(state_path),
                "prompt_path": str(prompt_path),
                "command_path": str(command_path),
            },
        )

    @staticmethod
    def _supports_exec_flag(exec_help: str, flag: str) -> bool:
        return flag in exec_help

    def _build_live_exec_command(
        self,
        *,
        binary_path: str,
        request: RunLaunchRequest,
        exec_help: str,
        last_message_path: Path,
    ) -> list[str]:
        command = [
            binary_path,
            "exec",
            "-",
            "--json",
            "--skip-git-repo-check",
        ]
        if self._supports_exec_flag(exec_help, "--ephemeral"):
            command.append("--ephemeral")
        if self._supports_exec_flag(exec_help, "--ask-for-approval"):
            command.extend(["--sandbox", "workspace-write", "--ask-for-approval", "never"])
        else:
            command.extend(["-c", 'approval_policy="never"'])
            if self._supports_exec_flag(exec_help, "--sandbox"):
                command.extend(["--sandbox", "workspace-write"])
            else:
                command.extend(["-c", 'sandbox_mode="workspace-write"'])
        if self._supports_exec_flag(exec_help, "--output-last-message"):
            command.extend(["--output-last-message", str(last_message_path)])
        if self._supports_exec_flag(exec_help, "--cd"):
            command.extend(["--cd", request.workspace.worktree_path])
        if request.model:
            command.extend(["--model", request.model])
        return command

    def _launch_live_exec(self, request: RunLaunchRequest) -> RunHandle | None:
        binary_name, binary_path = self._detected_binary_details()
        if not self._live_exec_enabled() or not binary_path:
            return None

        help_text = self._command_output("--help") or ""
        if "exec" not in help_text:
            return None
        exec_help = self._command_output("exec", "--help") or ""

        run_root = Path(request.artifacts_path)
        raw_output_path = run_root / "transcript" / "raw" / "codex-exec-events.jsonl"
        last_message_path = run_root / "transcript" / "raw" / "codex-last-message.txt"
        exit_code_path = run_root / "driver" / "codex-exec-exit.txt"
        command_path = run_root / "driver" / "codex-exec-command.txt"
        stderr_path = run_root / "logs" / "stderr.txt"
        raw_output_path.parent.mkdir(parents=True, exist_ok=True)

        command = self._build_live_exec_command(
            binary_path=binary_path,
            request=request,
            exec_help=exec_help,
            last_message_path=last_message_path,
        )

        command_path.write_text(" ".join(shlex.quote(part) for part in command), encoding="utf-8")
        shell_command = (
            f"{command_path.read_text(encoding='utf-8')} "
            f"> {shlex.quote(str(raw_output_path))} "
            f"2> {shlex.quote(str(stderr_path))}; "
            f"status=$?; printf '%s\\n' \"$status\" > {shlex.quote(str(exit_code_path))}"
        )
        try:
            prompt = self._build_exec_prompt(request)
        except OSError as exc:
            return RunHandle(
                run_id=request.run_id,
                driver=self.name,
                driver_handle=f"{self.name}:exec:{request.run_id}",
                status="failed",
                launched_at=utc_now_iso(),
                launch_mode="exec",
                transport="subprocess",
                metadata={"launch_error": str(exc)},
            )
        try:
            process = subprocess.Popen(
                ["/bin/sh", "-lc", shell_command],
                cwd=request.workspace.worktree_path,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
                start_new_session=True,
            )
        except OSError as exc:
            return RunHandle(
                run_id=request.run_id,
                driver=self.name,
                driver_handle=f"{self.name}:exec:{request.run_id}",
                status="failed",
                launched_at=utc_now_iso(),
                launch_mode="exec",
                transport="subprocess",
                metadata={"launch_error": str(exc)},
            )
        assert process.stdin is not None
        process.stdin.write(prompt)
        process.stdin.close()
        return RunHandle(
            run_id=request.run_id,
            driver=self.name,
            driver_handle=f"{self.name}:exec:{process.pid}",
            status="running",
            launched_at=utc_now_iso(),
            launch_mode="exec",
            transport="subprocess",
            session_id=str(process.pid),
            event_cursor="0",
            approval_channel=str(request.metadata.get("approval_channel") or "") or None,
            metadata={
                "binary_name": binary_name,
                "binary_path": binary_path,
                "pid": process.pid,
                "raw_output_path": str(raw_output_path),
                "last_message_path": str(last_message_path),
                "exit_code_path": str(exit_code_path),
                "command_path": str(command_path),
            },
        )

    def _probe_details(
        self,
        *,
        binary_name: str | None,
        binary_path: str | None,
    ) -> tuple[dict[str, Any], list[str], dict[str, str]]:
        if not binary_path:
            return {}, [], {}

        help_text = self._command_output("--help") or ""
        exec_help = self._command_output("exec", "--help") or ""
        app_server_help = self._command_output("app-server", "--help") or ""
        probed = {
            "binary_name": binary_name,
            "exec_available": "exec" in help_text,
            "app_server_available": "app-server" in help_text,
            "sandbox_cli_available": "sandbox" in help_text,
            "features_cli_available": "features" in help_text,
            "exec_approval_flag": "--ask-for-approval" in exec_help,
            "exec_json_output": "--json" in exec_help,
            "exec_output_schema": "--output-schema" in exec_help,
            "exec_output_last_message": "--output-last-message" in exec_help,
            "app_server_listen": "--listen" in app_server_help,
        }
        notes = []
        if probed["exec_available"]:
            notes.append("Codex CLI exposes `exec`, so batch fallback can be probed truthfully.")
        if not probed["exec_approval_flag"]:
            notes.append(
                "Codex CLI does not expose `--ask-for-approval`; Hive falls back to config "
                "overrides for non-interactive exec launches."
            )
        if probed["app_server_available"]:
            notes.append(
                "Codex CLI exposes `app-server`, but Hive still stages runs until the protocol "
                "adapter is implemented."
            )
        evidence = {
            "codex_exec": (
                "Codex CLI help exposes `exec` with structured output flags."
                if probed["exec_available"]
                else "Codex CLI help did not expose `exec` on this machine."
            ),
            "codex_app_server": (
                "Codex CLI help exposes `app-server`; the effective mode stays staged until Hive "
                "speaks that protocol."
                if probed["app_server_available"]
                else "Codex CLI help did not expose `app-server` on this machine."
            ),
        }
        return probed, notes, evidence

    def probe(self) -> DriverInfo:
        info = super().probe()
        snapshot = info.capability_snapshot
        if snapshot is None:
            return info
        if self._live_app_server_enabled() and snapshot.probed.get("app_server_available"):
            snapshot.effective = capability_surface(
                launch_mode="app_server",
                session_persistence="thread",
                event_stream="structured_deltas",
                approvals=["command", "file"],
                skills="file_projection",
                worktrees="host_managed",
                subagents="none",
                native_sandbox="policy",
                outer_sandbox_required=True,
                artifacts=["runpack", "transcript", "plan", "diff"],
                reroute_export="transcript",
            )
            snapshot.confidence["effective"] = "verified"
            snapshot.evidence["effective"] = (
                "Codex app-server mode is enabled, so Hive can launch a real interactive "
                "Codex session over stdio JSON-RPC."
            )
            info.capabilities.resume = False
            info.capabilities.interrupt = ["cancel"]
            info.capabilities.reroute_export = "transcript"
            info.notes.append(
                "Codex app-server mode is enabled; Hive can launch a live interactive Codex run."
            )
        elif self._live_exec_enabled() and snapshot.probed.get("exec_available"):
            snapshot.effective = capability_surface(
                launch_mode="exec",
                session_persistence="ephemeral",
                event_stream="status",
                approvals=[],
                skills="file_projection",
                worktrees="host_managed",
                subagents="none",
                native_sandbox="policy",
                outer_sandbox_required=True,
                artifacts=["runpack", "transcript", "plan", "diff"],
                reroute_export="transcript",
            )
            snapshot.confidence["effective"] = "verified"
            snapshot.evidence["effective"] = (
                "Codex live exec mode is enabled, so Hive can launch a real non-interactive "
                "Codex session instead of staging the runpack."
            )
            info.capabilities.resume = False
            info.capabilities.interrupt = ["pause", "resume", "cancel"]
            info.capabilities.reroute_export = "transcript"
            info.notes.append(
                "Codex live exec is enabled; Hive can launch a real non-interactive Codex run."
            )
        return info

    def launch(self, request: RunLaunchRequest) -> RunHandle:
        app_server_handle = self._launch_live_app_server(request)
        if app_server_handle is not None:
            return app_server_handle
        live_handle = self._launch_live_exec(request)
        if live_handle is not None:
            return live_handle
        return super().launch(request)

    def status(self, handle: RunHandle) -> RunStatus:
        if handle.launch_mode == "app_server":
            raw_output_path = str(handle.metadata.get("raw_output_path") or "")
            last_message_path = str(handle.metadata.get("last_message_path") or "")
            exit_code_path = str(handle.metadata.get("exit_code_path") or "")
            state_path = str(handle.metadata.get("state_path") or "")
            stderr_path = str(handle.metadata.get("stderr_path") or "")
            worker_stderr_path = str(handle.metadata.get("worker_stderr_path") or "")
            pid = int(handle.metadata.get("pid") or 0)
            exit_code = self._read_exit_code(exit_code_path)
            state = self._load_state(state_path)
            budget = self._budget_usage_from_state(state)
            cursor = self._event_cursor(raw_output_path) or handle.event_cursor
            last_event_at = self._last_event_timestamp(
                raw_output_path,
                last_message_path,
                state_path,
                exit_code_path,
                stderr_path,
                worker_stderr_path,
            )
            turn_status = str(state.get("turn_status") or "")
            thread_status = str(state.get("thread_status") or "")
            session = {
                "launch_mode": "app_server",
                "transport": "stdio-jsonrpc",
                "session_id": handle.session_id,
                "thread_id": state.get("thread_id"),
                "turn_id": state.get("turn_id"),
                "pid": pid or None,
            }
            artifacts = {
                "raw_output_path": raw_output_path or None,
                "last_message_path": last_message_path or None,
                "exit_code_path": exit_code_path or None,
                "state_path": state_path or None,
                "stderr_path": stderr_path or None,
                "worker_stderr_path": worker_stderr_path or None,
            }
            if state_path and not Path(state_path).exists():
                return RunStatus(
                    run_id=handle.run_id,
                    state="failed",
                    health="failed",
                    driver=self.name,
                    progress=RunProgress(
                        phase="failed",
                        message=(
                            "Codex app-server broker never initialized its startup state; "
                            "check the captured worker stderr."
                        ),
                        percent=100,
                    ),
                    waiting_on="operator",
                    last_event_at=last_event_at or handle.launched_at,
                    budget=budget,
                    event_cursor=cursor,
                    session=session,
                    artifacts=artifacts,
                )
            if exit_code is None:
                if pid and self._pid_is_running(pid):
                    message = "Codex app-server is actively working in the Hive run worktree."
                    phase = "implementing"
                    percent = 20
                    if thread_status == "idle" and turn_status == "inProgress":
                        message = "Codex app-server is wrapping up the current turn."
                    elif turn_status == "completed":
                        message = (
                            "Codex app-server finished the turn and is draining final events "
                            "before Hive marks the run complete."
                        )
                        phase = "finalizing"
                        percent = 95
                    elif turn_status in {"cancelled", "interrupted"}:
                        message = (
                            "Codex app-server acknowledged the interrupt and is finalizing "
                            "shutdown artifacts."
                        )
                        phase = "cancelling"
                        percent = 95
                    return RunStatus(
                        run_id=handle.run_id,
                        state="running",
                        health="healthy",
                        driver=self.name,
                        progress=RunProgress(
                            phase=phase,
                            message=message,
                            percent=percent,
                        ),
                        waiting_on=None,
                        last_event_at=last_event_at or handle.launched_at,
                        budget=budget,
                        event_cursor=cursor,
                        session=session,
                        artifacts=artifacts,
                    )
                if turn_status == "completed":
                    return RunStatus(
                        run_id=handle.run_id,
                        state="completed_candidate",
                        health="needs_attention",
                        driver=self.name,
                        progress=RunProgress(
                            phase="completed",
                            message=(
                                "Codex app-server recorded a completed turn, but the bridge "
                                "stopped before writing an exit marker."
                            ),
                            percent=100,
                        ),
                        waiting_on="review",
                        last_event_at=last_event_at or handle.launched_at,
                        budget=budget,
                        event_cursor=cursor,
                        session=session,
                        artifacts=artifacts,
                    )
                if turn_status in {"cancelled", "interrupted"}:
                    return RunStatus(
                        run_id=handle.run_id,
                        state="cancelled",
                        health="needs_attention",
                        driver=self.name,
                        progress=RunProgress(
                            phase="cancelled",
                            message=(
                                "Codex app-server recorded an interrupted turn, but the bridge "
                                "stopped before writing an exit marker."
                            ),
                            percent=100,
                        ),
                        waiting_on="operator",
                        last_event_at=last_event_at or handle.launched_at,
                        budget=budget,
                        event_cursor=cursor,
                        session=session,
                        artifacts=artifacts,
                    )
                return RunStatus(
                    run_id=handle.run_id,
                    state="failed",
                    health="failed",
                    driver=self.name,
                    progress=RunProgress(
                        phase="failed",
                        message="Codex app-server stopped without writing an exit marker.",
                        percent=100,
                    ),
                    waiting_on="operator",
                    last_event_at=last_event_at or handle.launched_at,
                    budget=budget,
                    event_cursor=cursor,
                    session=session,
                    artifacts=artifacts,
                )
            if exit_code == 0:
                state_name = "completed_candidate"
                health = "healthy"
                waiting_on = "review"
                progress = RunProgress(
                    phase="completed",
                    message="Codex app-server finished and produced a candidate result for review.",
                    percent=100,
                )
                if turn_status in {"cancelled", "interrupted"}:
                    state_name = "cancelled"
                    health = "needs_attention"
                    waiting_on = "operator"
                    progress = RunProgress(
                        phase="cancelled",
                        message="Codex app-server turn was interrupted by Hive.",
                        percent=100,
                    )
                return RunStatus(
                    run_id=handle.run_id,
                    state=state_name,
                    health=health,
                    driver=self.name,
                    progress=progress,
                    waiting_on=waiting_on,
                    last_event_at=last_event_at or handle.launched_at,
                    budget=budget,
                    event_cursor=cursor,
                    session=session,
                    artifacts=artifacts,
                )
            return RunStatus(
                run_id=handle.run_id,
                state="failed",
                health="failed",
                driver=self.name,
                progress=RunProgress(
                    phase="failed",
                    message=f"Codex app-server bridge exited with status {exit_code}.",
                    percent=100,
                ),
                waiting_on="operator",
                last_event_at=last_event_at or handle.launched_at,
                budget=budget,
                event_cursor=cursor,
                session=session,
                artifacts=artifacts,
            )
        if handle.launch_mode != "exec":
            return super().status(handle)

        raw_output_path = str(handle.metadata.get("raw_output_path") or "")
        last_message_path = str(handle.metadata.get("last_message_path") or "")
        exit_code_path = str(handle.metadata.get("exit_code_path") or "")
        pid = int(handle.metadata.get("pid") or 0)
        exit_code = self._read_exit_code(exit_code_path)
        cursor = self._event_cursor(raw_output_path) or handle.event_cursor
        last_event_at = self._last_event_timestamp(
            raw_output_path,
            last_message_path,
            exit_code_path,
        )
        session = {
            "launch_mode": "exec",
            "transport": "subprocess",
            "session_id": handle.session_id,
            "pid": pid or None,
        }
        artifacts = {
            "raw_output_path": raw_output_path or None,
            "last_message_path": last_message_path or None,
            "exit_code_path": exit_code_path or None,
        }
        if exit_code is None:
            if pid and self._pid_is_running(pid):
                return RunStatus(
                    run_id=handle.run_id,
                    state="running",
                    health="healthy",
                    driver=self.name,
                    progress=RunProgress(
                        phase="implementing",
                        message="Codex exec is actively working in the Hive run worktree.",
                        percent=20,
                    ),
                    waiting_on=None,
                    last_event_at=last_event_at or handle.launched_at,
                    event_cursor=cursor,
                    session=session,
                    artifacts=artifacts,
                )
            return RunStatus(
                run_id=handle.run_id,
                state="failed",
                health="failed",
                driver=self.name,
                progress=RunProgress(
                    phase="failed",
                    message="Codex exec stopped without writing an exit marker.",
                    percent=100,
                ),
                waiting_on="operator",
                last_event_at=last_event_at or handle.launched_at,
                event_cursor=cursor,
                session=session,
                artifacts=artifacts,
            )
        if exit_code == 0:
            return RunStatus(
                run_id=handle.run_id,
                state="completed_candidate",
                health="healthy",
                driver=self.name,
                progress=RunProgress(
                    phase="completed",
                    message="Codex exec finished and produced a candidate result for review.",
                    percent=100,
                ),
                waiting_on="review",
                last_event_at=last_event_at or handle.launched_at,
                event_cursor=cursor,
                session=session,
                artifacts=artifacts,
            )
        return RunStatus(
            run_id=handle.run_id,
            state="failed",
            health="failed",
            driver=self.name,
            progress=RunProgress(
                phase="failed",
                message=f"Codex exec exited with status {exit_code}.",
                percent=100,
            ),
            waiting_on="operator",
            last_event_at=last_event_at or handle.launched_at,
            event_cursor=cursor,
            session=session,
            artifacts=artifacts,
        )

    def interrupt(self, handle: RunHandle, mode: str) -> dict[str, Any]:
        if handle.launch_mode == "app_server":
            if mode != "cancel":
                return super().interrupt(handle, mode)
            channel_path = str(handle.approval_channel or handle.metadata.get("approval_channel") or "")
            if not channel_path.strip():
                return {
                    "ok": False,
                    "driver": self.name,
                    "run_id": handle.run_id,
                    "mode": mode,
                    "message": "Codex app-server handle does not expose a control channel.",
                }
            target = Path(channel_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            record = {
                "ts": utc_now_iso(),
                "kind": "interrupt_request",
                "driver": self.name,
                "run_id": handle.run_id,
                "driver_handle": handle.driver_handle,
                "mode": mode,
            }
            with open(target, "a", encoding="utf-8") as handle_out:
                handle_out.write(json.dumps(record, sort_keys=True) + "\n")
            return {
                "ok": True,
                "driver": self.name,
                "run_id": handle.run_id,
                "mode": mode,
                "channel": str(target),
                "message": "Queued a Codex app-server interrupt request.",
            }
        if handle.launch_mode != "exec":
            return super().interrupt(handle, mode)
        pid = int(handle.metadata.get("pid") or 0)
        if not pid:
            return {
                "ok": False,
                "driver": self.name,
                "run_id": handle.run_id,
                "mode": mode,
                "message": "Codex exec handle does not include a live pid.",
            }
        signal_map = {
            "pause": signal.SIGSTOP,
            "resume": signal.SIGCONT,
            "cancel": signal.SIGTERM,
        }
        sig = signal_map.get(mode)
        if sig is None:
            return super().interrupt(handle, mode)
        try:
            os.killpg(os.getpgid(pid), sig)
        except OSError as exc:
            return {
                "ok": False,
                "driver": self.name,
                "run_id": handle.run_id,
                "mode": mode,
                "message": str(exc),
            }
        return {
            "ok": True,
            "driver": self.name,
            "run_id": handle.run_id,
            "mode": mode,
            "pid": pid,
            "message": f"Sent {sig.name} to Codex exec pid {pid}.",
        }

    def collect_artifacts(self, handle: RunHandle) -> dict[str, Any]:
        if handle.launch_mode == "app_server":
            return {
                "driver": self.name,
                "run_id": handle.run_id,
                "artifacts": [
                    handle.metadata.get("raw_output_path"),
                    handle.metadata.get("last_message_path"),
                    handle.metadata.get("exit_code_path"),
                    handle.metadata.get("state_path"),
                ],
            }
        if handle.launch_mode != "exec":
            return super().collect_artifacts(handle)
        return {
            "driver": self.name,
            "run_id": handle.run_id,
            "artifacts": [
                handle.metadata.get("raw_output_path"),
                handle.metadata.get("last_message_path"),
                handle.metadata.get("exit_code_path"),
            ],
        }

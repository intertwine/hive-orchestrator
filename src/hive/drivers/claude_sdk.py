"""Claude SDK-backed harness driver."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time
from typing import Any

from src.hive.clock import utc_now_iso
from src.hive.drivers.claude_code import ClaudeCodeDriver
from src.hive.drivers.types import (
    DriverInfo,
    RunBudgetUsage,
    RunHandle,
    RunLaunchRequest,
    RunProgress,
    RunStatus,
)
from src.hive.runtime.capabilities import capability_surface


def _load_claude_sdk():
    """Import the optional Claude Code SDK only when live SDK mode is selected."""
    try:
        import claude_code_sdk  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - exercised through monkeypatching
        raise ImportError(
            "Claude Code SDK is not installed. Install `mellona-hive[drivers-claude]` "
            "or `pip install claude-code-sdk` to use the live Claude SDK driver."
        ) from exc
    return claude_code_sdk


class ClaudeSDKDriver(ClaudeCodeDriver):
    """Driver that prefers the Claude Code Python SDK and falls back truthfully."""

    @staticmethod
    def _load_sdk():
        return _load_claude_sdk()

    def _live_sdk_enabled(self) -> bool:
        raw = os.environ.get("HIVE_CLAUDE_LIVE_SDK")
        if raw is None:
            return False
        return raw.strip().lower() in {"1", "true", "yes", "on"}

    def _sdk_available(self) -> bool:
        try:
            self._load_sdk()
        except ImportError:
            return False
        return True

    @staticmethod
    def _startup_timeout_seconds() -> float:
        raw = os.environ.get("HIVE_CLAUDE_SDK_STARTUP_TIMEOUT_SECONDS")
        if raw is None:
            return 3.0
        try:
            timeout = float(raw)
        except ValueError:
            return 3.0
        return max(timeout, 0.1)

    @staticmethod
    def _wait_for_startup_artifact(
        path: Path,
        *,
        process: subprocess.Popen[str],
        timeout_seconds: float = 3.0,
        poll_seconds: float = 0.05,
    ) -> bool:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if path.exists():
                return True
            if process.poll() is not None:
                return path.exists()
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
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                return

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
    def _budget_usage_from_state(state: dict[str, Any]) -> RunBudgetUsage:
        duration_ms = int(state.get("duration_ms") or 0)
        wall_minutes = 0 if duration_ms <= 0 else max(1, (duration_ms + 59_999) // 60_000)
        usage = state.get("usage")
        if not isinstance(usage, dict):
            return RunBudgetUsage(
                spent_tokens=0,
                spent_cost_usd=float(state.get("total_cost_usd") or 0.0),
                wall_minutes=wall_minutes,
            )
        input_tokens = int(
            usage.get("input_tokens", 0)
            + usage.get("cache_creation_input_tokens", 0)
            + usage.get("cache_read_input_tokens", 0)
            + usage.get("cached_input_tokens", 0)
        )
        output_tokens = int(usage.get("output_tokens", 0) + usage.get("reasoning_output_tokens", 0))
        total_tokens = int(usage.get("total_tokens") or input_tokens + output_tokens)
        return RunBudgetUsage(
            spent_tokens=total_tokens,
            spent_cost_usd=float(state.get("total_cost_usd") or 0.0),
            wall_minutes=wall_minutes,
        )

    @staticmethod
    def _last_event_timestamp(*paths: str | None) -> str | None:
        candidates = [Path(path) for path in paths if path and Path(path).exists()]
        if not candidates:
            return None
        latest = max(candidate.stat().st_mtime for candidate in candidates)
        return datetime.fromtimestamp(latest, tz=timezone.utc).isoformat().replace("+00:00", "Z")

    def probe(self) -> DriverInfo:
        info = super().probe()
        snapshot = info.capability_snapshot
        if snapshot is None:
            return info
        sdk_available = self._sdk_available()
        snapshot.probed["python_sdk"] = sdk_available
        if self._live_sdk_enabled() and sdk_available and snapshot.probed.get("binary_present"):
            snapshot.effective = capability_surface(
                launch_mode="sdk",
                session_persistence="session",
                event_stream="status",
                approvals=["command", "file", "network"],
                skills="file_projection",
                worktrees="host_managed",
                subagents="none",
                native_sandbox="policy",
                outer_sandbox_required=True,
                artifacts=["runpack", "transcript", "plan", "review"],
                reroute_export="transcript",
            )
            snapshot.confidence["effective"] = "verified"
            snapshot.evidence["effective"] = (
                "Claude SDK mode is enabled and the Python SDK is installed, so Hive can launch "
                "a real Claude session through the SDK worker bridge."
            )
            info.capabilities.resume = False
            info.capabilities.interrupt = ["cancel"]
            info.capabilities.reroute_export = "transcript"
            info.notes.append(
                "Claude SDK mode is enabled; Hive can launch a live Claude SDK-backed run."
            )
        elif self._live_sdk_enabled() and not sdk_available:
            info.notes.append(
                "Claude SDK mode is enabled, but `claude-code-sdk` is not installed; "
                "Hive will fall back to the legacy Claude CLI paths."
            )
            snapshot.evidence["python_sdk"] = (
                "Claude SDK mode was requested, but the Python SDK import failed."
            )
        else:
            snapshot.evidence["python_sdk"] = (
                "Claude SDK mode is disabled or the SDK is not installed, so Hive stays on the "
                "legacy staged/exec Claude paths."
            )
        return info

    def _build_sdk_prompt(self, request: RunLaunchRequest) -> str:
        return self._build_exec_prompt(request)

    def _launch_live_sdk(self, request: RunLaunchRequest) -> RunHandle | None:
        binary_name, binary_path = self._detected_binary_details()
        if not self._live_sdk_enabled() or not binary_path or not self._sdk_available():
            return None

        run_root = Path(request.artifacts_path)
        raw_output_path = run_root / "transcript" / "raw" / "claude-sdk-events.jsonl"
        last_message_path = run_root / "transcript" / "raw" / "claude-sdk-last-message.txt"
        exit_code_path = run_root / "driver" / "claude-sdk-exit.txt"
        state_path = run_root / "driver" / "claude-sdk-state.json"
        prompt_path = run_root / "driver" / "claude-sdk-prompt.txt"
        policy_path = run_root / "driver" / "claude-sdk-policy.json"
        command_path = run_root / "driver" / "claude-sdk-command.txt"
        stderr_path = run_root / "logs" / "stderr.txt"
        worker_stderr_path = run_root / "logs" / "claude-sdk-worker-stderr.txt"
        raw_output_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        worker_stderr_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            prompt = self._build_sdk_prompt(request)
        except OSError as exc:
            return RunHandle(
                run_id=request.run_id,
                driver=self.name,
                driver_handle=f"{self.name}:sdk:{request.run_id}",
                status="failed",
                launched_at=utc_now_iso(),
                launch_mode="sdk",
                transport="sdk_worker",
                metadata={"launch_error": str(exc)},
            )

        prompt_path.write_text(prompt, encoding="utf-8")
        policy_path.write_text(
            json.dumps(dict(request.program_policy or {}), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        projection_path = run_root / "projections" / "CLAUDE.md"

        command = [
            sys.executable,
            "-u",
            "-m",
            "src.hive.drivers.claude_sdk_worker",
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
            "--policy",
            str(policy_path),
            "--session-id",
            request.run_id,
        ]
        if projection_path.exists():
            command.extend(["--claude-md", str(projection_path)])
        if request.model:
            command.extend(["--model", request.model])
        if request.budget.max_cost_usd > 0:
            command.extend(["--max-budget-usd", str(request.budget.max_cost_usd)])
        command_path.write_text(" ".join(shlex.quote(part) for part in command), encoding="utf-8")

        worker_stderr = worker_stderr_path.open("w", encoding="utf-8")
        try:
            process = subprocess.Popen(
                command,
                cwd=request.workspace.worktree_path,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=worker_stderr,
                text=True,
                start_new_session=True,
            )
        except OSError as exc:
            worker_stderr.close()
            return RunHandle(
                run_id=request.run_id,
                driver=self.name,
                driver_handle=f"{self.name}:sdk:{request.run_id}",
                status="failed",
                launched_at=utc_now_iso(),
                launch_mode="sdk",
                transport="sdk_worker",
                metadata={"launch_error": str(exc)},
            )
        finally:
            if not worker_stderr.closed:
                worker_stderr.close()

        if not self._wait_for_startup_artifact(
            state_path,
            process=process,
            timeout_seconds=self._startup_timeout_seconds(),
        ):
            self._terminate_process(process)
            message = worker_stderr_path.read_text(encoding="utf-8").strip()
            return RunHandle(
                run_id=request.run_id,
                driver=self.name,
                driver_handle=f"{self.name}:sdk:{process.pid}",
                status="failed",
                launched_at=utc_now_iso(),
                launch_mode="sdk",
                transport="sdk_worker",
                approval_channel=str(request.metadata.get("approval_channel") or "") or None,
                metadata={
                    "pid": process.pid,
                    "launch_error": message or "Claude SDK worker did not initialize in time.",
                    "worker_stderr_path": str(worker_stderr_path),
                },
            )

        return RunHandle(
            run_id=request.run_id,
            driver=self.name,
            driver_handle=f"{self.name}:sdk:{process.pid}",
            status="running",
            launched_at=utc_now_iso(),
            launch_mode="sdk",
            transport="sdk_worker",
            session_id=request.run_id,
            event_cursor="0",
            approval_channel=str(request.metadata.get("approval_channel") or "") or None,
            metadata={
                "binary_name": binary_name,
                "binary_path": binary_path,
                "pid": process.pid,
                "raw_output_path": str(raw_output_path),
                "last_message_path": str(last_message_path),
                "exit_code_path": str(exit_code_path),
                "state_path": str(state_path),
                "policy_path": str(policy_path),
                "command_path": str(command_path),
                "worker_stderr_path": str(worker_stderr_path),
            },
        )

    def launch(self, request: RunLaunchRequest) -> RunHandle:
        live_handle = self._launch_live_sdk(request)
        if live_handle is not None:
            return live_handle
        return super().launch(request)

    def status(self, handle: RunHandle) -> RunStatus:
        if handle.launch_mode != "sdk":
            return super().status(handle)

        raw_output_path = str(handle.metadata.get("raw_output_path") or "")
        last_message_path = str(handle.metadata.get("last_message_path") or "")
        exit_code_path = str(handle.metadata.get("exit_code_path") or "")
        state_path = str(handle.metadata.get("state_path") or "")
        worker_stderr_path = str(handle.metadata.get("worker_stderr_path") or "")
        pid = int(handle.metadata.get("pid") or 0)
        state = self._load_state(state_path)
        exit_code = self._read_exit_code(exit_code_path)
        cursor = self._event_cursor(raw_output_path) or handle.event_cursor
        last_event_at = self._last_event_timestamp(
            raw_output_path,
            last_message_path,
            state_path,
            exit_code_path,
            worker_stderr_path,
        )
        budget = self._budget_usage_from_state(state)
        worker_status = str(state.get("status") or "").strip().lower()
        pending_request = state.get("pending_request")
        pending_payload = pending_request if isinstance(pending_request, dict) else {}
        session = {
            "launch_mode": "sdk",
            "transport": "sdk_worker",
            "session_id": str(state.get("session_id") or handle.session_id or "") or None,
            "pid": pid or None,
            "worker_status": worker_status or None,
            "tool_name": str(pending_payload.get("tool_name") or "") or None,
        }
        artifacts = {
            "raw_output_path": raw_output_path or None,
            "last_message_path": last_message_path or None,
            "exit_code_path": exit_code_path or None,
            "state_path": state_path or None,
            "worker_stderr_path": worker_stderr_path or None,
        }
        if exit_code is None:
            if worker_status == "waiting_approval":
                tool_name = str(pending_payload.get("tool_name") or "tool")
                return RunStatus(
                    run_id=handle.run_id,
                    state="running",
                    health="blocked",
                    driver=self.name,
                    progress=RunProgress(
                        phase="waiting",
                        message=f"Claude is waiting for approval to use {tool_name}.",
                        percent=15,
                    ),
                    waiting_on="approval",
                    last_event_at=last_event_at or handle.launched_at,
                    budget=budget,
                    event_cursor=cursor,
                    session=session,
                    artifacts=artifacts,
                )
            if pid and self._pid_is_running(pid):
                return RunStatus(
                    run_id=handle.run_id,
                    state="running",
                    health="healthy",
                    driver=self.name,
                    progress=RunProgress(
                        phase="implementing",
                        message="Claude SDK is actively working in the Hive run worktree.",
                        percent=20,
                    ),
                    waiting_on=None,
                    last_event_at=last_event_at or handle.launched_at,
                    budget=budget,
                    event_cursor=cursor,
                    session=session,
                    artifacts=artifacts,
                )
            if worker_status in {"completed", "cancelled"}:
                terminal_state = (
                    "cancelled" if worker_status == "cancelled" else "completed_candidate"
                )
                return RunStatus(
                    run_id=handle.run_id,
                    state=terminal_state,
                    health=(
                        "needs_attention"
                        if terminal_state == "completed_candidate"
                        else "cancelled"
                    ),
                    driver=self.name,
                    progress=RunProgress(
                        phase=(
                            "completed" if terminal_state == "completed_candidate" else "cancelled"
                        ),
                        message=(
                            "Claude SDK worker finished before writing an exit marker."
                            if terminal_state == "completed_candidate"
                            else "Claude SDK worker acknowledged cancellation."
                        ),
                        percent=100,
                    ),
                    waiting_on="review" if terminal_state == "completed_candidate" else None,
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
                    message="Claude SDK worker stopped without writing an exit marker.",
                    percent=100,
                ),
                waiting_on="operator",
                last_event_at=last_event_at or handle.launched_at,
                budget=budget,
                event_cursor=cursor,
                session=session,
                artifacts=artifacts,
            )
        if worker_status == "cancelled":
            return RunStatus(
                run_id=handle.run_id,
                state="cancelled",
                health="cancelled",
                driver=self.name,
                progress=RunProgress(
                    phase="cancelled",
                    message="Claude SDK worker stopped after a cancellation request.",
                    percent=100,
                ),
                waiting_on=None,
                last_event_at=last_event_at or handle.launched_at,
                budget=budget,
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
                    message="Claude SDK finished and produced a candidate result for review.",
                    percent=100,
                ),
                waiting_on="review",
                last_event_at=last_event_at or handle.launched_at,
                budget=budget,
                event_cursor=cursor,
                session=session,
                artifacts=artifacts,
            )
        error_message = str(state.get("error") or "").strip()
        return RunStatus(
            run_id=handle.run_id,
            state="failed",
            health="failed",
            driver=self.name,
            progress=RunProgress(
                phase="failed",
                message=error_message or f"Claude SDK worker exited with status {exit_code}.",
                percent=100,
            ),
            waiting_on="operator",
            last_event_at=last_event_at or handle.launched_at,
            budget=budget,
            event_cursor=cursor,
            session=session,
            artifacts=artifacts,
        )

    def interrupt(self, handle: RunHandle, mode: str) -> dict[str, Any]:
        if handle.launch_mode != "sdk" or mode != "cancel":
            return super().interrupt(handle, mode)
        channel_path = str(handle.approval_channel or handle.metadata.get("approval_channel") or "")
        if not channel_path.strip():
            return {
                "ok": False,
                "driver": self.name,
                "run_id": handle.run_id,
                "mode": mode,
                "message": "Claude SDK handle does not expose a control channel.",
            }
        record = {
            "ts": utc_now_iso(),
            "kind": "interrupt",
            "driver": self.name,
            "run_id": handle.run_id,
            "driver_handle": handle.driver_handle,
            "mode": mode,
        }
        target = Path(channel_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "a", encoding="utf-8") as handle_out:
            handle_out.write(json.dumps(record, sort_keys=True) + "\n")
        return {
            "ok": True,
            "driver": self.name,
            "run_id": handle.run_id,
            "mode": mode,
            "channel": str(target),
            "message": "Forwarded a cancellation request to the Claude SDK worker.",
        }

    def collect_artifacts(self, handle: RunHandle) -> dict[str, Any]:
        if handle.launch_mode != "sdk":
            return super().collect_artifacts(handle)
        return {
            "driver": self.name,
            "run_id": handle.run_id,
            "artifacts": [
                handle.metadata.get("raw_output_path"),
                handle.metadata.get("last_message_path"),
                handle.metadata.get("exit_code_path"),
                handle.metadata.get("state_path"),
                handle.metadata.get("worker_stderr_path"),
            ],
        }

"""Claude Code harness driver."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
from typing import Any
from uuid import uuid4

from src.hive.clock import utc_now_iso
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


class ClaudeCodeDriver(HarnessDriver):
    """Driver that stages or launches Claude runs."""

    name = "claude"
    binary_names = ("claude", "claude-code")
    display_name = "Claude Code"
    cli_label = "Claude Code CLI"
    declared_launch_mode = "sdk"
    declared_session_persistence = "session"
    declared_event_stream = "structured_deltas"
    declared_approvals = ("command", "file", "network")
    declared_skills = "list"
    declared_subagents = "native"
    declared_native_sandbox = "policy"
    declared_artifacts = ("diff", "transcript", "plan", "review")
    declared_reroute_export = "transcript_plus_context"

    def _live_exec_enabled(self) -> bool:
        raw = os.environ.get("HIVE_CLAUDE_LIVE_EXEC")
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
    def _load_result_payload(path_value: str | None) -> dict[str, Any]:
        if not path_value:
            return {}
        path = Path(path_value)
        if not path.exists():
            return {}
        lines = [
            line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
        ]
        if not lines:
            return {}
        try:
            payload = json.loads(lines[-1])
        except json.JSONDecodeError:
            return {}
        if not isinstance(payload, dict):
            return {}
        return payload

    @staticmethod
    def _sync_last_message(payload: dict[str, Any], path_value: str | None) -> str | None:
        if not path_value:
            return None
        result = payload.get("result")
        if not isinstance(result, str) or not result.strip():
            return None
        path = Path(path_value)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(result.strip() + "\n", encoding="utf-8")
        return str(path)

    @staticmethod
    def _budget_usage(payload: dict[str, Any]) -> RunBudgetUsage:
        usage = payload.get("usage")
        usage_map = usage if isinstance(usage, dict) else {}
        token_keys = (
            "input_tokens",
            "cache_creation_input_tokens",
            "cache_read_input_tokens",
            "output_tokens",
        )
        spent_tokens = sum(int(usage_map.get(key) or 0) for key in token_keys)
        duration_ms = int(payload.get("duration_ms") or 0)
        wall_minutes = 0 if duration_ms <= 0 else max(1, (duration_ms + 59_999) // 60_000)
        return RunBudgetUsage(
            spent_tokens=spent_tokens,
            spent_cost_usd=float(payload.get("total_cost_usd") or 0.0),
            wall_minutes=wall_minutes,
        )

    def _build_exec_prompt(self, request: RunLaunchRequest) -> str:
        run_brief_path = Path(request.artifacts_path) / "context" / "compiled" / "run-brief.md"
        run_brief = run_brief_path.read_text(encoding="utf-8")
        return "\n\n".join(
            [
                "You are Claude Code running inside a governed Hive v2.3 run.",
                "Read the run brief below, follow the recorded PROGRAM.md policy, make the "
                "needed repository changes inside the current worktree, and finish with a concise "
                "summary of what changed and any remaining risks.",
                run_brief.strip(),
            ]
        )

    def _launch_live_exec(self, request: RunLaunchRequest) -> RunHandle | None:
        binary_name, binary_path = self._detected_binary_details()
        if not self._live_exec_enabled() or not binary_path:
            return None

        help_text = self._command_output("--help") or ""
        if "--print" not in help_text or "--output-format" not in help_text:
            return None

        run_root = Path(request.artifacts_path)
        raw_output_path = run_root / "transcript" / "raw" / "claude-print-result.json"
        last_message_path = run_root / "transcript" / "raw" / "claude-last-message.txt"
        exit_code_path = run_root / "driver" / "claude-exec-exit.txt"
        command_path = run_root / "driver" / "claude-exec-command.txt"
        stderr_path = run_root / "logs" / "stderr.txt"
        raw_output_path.parent.mkdir(parents=True, exist_ok=True)

        session_id = str(uuid4()) if "--session-id" in help_text else None
        command = [
            binary_path,
            "--print",
            "--output-format",
            "json",
            "--add-dir",
            request.workspace.worktree_path,
        ]
        if "--permission-mode" in help_text:
            command.extend(["--permission-mode", "bypassPermissions"])
        elif "--dangerously-skip-permissions" in help_text:
            command.append("--dangerously-skip-permissions")
        if session_id:
            command.extend(["--session-id", session_id])
        if request.budget.max_cost_usd > 0:
            command.extend(["--max-budget-usd", str(request.budget.max_cost_usd)])
        if request.model:
            command.extend(["--model", request.model])

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
            session_id=session_id,
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
        probed = {
            "binary_name": binary_name,
            "print_mode": "--print" in help_text or "-p," in help_text,
            "output_format_json": "--output-format" in help_text and "json" in help_text,
            "input_format_stream_json": "--input-format" in help_text
            and "stream-json" in help_text,
            "resume": "--resume" in help_text,
            "continue": "--continue" in help_text,
            "session_id": "--session-id" in help_text,
            "permission_mode": "--permission-mode" in help_text,
            "tools": "--tools" in help_text,
            "mcp_config": "--mcp-config" in help_text,
            "session_persistence_toggle": "--no-session-persistence" in help_text,
            "max_budget_usd": "--max-budget-usd" in help_text,
        }
        notes = []
        if binary_name == "claude":
            notes.append("Claude is currently detected through the `claude` executable.")
        if probed["resume"] and probed["session_id"]:
            notes.append(
                "Claude CLI exposes resume/session flags, which supports truthful session "
                "continuity claims while the Hive adapter remains staged."
            )
        evidence = {
            "claude_cli_surface": (
                "Claude CLI help exposes print/stream/resume/session/permission controls."
                if help_text
                else "Claude CLI help could not be read on this machine."
            ),
            "claude_binary": (
                "Hive normalizes the `claude-code` executable to the `claude` driver."
                if binary_name == "claude"
                else "Hive detected a `claude-code` executable directly."
            ),
        }
        return probed, notes, evidence

    def probe(self) -> DriverInfo:
        info = super().probe()
        snapshot = info.capability_snapshot
        if snapshot is None:
            return info
        if (
            self._live_exec_enabled()
            and snapshot.probed.get("print_mode")
            and snapshot.probed.get("output_format_json")
        ):
            snapshot.effective = capability_surface(
                launch_mode="exec",
                session_persistence="ephemeral",
                event_stream="status",
                approvals=[],
                skills="file_projection",
                worktrees="host_managed",
                subagents="none",
                native_sandbox="none",
                outer_sandbox_required=True,
                artifacts=["runpack", "transcript", "plan", "review"],
                reroute_export="transcript",
            )
            snapshot.confidence["effective"] = "verified"
            snapshot.evidence["effective"] = (
                "Claude live exec mode is enabled, so Hive can launch a real non-interactive "
                "Claude Code session instead of staging the runpack."
            )
            info.capabilities.resume = False
            info.capabilities.interrupt = ["pause", "resume", "cancel"]
            info.capabilities.reroute_export = "transcript"
            info.notes.append(
                "Claude live exec is enabled; Hive can launch a real non-interactive Claude run."
            )
        return info

    def launch(self, request: RunLaunchRequest) -> RunHandle:
        live_handle = self._launch_live_exec(request)
        if live_handle is not None:
            return live_handle
        return super().launch(request)

    def status(self, handle: RunHandle) -> RunStatus:
        if handle.launch_mode != "exec":
            return super().status(handle)

        raw_output_path = str(handle.metadata.get("raw_output_path") or "")
        last_message_path = str(handle.metadata.get("last_message_path") or "")
        exit_code_path = str(handle.metadata.get("exit_code_path") or "")
        pid = int(handle.metadata.get("pid") or 0)
        exit_code = self._read_exit_code(exit_code_path)
        payload = self._load_result_payload(raw_output_path)
        synced_message_path = self._sync_last_message(payload, last_message_path)
        cursor = self._event_cursor(raw_output_path) or handle.event_cursor
        last_event_at = self._last_event_timestamp(
            raw_output_path,
            synced_message_path or last_message_path,
            exit_code_path,
        )
        budget = self._budget_usage(payload)
        session = {
            "launch_mode": "exec",
            "transport": "subprocess",
            "session_id": str(payload.get("session_id") or handle.session_id or "") or None,
            "pid": pid or None,
        }
        artifacts = {
            "raw_output_path": raw_output_path or None,
            "last_message_path": synced_message_path or last_message_path or None,
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
                        message="Claude Code is actively working in the Hive run worktree.",
                        percent=20,
                    ),
                    waiting_on=None,
                    last_event_at=last_event_at or handle.launched_at,
                    budget=budget,
                    event_cursor=cursor,
                    session=session,
                    artifacts=artifacts,
                )
            if isinstance(payload.get("result"), str) and str(payload.get("result")).strip():
                return RunStatus(
                    run_id=handle.run_id,
                    state="completed_candidate",
                    health="needs_attention",
                    driver=self.name,
                    progress=RunProgress(
                        phase="completed",
                        message=(
                            "Claude Code produced a result, but the live exec helper stopped "
                            "before writing an exit marker."
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
            return RunStatus(
                run_id=handle.run_id,
                state="failed",
                health="failed",
                driver=self.name,
                progress=RunProgress(
                    phase="failed",
                    message="Claude Code stopped without writing an exit marker.",
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
            return RunStatus(
                run_id=handle.run_id,
                state="completed_candidate",
                health="healthy",
                driver=self.name,
                progress=RunProgress(
                    phase="completed",
                    message="Claude Code finished and produced a candidate result for review.",
                    percent=100,
                ),
                waiting_on="review",
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
                message=f"Claude Code exited with status {exit_code}.",
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
        if handle.launch_mode != "exec":
            return super().interrupt(handle, mode)
        pid = int(handle.metadata.get("pid") or 0)
        if not pid:
            return {
                "ok": False,
                "driver": self.name,
                "run_id": handle.run_id,
                "mode": mode,
                "message": "Claude live exec handle does not include a live pid.",
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
            "message": f"Sent {sig.name} to Claude live exec pid {pid}.",
        }

    def collect_artifacts(self, handle: RunHandle) -> dict[str, Any]:
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

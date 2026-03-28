"""Pi run driver backed by the v2.4 worker-session adapter."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from src.hive.clock import utc_now_iso
from src.hive.drivers.base import Driver
from src.hive.drivers.types import (
    DriverCapabilities,
    DriverInfo,
    RunBudgetUsage,
    RunHandle,
    RunLaunchRequest,
    RunProgress,
    RunStatus,
    SteeringRequest,
)
from src.hive.integrations.models import GovernanceMode, SessionHandle
from src.hive.integrations.pi import PiWorkerAdapter
from src.hive.integrations.registry import get_integration


def _read_json(path_value: str | None) -> dict[str, Any]:
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


def _jsonl_count(path_value: str | None) -> int:
    if not path_value:
        return 0
    path = Path(path_value)
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _last_jsonl_record(path_value: str | None) -> dict[str, Any]:
    if not path_value:
        return {}
    path = Path(path_value)
    if not path.exists():
        return {}
    for raw_line in reversed(path.read_text(encoding="utf-8").splitlines()):
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return {}


def _wall_minutes(started_at: str | None) -> int:
    if not started_at:
        return 0
    try:
        started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    except ValueError:
        return 0
    now = datetime.now(timezone.utc)
    return max(0, int((now - started).total_seconds() // 60))


class PiDriver(Driver):
    """Hive run driver that uses the Pi worker-session adapter."""

    name = "pi"

    def _adapter(self, workspace_root: str | Path | None = None) -> PiWorkerAdapter:
        adapter = get_integration("pi")
        if not isinstance(adapter, PiWorkerAdapter):
            raise TypeError("The registered Pi integration is not a worker-session adapter.")
        if workspace_root is not None:
            adapter.workspace_root = Path(workspace_root).resolve()
        return adapter

    def _session_from_handle(self, handle: RunHandle) -> SessionHandle:
        payload = dict(handle.metadata.get("session") or {})
        if not payload:
            raise ValueError(f"Run {handle.run_id} is missing Pi session metadata.")
        return SessionHandle(**payload)

    def probe(self) -> DriverInfo:
        info = self._adapter().probe()
        supported_levels = {str(level) for level in info.supported_levels}
        notes = list(info.notes)
        notes.extend(info.configuration_problems)
        return DriverInfo(
            driver=self.name,
            version=info.version,
            available=bool({"attach", "managed"} & supported_levels),
            capabilities=DriverCapabilities(
                worktrees=True,
                resume=True,
                streaming=True,
                subagents=False,
                scheduled=False,
                remote_execution=False,
                diff_preview=True,
                sandbox="medium",
                context_files=["AGENTS.md"],
                skills=True,
                interrupt=["pause", "resume", "cancel"],
                reroute_export="transcript",
            ),
            capability_snapshot=info.capability_snapshot,
            notes=notes,
        )

    def launch(self, request: RunLaunchRequest) -> RunHandle:
        adapter = self._adapter(request.workspace.repo_root)
        attach_ref = str(request.metadata.get("attach_native_session_ref") or "").strip()
        if attach_ref:
            session = adapter.attach_session(
                attach_ref,
                GovernanceMode.ADVISORY,
                run_id=request.run_id,
            )
            session.project_id = request.project_id
            session.task_id = request.task_id
            session.metadata.setdefault("worktree_path", request.workspace.worktree_path)
            session.metadata.setdefault("compiled_context_path", request.compiled_context_path)
            session.metadata.setdefault("artifacts_path", request.artifacts_path)
        else:
            session = adapter.open_session(request)
        trajectory_path = str(session.metadata.get("trajectory_path") or "")
        state_path = str(session.metadata.get("state_path") or "")
        return RunHandle(
            run_id=request.run_id,
            driver=self.name,
            driver_handle=session.native_session_ref,
            status="running",
            launched_at=utc_now_iso(),
            launch_mode="sdk",
            transport=str(session.metadata.get("link_transport") or "process"),
            session_id=session.session_id,
            approval_channel=str(request.metadata.get("approval_channel") or "") or None,
            event_cursor=str(_jsonl_count(trajectory_path)),
            metadata={
                "session": session.to_dict(),
                "state_path": state_path,
                "trajectory_path": trajectory_path,
                "steering_path": session.metadata.get("steering_path"),
                "last_message_path": session.metadata.get("last_message_path"),
                "runner_manifest_path": session.metadata.get("runner_manifest_path"),
                "stdout_path": session.metadata.get("stdout_path"),
                "stderr_path": session.metadata.get("stderr_path"),
                "capability_snapshot": session.metadata.get("capability_snapshot"),
            },
        )

    def status(self, handle: RunHandle) -> RunStatus:
        session = self._session_from_handle(handle)
        state = _read_json(str(handle.metadata.get("state_path") or ""))
        trajectory_path = str(handle.metadata.get("trajectory_path") or "")
        last_event = _last_jsonl_record(trajectory_path)
        current_state = str(state.get("state") or "running")
        if current_state == "completed":
            current_state = "completed_candidate"
        progress_message = str(
            state.get("message")
            or last_event.get("payload", {}).get("text")
            or (
                "Pi advisory session is attached to this run."
                if session.governance_mode == GovernanceMode.ADVISORY
                else "Pi managed session is active."
            )
        )
        phase = "attached" if session.governance_mode == GovernanceMode.ADVISORY else "implementing"
        if current_state == "completed_candidate":
            phase = "complete"
        elif current_state == "failed":
            phase = "failed"
        elif current_state == "cancelled":
            phase = "cancelled"
        health = str(
            state.get("health")
            or (
                "failed"
                if current_state == "failed"
                else "cancelled"
                if current_state == "cancelled"
                else "healthy"
            )
        )
        artifacts = {
            "trajectory_path": trajectory_path or None,
            "steering_path": handle.metadata.get("steering_path"),
            "last_message_path": handle.metadata.get("last_message_path"),
            "runner_manifest_path": handle.metadata.get("runner_manifest_path"),
            "stdout_path": handle.metadata.get("stdout_path"),
            "stderr_path": handle.metadata.get("stderr_path"),
            "native_transcript_path": session.metadata.get("native_transcript_path"),
            "native_session_root": session.metadata.get("native_session_root"),
        }
        return RunStatus(
            run_id=handle.run_id,
            state=current_state,
            health=health,
            driver=self.name,
            progress=RunProgress(
                phase=phase,
                message=progress_message,
                percent=state.get("percent"),
            ),
            waiting_on=str(state.get("waiting_on") or "") or None,
            last_event_at=str(last_event.get("ts") or state.get("updated_at") or handle.launched_at),
            budget=RunBudgetUsage(
                spent_tokens=int(state.get("spent_tokens") or 0),
                spent_cost_usd=float(state.get("spent_cost_usd") or 0.0),
                wall_minutes=int(state.get("wall_minutes") or _wall_minutes(handle.launched_at)),
            ),
            event_cursor=str(_jsonl_count(trajectory_path)),
            session={
                "session_id": session.session_id,
                "transport": handle.transport,
                "native_session_ref": session.native_session_ref,
                "adapter_family": str(session.adapter_family),
                "governance_mode": str(session.governance_mode),
                "integration_level": str(session.integration_level),
                "sandbox_owner": "hive"
                if session.governance_mode == GovernanceMode.GOVERNED
                else "pi",
            },
            artifacts=artifacts,
        )

    def interrupt(self, handle: RunHandle, mode: str) -> dict[str, Any]:
        session = self._session_from_handle(handle)
        adapter = self._adapter(session.metadata.get("workspace_root"))
        return adapter.send_steer(session, SteeringRequest(action=mode))

    def steer(self, handle: RunHandle, request: SteeringRequest) -> dict[str, Any]:
        session = self._session_from_handle(handle)
        adapter = self._adapter(session.metadata.get("workspace_root"))
        return adapter.send_steer(session, request)

    def collect_artifacts(self, handle: RunHandle) -> dict[str, Any]:
        session = self._session_from_handle(handle)
        adapter = self._adapter(session.metadata.get("workspace_root"))
        return adapter.collect_artifacts(session)

    def stream_events(self, handle: RunHandle):
        session = self._session_from_handle(handle)
        adapter = self._adapter(session.metadata.get("workspace_root"))
        return adapter.stream_events(session)

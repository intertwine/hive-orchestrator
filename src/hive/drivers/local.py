"""Local run driver."""

from __future__ import annotations

from src.hive.clock import utc_now_iso
from src.hive.drivers.base import Driver
from src.hive.drivers.types import (
    DriverCapabilities,
    DriverInfo,
    RunHandle,
    RunLaunchRequest,
    RunProgress,
    RunStatus,
)
from src.hive.runtime import CapabilitySnapshot, capability_surface


class LocalDriver(Driver):
    """Local worktree-backed run driver."""

    name = "local"

    def probe(self) -> DriverInfo:
        snapshot = CapabilitySnapshot(
            driver=self.name,
            declared=capability_surface(
                launch_mode="local",
                session_persistence="session",
                event_stream="status",
                approvals=[],
                skills="file_projection",
                worktrees="host_managed",
                subagents="none",
                native_sandbox="none",
                outer_sandbox_required=False,
                artifacts=["runpack", "transcript", "patch", "review"],
                reroute_export="transcript",
            ),
            probed={"workspace_available": True},
            effective=capability_surface(
                launch_mode="local",
                session_persistence="session",
                event_stream="status",
                approvals=[],
                skills="file_projection",
                worktrees="host_managed",
                subagents="none",
                native_sandbox="none",
                outer_sandbox_required=False,
                artifacts=["runpack", "transcript", "patch", "review"],
                reroute_export="transcript",
            ),
            confidence={"launch_mode": "verified", "effective": "verified"},
            evidence={
                "launch_mode": "Local driver manages a Hive worktree-backed run directly.",
                "effective": "No external harness integration is involved for the local driver.",
            },
        )
        return DriverInfo(
            driver=self.name,
            capabilities=DriverCapabilities(
                worktrees=True,
                resume=True,
                streaming=False,
                subagents=False,
                scheduled=True,
                remote_execution=False,
                diff_preview=True,
                sandbox="medium",
                context_files=["AGENTS.md"],
                skills=True,
                interrupt=["pause", "cancel"],
                reroute_export="transcript",
            ),
            capability_snapshot=snapshot,
        )

    def launch(self, request: RunLaunchRequest) -> RunHandle:
        return RunHandle(
            run_id=request.run_id,
            driver=self.name,
            driver_handle=f"local:{request.run_id}",
            status="running",
            launched_at=utc_now_iso(),
            launch_mode="local",
            transport="process",
            metadata={
                "worktree_path": request.workspace.worktree_path,
                "artifacts_path": request.artifacts_path,
            },
        )

    def status(self, handle: RunHandle) -> RunStatus:
        return RunStatus(
            run_id=handle.run_id,
            state=handle.status,
            health="healthy",
            driver=self.name,
            progress=RunProgress(
                phase="implementing",
                message="Local run worktree is ready for implementation.",
                percent=5,
            ),
            waiting_on=None,
            last_event_at=utc_now_iso(),
            session={"launch_mode": "local", "transport": "process"},
        )

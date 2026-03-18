"""Manual execution driver."""

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


class ManualDriver(Driver):
    """A driver that stages work for a human or external process."""

    name = "manual"

    def probe(self) -> DriverInfo:
        snapshot = CapabilitySnapshot(
            driver=self.name,
            declared=capability_surface(
                launch_mode="staged",
                session_persistence="none",
                event_stream="none",
                approvals=[],
                skills="file_projection",
                worktrees="host_managed",
                subagents="none",
                native_sandbox="none",
                outer_sandbox_required=True,
                artifacts=["runpack"],
                reroute_export="none",
            ),
            probed={"manual_handoff": True},
            effective=capability_surface(
                launch_mode="staged",
                session_persistence="none",
                event_stream="none",
                approvals=[],
                skills="file_projection",
                worktrees="host_managed",
                subagents="none",
                native_sandbox="none",
                outer_sandbox_required=True,
                artifacts=["runpack"],
                reroute_export="none",
            ),
            confidence={"launch_mode": "verified", "effective": "verified"},
            evidence={
                "launch_mode": "Manual driver only prepares the runpack.",
                "effective": "A human or unsupported harness must attach outside Hive.",
            },
        )
        return DriverInfo(
            driver=self.name,
            capabilities=DriverCapabilities(
                worktrees=True,
                resume=False,
                streaming=False,
                subagents=False,
                scheduled=False,
                remote_execution=False,
                diff_preview=True,
                sandbox="none",
                context_files=["AGENTS.md"],
                skills=False,
                interrupt=[],
                reroute_export="none",
            ),
            capability_snapshot=snapshot,
            notes=[
                "Stages a governed run pack for manual execution.",
                "Use this when a human or unsupported harness should drive the worktree.",
            ],
        )

    def launch(self, request: RunLaunchRequest) -> RunHandle:
        return RunHandle(
            run_id=request.run_id,
            driver=self.name,
            driver_handle=f"manual:{request.run_id}",
            status="awaiting_input",
            launched_at=utc_now_iso(),
        )

    def status(self, handle: RunHandle) -> RunStatus:
        return RunStatus(
            run_id=handle.run_id,
            state=handle.status,
            health="needs_attention",
            driver=self.name,
            progress=RunProgress(
                phase="waiting",
                message="Run pack prepared; waiting for a human or external harness to attach.",
                percent=0,
            ),
            waiting_on="operator",
            last_event_at=utc_now_iso(),
        )

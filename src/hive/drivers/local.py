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


class LocalDriver(Driver):
    """Local worktree-backed run driver."""

    name = "local"

    def probe(self) -> DriverInfo:
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
                reroute_export="metadata-only",
            ),
        )

    def launch(self, request: RunLaunchRequest) -> RunHandle:
        return RunHandle(
            run_id=request.run_id,
            driver=self.name,
            driver_handle=f"local:{request.run_id}",
            status="running",
            launched_at=utc_now_iso(),
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
        )

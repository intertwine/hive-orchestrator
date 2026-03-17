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


class ManualDriver(Driver):
    """A driver that stages work for a human or external process."""

    name = "manual"

    def probe(self) -> DriverInfo:
        return DriverInfo(
            driver=self.name,
            capabilities=DriverCapabilities(
                worktrees=True,
                resume=False,
                streaming=False,
                subagents=False,
                scheduled=True,
                remote_execution=False,
                diff_preview=True,
                sandbox="none",
                context_files=["AGENTS.md"],
                skills=True,
                interrupt=["cancel"],
                reroute_export="metadata-only",
            ),
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

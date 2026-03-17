"""Codex harness driver."""

from __future__ import annotations

from pathlib import Path
import shutil

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


class CodexDriver(Driver):
    """Driver that stages runs for Codex."""

    name = "codex"

    def _notes(self) -> list[str]:
        notes = [
            "Hive prepares a Codex-ready run pack with compiled context and worktree metadata.",
            "Codex is not auto-launched from Hive yet; attach the run from the prepared worktree.",
        ]
        binary = shutil.which("codex")
        if binary:
            notes.append(f"Detected Codex CLI at {Path(binary).resolve()}.")
        else:
            notes.append("Codex CLI was not detected on PATH; the staged run can still be handed off.")
        return notes

    def probe(self) -> DriverInfo:
        return DriverInfo(
            driver=self.name,
            capabilities=DriverCapabilities(
                worktrees=True,
                resume=True,
                streaming=True,
                subagents=True,
                scheduled=True,
                remote_execution=False,
                diff_preview=True,
                sandbox="medium",
                context_files=["AGENTS.md"],
                skills=True,
                interrupt=["pause", "cancel"],
                reroute_export="transcript-aware",
            ),
            notes=self._notes(),
        )

    def launch(self, request: RunLaunchRequest) -> RunHandle:
        return RunHandle(
            run_id=request.run_id,
            driver=self.name,
            driver_handle=f"codex:{request.run_id}",
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
                message="Codex run pack is ready; attach a Codex session to continue.",
                percent=0,
            ),
            waiting_on="codex",
            last_event_at=utc_now_iso(),
        )

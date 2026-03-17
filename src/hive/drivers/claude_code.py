"""Claude Code harness driver."""

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


class ClaudeCodeDriver(Driver):
    """Driver that stages runs for Claude Code."""

    name = "claude-code"

    def _notes(self) -> list[str]:
        notes = [
            "Hive prepares a Claude Code-ready run pack with compiled context and worktree metadata.",
            "Claude Code is not auto-launched from Hive yet; attach the run from the prepared worktree.",
        ]
        for candidate in ("claude", "claude-code"):
            binary = shutil.which(candidate)
            if binary:
                notes.append(f"Detected Claude Code CLI at {Path(binary).resolve()}.")
                break
        else:
            notes.append(
                "Claude Code CLI was not detected on PATH; the staged run can still be handed off."
            )
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
            driver_handle=f"claude-code:{request.run_id}",
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
                message="Claude Code run pack is ready; attach a Claude Code session to continue.",
                percent=0,
            ),
            waiting_on="claude-code",
            last_event_at=utc_now_iso(),
        )

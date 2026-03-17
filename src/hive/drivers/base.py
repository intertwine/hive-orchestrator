"""Driver protocol helpers for Hive 2.2."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
import shutil
from typing import Any, Iterator

from src.hive.clock import utc_now_iso
from src.hive.drivers.types import (
    DriverCapabilities,
    DriverInfo,
    RunHandle,
    RunLaunchRequest,
    RunProgress,
    RunStatus,
    SteeringRequest,
)


class Driver(ABC):
    """Abstract base class for normalized run drivers."""

    name: str

    @abstractmethod
    def probe(self) -> DriverInfo:
        """Return driver capability and availability information."""

    @abstractmethod
    def launch(self, request: RunLaunchRequest) -> RunHandle:
        """Launch or stage a run."""

    def resume(self, handle: RunHandle) -> RunHandle:
        """Resume a run handle when the driver supports it."""
        return handle

    @abstractmethod
    def status(self, handle: RunHandle) -> RunStatus:
        """Return the normalized status for an existing handle."""

    def interrupt(self, handle: RunHandle, mode: str) -> dict[str, Any]:
        """Interrupt or cancel a run when supported."""
        return {
            "ok": False,
            "driver": self.name,
            "run_id": handle.run_id,
            "mode": mode,
            "message": f"Driver {self.name} does not support interrupt mode {mode!r}.",
        }

    def steer(self, handle: RunHandle, request: SteeringRequest) -> dict[str, Any]:
        """Apply a typed steering request to an active run."""
        return {
            "ok": True,
            "driver": self.name,
            "run_id": handle.run_id,
            "action": request.action,
            "message": f"Recorded steering action {request.action!r} for {self.name}.",
        }

    def collect_artifacts(self, handle: RunHandle) -> dict[str, Any]:
        """Return additional driver-owned artifacts."""
        return {"driver": self.name, "run_id": handle.run_id, "artifacts": []}

    def stream_events(self, handle: RunHandle) -> Iterator[dict[str, Any]]:
        """Yield driver-originated events when the backend supports streaming."""
        del handle
        return iter(())


class HarnessDriver(Driver):
    """Shared staging behavior for external harness drivers."""

    name: str
    binary_names: tuple[str, ...] = ()
    display_name: str
    cli_label: str

    def _notes(self) -> list[str]:
        notes = [
            f"Hive prepares a {self.display_name}-ready run pack with compiled context and "
            "worktree metadata.",
            f"{self.display_name} is not auto-launched from Hive yet; attach the run from the "
            "prepared worktree.",
        ]
        for candidate in self.binary_names:
            binary = shutil.which(candidate)
            if binary:
                notes.append(f"Detected {self.cli_label} at {Path(binary).resolve()}.")
                break
        else:
            notes.append(
                f"{self.cli_label} was not detected on PATH; the staged run can still be handed off."
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
            driver_handle=f"{self.name}:{request.run_id}",
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
                message=(
                    f"{self.display_name} run pack is ready; attach a {self.display_name} "
                    "session to continue."
                ),
                percent=0,
            ),
            waiting_on=self.name,
            last_event_at=utc_now_iso(),
        )

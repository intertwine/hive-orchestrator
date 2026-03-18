"""Driver protocol helpers for Hive 2.2."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
import shutil
import subprocess
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
from src.hive.runtime import CapabilitySnapshot, capability_surface


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
    declared_launch_mode: str = "staged"
    declared_session_persistence: str = "none"
    declared_event_stream: str = "none"
    declared_approvals: tuple[str, ...] = ()
    declared_skills: str = "file_projection"
    declared_subagents: str = "none"
    declared_native_sandbox: str = "none"
    declared_artifacts: tuple[str, ...] = ("runpack",)
    declared_reroute_export: str = "none"

    def _detected_binary_details(self) -> tuple[str | None, str | None]:
        for candidate in self.binary_names:
            binary = shutil.which(candidate)
            if binary:
                return candidate, str(Path(binary).resolve())
        return None, None

    def _detected_binary(self) -> str | None:
        """Return the resolved binary path when one of the declared names exists."""
        return self._detected_binary_details()[1]

    def _command_output(self, *args: str) -> str | None:
        binary_name, binary_path = self._detected_binary_details()
        del binary_name
        if not binary_path:
            return None
        try:
            result = subprocess.run(
                [binary_path, *args],
                check=False,
                capture_output=True,
                text=True,
                timeout=2,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        output = result.stdout.strip() or result.stderr.strip()
        return output or None

    def _version_text(self) -> str | None:
        for args in (("--version",), ("version",)):
            output = self._command_output(*args)
            if output:
                return output.splitlines()[0].strip()
        return None

    def _probe_details(
        self,
        *,
        binary_name: str | None,
        binary_path: str | None,
    ) -> tuple[dict[str, Any], list[str], dict[str, str]]:
        del binary_name, binary_path
        return {}, [], {}

    def _notes(self) -> list[str]:
        notes = [
            f"Hive prepares a {self.display_name}-ready run pack with compiled context and "
            "worktree metadata.",
            f"{self.display_name} is not auto-launched from Hive yet; attach the run from the "
            "prepared worktree.",
        ]
        binary = self._detected_binary()
        if binary:
            notes.append(f"Detected {self.cli_label} at {binary}.")
        else:
            notes.append(
                f"{self.cli_label} was not detected on PATH; "
                "the staged run can still be handed off."
            )
        return notes

    def _declared_snapshot(
        self, *, binary_present: bool, binary_path: str | None
    ) -> CapabilitySnapshot:
        evidence = {
            "launch_mode": (
                f"{self.display_name} family intends to integrate via {self.declared_launch_mode}."
            ),
            "effective": (
                f"{self.display_name} is still staged in the current implementation; "
                "interactive control stays disabled until a deep adapter lands."
            ),
        }
        if binary_path:
            evidence["binary"] = binary_path
        return CapabilitySnapshot(
            driver=self.name,
            declared=capability_surface(
                launch_mode=self.declared_launch_mode,
                session_persistence=self.declared_session_persistence,
                event_stream=self.declared_event_stream,
                approvals=list(self.declared_approvals),
                skills=self.declared_skills,
                worktrees="host_managed",
                subagents=self.declared_subagents,
                native_sandbox=self.declared_native_sandbox,
                outer_sandbox_required=True,
                artifacts=list(self.declared_artifacts),
                reroute_export=self.declared_reroute_export,
            ),
            probed={
                "binary_present": binary_present,
                "binary_path": binary_path,
            },
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
            confidence={
                "launch_mode": "planned",
                "event_stream": "planned",
                "subagents": "planned",
                "effective": "verified",
            },
            evidence=evidence,
        )

    def probe(self) -> DriverInfo:
        binary_name, binary_path = self._detected_binary_details()
        snapshot = self._declared_snapshot(
            binary_present=bool(binary_path),
            binary_path=binary_path,
        )
        extra_probed, extra_notes, extra_evidence = self._probe_details(
            binary_name=binary_name,
            binary_path=binary_path,
        )
        snapshot.probed.update(extra_probed)
        snapshot.evidence.update(extra_evidence)
        version_text = self._version_text()
        return DriverInfo(
            driver=self.name,
            version=version_text or "0.0.0",
            capabilities=DriverCapabilities(
                worktrees=True,
                resume=False,
                streaming=False,
                subagents=False,
                scheduled=False,
                remote_execution=False,
                diff_preview=True,
                sandbox="low",
                context_files=["AGENTS.md"],
                skills=False,
                interrupt=[],
                reroute_export="none",
            ),
            capability_snapshot=snapshot,
            notes=[*self._notes(), *extra_notes],
        )

    def launch(self, request: RunLaunchRequest) -> RunHandle:
        return RunHandle(
            run_id=request.run_id,
            driver=self.name,
            driver_handle=f"{self.name}:{request.run_id}",
            status="awaiting_input",
            launched_at=utc_now_iso(),
            launch_mode="staged",
            transport="manual",
            metadata={
                "declared_launch_mode": self.declared_launch_mode,
                "compiled_context_path": request.compiled_context_path,
                "artifacts_path": request.artifacts_path,
            },
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
            session={
                "launch_mode": "staged",
                "transport": "manual",
            },
        )

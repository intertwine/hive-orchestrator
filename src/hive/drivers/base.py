"""Driver protocol helpers for Hive 2.2."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterator

from src.hive.drivers.types import (
    DriverInfo,
    RunHandle,
    RunLaunchRequest,
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

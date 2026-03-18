"""Typed driver contracts for Hive 2.3-compatible driver probing."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from src.hive.runtime.capabilities import CapabilitySnapshot

SandboxLevel = Literal["low", "medium", "high"]


@dataclass
class DriverCapabilities:
    """Normalized capability map exposed by every driver."""

    worktrees: bool = True
    resume: bool = True
    streaming: bool = False
    subagents: bool = False
    scheduled: bool = False
    remote_execution: bool = False
    diff_preview: bool = True
    sandbox: SandboxLevel = "medium"
    context_files: list[str] = field(default_factory=list)
    skills: bool = True
    interrupt: list[str] = field(default_factory=list)
    reroute_export: str = "metadata-only"

    def to_dict(self) -> dict[str, Any]:
        """Serialize capabilities for JSON output."""
        return asdict(self)


@dataclass
class DriverInfo:
    """Probe result for an installed or virtual driver."""

    driver: str
    version: str = "0.0.0"
    available: bool = True
    capabilities: DriverCapabilities = field(default_factory=DriverCapabilities)
    capability_snapshot: CapabilitySnapshot | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize probe data for JSON output."""
        payload = {
            "driver": self.driver,
            "version": self.version,
            "available": self.available,
            "capabilities": self.capabilities.to_dict(),
            "notes": list(self.notes),
        }
        if self.capability_snapshot is not None:
            snapshot = self.capability_snapshot.to_dict()
            payload["capability_snapshot"] = snapshot
            payload["declared"] = snapshot["declared"]
            payload["probed"] = snapshot["probed"]
            payload["effective"] = snapshot["effective"]
            payload["confidence"] = snapshot["confidence"]
            payload["evidence"] = snapshot["evidence"]
        return payload


@dataclass
class RunBudget:
    """Normalized budget envelope for a launched run."""

    max_tokens: int
    max_cost_usd: float
    max_wall_minutes: int

    def to_dict(self) -> dict[str, Any]:
        """Serialize the launch budget."""
        return asdict(self)


@dataclass
class RunWorkspace:
    """Workspace details handed to a driver launch request."""

    repo_root: str
    worktree_path: str
    base_branch: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize workspace metadata."""
        return asdict(self)


@dataclass
class RunLaunchRequest:
    """Normalized request that every driver receives."""

    run_id: str
    task_id: str
    project_id: str
    campaign_id: str | None
    driver: str
    model: str | None
    budget: RunBudget
    workspace: RunWorkspace
    compiled_context_path: str
    artifacts_path: str
    program_policy: dict[str, Any]
    steering_notes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize launch input."""
        return {
            "run_id": self.run_id,
            "task_id": self.task_id,
            "project_id": self.project_id,
            "campaign_id": self.campaign_id,
            "driver": self.driver,
            "model": self.model,
            "budget": self.budget.to_dict(),
            "workspace": self.workspace.to_dict(),
            "compiled_context_path": self.compiled_context_path,
            "artifacts_path": self.artifacts_path,
            "program_policy": dict(self.program_policy),
            "steering_notes": list(self.steering_notes),
            "metadata": dict(self.metadata),
        }


@dataclass
class RunHandle:
    """Driver-owned handle after a launch or resume."""

    run_id: str
    driver: str
    driver_handle: str
    status: str
    launched_at: str
    launch_mode: str | None = None
    transport: str | None = None
    session_id: str | None = None
    thread_id: str | None = None
    resume_token: str | None = None
    event_cursor: str | None = None
    approval_channel: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize handle metadata."""
        return {
            "run_id": self.run_id,
            "driver": self.driver,
            "driver_handle": self.driver_handle,
            "status": self.status,
            "launched_at": self.launched_at,
            "launch_mode": self.launch_mode,
            "transport": self.transport,
            "session_id": self.session_id,
            "thread_id": self.thread_id,
            "resume_token": self.resume_token,
            "event_cursor": self.event_cursor,
            "approval_channel": self.approval_channel,
            "metadata": dict(self.metadata),
        }


@dataclass
class RunProgress:
    """Human-friendly progress block for a driver status."""

    phase: str
    message: str
    percent: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize progress metadata."""
        return asdict(self)


@dataclass
class RunLinks:
    """Optional URLs or deep links for a run."""

    driver_ui: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize status links."""
        return asdict(self)


@dataclass
class RunBudgetUsage:
    """Observed spend for a run."""

    spent_tokens: int = 0
    spent_cost_usd: float = 0.0
    wall_minutes: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize current budget usage."""
        return asdict(self)


@dataclass
class RunStatus:
    """Normalized driver-reported status."""

    run_id: str
    state: str
    health: str
    driver: str
    progress: RunProgress
    waiting_on: str | None
    last_event_at: str | None
    budget: RunBudgetUsage = field(default_factory=RunBudgetUsage)
    links: RunLinks = field(default_factory=RunLinks)
    pending_approvals: list[dict[str, Any]] = field(default_factory=list)
    event_cursor: str | None = None
    session: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize a driver status."""
        return {
            "run_id": self.run_id,
            "state": self.state,
            "health": self.health,
            "driver": self.driver,
            "progress": self.progress.to_dict(),
            "waiting_on": self.waiting_on,
            "last_event_at": self.last_event_at,
            "budget": self.budget.to_dict(),
            "links": self.links.to_dict(),
            "pending_approvals": list(self.pending_approvals),
            "event_cursor": self.event_cursor,
            "session": dict(self.session),
            "artifacts": dict(self.artifacts),
        }


@dataclass
class SteeringRequest:
    """Typed steering request shared across CLI, UI, and drivers."""

    action: str
    reason: str | None = None
    target: dict[str, Any] | None = None
    budget_delta: dict[str, Any] | None = None
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the steering request."""
        return {
            "action": self.action,
            "reason": self.reason,
            "target": dict(self.target or {}),
            "budget_delta": dict(self.budget_delta or {}),
            "note": self.note,
        }

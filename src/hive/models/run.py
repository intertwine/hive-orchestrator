"""Run metadata model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.hive.clock import utc_now_iso


@dataclass
class RunRecord:
    """Immutable run metadata."""

    id: str
    project_id: str
    task_id: str
    mode: str = "workflow"
    status: str = "planned"
    executor: str = "local"
    branch_name: str | None = None
    worktree_path: str | None = None
    program_path: str | None = None
    program_sha256: str | None = None
    plan_path: str | None = None
    summary_path: str | None = None
    review_path: str | None = None
    patch_path: str | None = None
    command_log_path: str | None = None
    logs_dir: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost_usd: float | None = None
    started_at: str = field(default_factory=utc_now_iso)
    finished_at: str | None = None
    exit_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize run metadata."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "mode": self.mode,
            "status": self.status,
            "executor": self.executor,
            "branch_name": self.branch_name,
            "worktree_path": self.worktree_path,
            "program_path": self.program_path,
            "program_sha256": self.program_sha256,
            "plan_path": self.plan_path,
            "summary_path": self.summary_path,
            "review_path": self.review_path,
            "patch_path": self.patch_path,
            "command_log_path": self.command_log_path,
            "logs_dir": self.logs_dir,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "cost_usd": self.cost_usd,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "exit_reason": self.exit_reason,
            "metadata_json": self.metadata,
        }

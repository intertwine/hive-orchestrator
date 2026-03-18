"""Run metadata model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.hive.clock import utc_now_iso


@dataclass
class RunRecord:
    """Immutable run metadata.

    The in-memory attribute is named ``metadata`` for ergonomic access, while the serialized key
    remains ``metadata_json`` so it cannot be confused with the run's top-level metadata fields.
    """

    id: str
    project_id: str
    task_id: str
    driver: str = "local"
    driver_handle: str | None = None
    campaign_id: str | None = None
    mode: str = "workflow"
    status: str = "queued"
    health: str = "healthy"
    executor: str = "local"
    branch_name: str | None = None
    worktree_path: str | None = None
    program_path: str | None = None
    program_sha256: str | None = None
    runtime_manifest_path: str | None = None
    capability_snapshot_path: str | None = None
    sandbox_policy_path: str | None = None
    launch_path: str | None = None
    context_manifest_path: str | None = None
    context_compiled_dir: str | None = None
    transcript_path: str | None = None
    transcript_ndjson_path: str | None = None
    transcript_raw_dir: str | None = None
    workspace_patch_path: str | None = None
    workspace_changed_files_path: str | None = None
    driver_metadata_path: str | None = None
    driver_handles_path: str | None = None
    events_path: str | None = None
    events_ndjson_path: str | None = None
    approvals_path: str | None = None
    retrieval_trace_path: str | None = None
    retrieval_hits_path: str | None = None
    scheduler_candidate_set_path: str | None = None
    scheduler_decision_path: str | None = None
    plan_path: str | None = None
    summary_path: str | None = None
    review_path: str | None = None
    patch_path: str | None = None
    command_log_path: str | None = None
    logs_dir: str | None = None
    final_path: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost_usd: float | None = None
    started_at: str = field(default_factory=utc_now_iso)
    finished_at: str | None = None
    exit_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize run metadata using ``metadata_json`` for the nested payload."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "driver": self.driver,
            "driver_handle": self.driver_handle,
            "campaign_id": self.campaign_id,
            "mode": self.mode,
            "status": self.status,
            "health": self.health,
            "executor": self.executor,
            "branch_name": self.branch_name,
            "worktree_path": self.worktree_path,
            "program_path": self.program_path,
            "program_sha256": self.program_sha256,
            "runtime_manifest_path": self.runtime_manifest_path,
            "capability_snapshot_path": self.capability_snapshot_path,
            "sandbox_policy_path": self.sandbox_policy_path,
            "launch_path": self.launch_path,
            "context_manifest_path": self.context_manifest_path,
            "context_compiled_dir": self.context_compiled_dir,
            "transcript_path": self.transcript_path,
            "transcript_ndjson_path": self.transcript_ndjson_path,
            "transcript_raw_dir": self.transcript_raw_dir,
            "workspace_patch_path": self.workspace_patch_path,
            "workspace_changed_files_path": self.workspace_changed_files_path,
            "driver_metadata_path": self.driver_metadata_path,
            "driver_handles_path": self.driver_handles_path,
            "events_path": self.events_path,
            "events_ndjson_path": self.events_ndjson_path,
            "approvals_path": self.approvals_path,
            "retrieval_trace_path": self.retrieval_trace_path,
            "retrieval_hits_path": self.retrieval_hits_path,
            "scheduler_candidate_set_path": self.scheduler_candidate_set_path,
            "scheduler_decision_path": self.scheduler_decision_path,
            "plan_path": self.plan_path,
            "summary_path": self.summary_path,
            "review_path": self.review_path,
            "patch_path": self.patch_path,
            "command_log_path": self.command_log_path,
            "logs_dir": self.logs_dir,
            "final_path": self.final_path,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "cost_usd": self.cost_usd,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "exit_reason": self.exit_reason,
            "metadata_json": self.metadata,
        }

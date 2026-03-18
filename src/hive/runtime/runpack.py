"""v2.3 runpack helpers and canonical run artifact scaffolding."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from src.hive.flags import feature_flags
from src.hive.runtime.capabilities import CapabilitySnapshot


@dataclass
class SandboxPolicy:
    """Persisted sandbox policy for a run."""

    backend: str
    isolation_class: str
    network: dict[str, Any]
    mounts: dict[str, Any]
    resources: dict[str, Any]
    env: dict[str, Any]
    snapshot: bool
    resume: bool
    profile: str = "legacy-default"
    provenance: str = "legacy-host"

    def to_dict(self) -> dict[str, Any]:
        """Serialize the sandbox policy."""
        return {
            "backend": self.backend,
            "isolation_class": self.isolation_class,
            "network": dict(self.network),
            "mounts": dict(self.mounts),
            "resources": dict(self.resources),
            "env": dict(self.env),
            "snapshot": self.snapshot,
            "resume": self.resume,
            "profile": self.profile,
            "provenance": self.provenance,
        }


def default_sandbox_policy(
    *,
    worktree_path: str,
    artifacts_path: str,
    profile: str = "legacy-default",
) -> SandboxPolicy:
    """Return a truthful legacy-host sandbox placeholder until real backends land."""
    return SandboxPolicy(
        backend="legacy-host",
        isolation_class="host",
        network={"mode": "inherit", "allowlist": []},
        mounts={"read_only": [], "read_write": [worktree_path, artifacts_path]},
        resources={
            "cpu": None,
            "memory_mb": None,
            "disk_mb": None,
            "wall_clock_sec": None,
        },
        env={"inherit": True, "allowlist": []},
        snapshot=False,
        resume=False,
        profile=profile,
        provenance="runtime_v2_scaffold",
    )


def runtime_manifest(
    *,
    run_id: str,
    task_id: str,
    project_id: str,
    campaign_id: str | None,
    driver: str,
    driver_mode: str,
    sandbox_backend: str,
    sandbox_profile: str,
    repo_root: str,
    worktree_path: str,
    base_branch: str,
    compiled_context_manifest: str,
    capability_snapshot_path: str,
    scheduler_decision_path: str,
    retrieval_trace_path: str,
) -> dict[str, Any]:
    """Build the canonical v2.3 run manifest payload."""
    return {
        "run_id": run_id,
        "task_id": task_id,
        "project_id": project_id,
        "campaign_id": campaign_id,
        "driver": driver,
        "driver_mode": driver_mode,
        "sandbox_backend": sandbox_backend,
        "sandbox_profile": sandbox_profile,
        "workspace": {
            "repo_root": repo_root,
            "worktree_path": worktree_path,
            "base_branch": base_branch,
        },
        "compiled_context_manifest": compiled_context_manifest,
        "capability_snapshot": capability_snapshot_path,
        "scheduler_decision": scheduler_decision_path,
        "retrieval_trace": retrieval_trace_path,
        "feature_flags": feature_flags(),
    }


def write_runtime_scaffold(
    run_directory: Path,
    *,
    manifest: dict[str, Any],
    capability_snapshot: CapabilitySnapshot,
    sandbox_policy: SandboxPolicy,
) -> dict[str, Path]:
    """Create the canonical v2.3 artifact layout and seed baseline files."""
    retrieval_dir = run_directory / "retrieval"
    scheduler_dir = run_directory / "scheduler"
    artifacts_dir = run_directory / "artifacts"
    artifacts_logs_dir = artifacts_dir / "logs"
    eval_dir = run_directory / "eval"
    for directory in (retrieval_dir, scheduler_dir, artifacts_dir, artifacts_logs_dir, eval_dir):
        directory.mkdir(parents=True, exist_ok=True)

    paths = {
        "manifest_path": run_directory / "manifest.json",
        "capability_snapshot_path": run_directory / "capability-snapshot.json",
        "sandbox_policy_path": run_directory / "sandbox-policy.json",
        "events_ndjson_path": run_directory / "events.ndjson",
        "approvals_path": run_directory / "approvals.ndjson",
        "transcript_ndjson_path": run_directory / "transcript.ndjson",
        "retrieval_trace_path": retrieval_dir / "trace.json",
        "retrieval_hits_path": retrieval_dir / "hits.json",
        "scheduler_candidate_set_path": scheduler_dir / "candidate-set.json",
        "scheduler_decision_path": scheduler_dir / "decision.json",
        "eval_results_path": eval_dir / "results.json",
        "final_path": run_directory / "final.json",
        "artifacts_dir": artifacts_dir,
        "artifacts_logs_dir": artifacts_logs_dir,
    }

    payloads: dict[str, Any] = {
        "manifest_path": manifest,
        "capability_snapshot_path": capability_snapshot.to_dict(),
        "sandbox_policy_path": sandbox_policy.to_dict(),
        "retrieval_trace_path": {
            "query": None,
            "intent": "mixed",
            "candidate_counts": {"lexical": 0, "dense": 0, "graph": 0},
            "fused": [],
            "reranked": [],
            "selected_context": [],
            "dropped": [],
        },
        "retrieval_hits_path": {"results": []},
        "scheduler_candidate_set_path": {"candidates": []},
        "scheduler_decision_path": {
            "selected_candidate_id": None,
            "reason": "runtime scaffold created before campaign decision logging is attached",
        },
        "eval_results_path": {"results": []},
        "final_path": {"status": "in_progress"},
    }
    for key, value in payloads.items():
        path = paths[key]
        path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")

    for empty_path_key in ("events_ndjson_path", "approvals_path", "transcript_ndjson_path"):
        paths[empty_path_key].write_text("", encoding="utf-8")

    return paths


def _artifact_status_payload(
    metadata: Mapping[str, Any],
    *,
    task_status: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    metadata_json = dict(metadata.get("metadata_json") or {})
    evaluations = list(metadata_json.get("evaluations") or [])
    promotion_decision = metadata_json.get("promotion_decision")
    eval_payload = {
        "run_id": metadata.get("id"),
        "task_id": metadata.get("task_id"),
        "project_id": metadata.get("project_id"),
        "status": metadata.get("status"),
        "results": evaluations,
        "promotion_decision": promotion_decision,
    }
    final_payload = {
        "run_id": metadata.get("id"),
        "task_id": metadata.get("task_id"),
        "project_id": metadata.get("project_id"),
        "driver": metadata.get("driver"),
        "status": metadata.get("status"),
        "health": metadata.get("health"),
        "task_status": task_status,
        "finished_at": metadata.get("finished_at"),
        "exit_reason": metadata.get("exit_reason"),
        "promotion_decision": promotion_decision,
        "evaluations": evaluations,
        "tokens_in": metadata.get("tokens_in"),
        "tokens_out": metadata.get("tokens_out"),
        "cost_usd": metadata.get("cost_usd"),
    }
    return eval_payload, final_payload


def sync_runtime_status_artifacts(
    metadata: Mapping[str, Any],
    *,
    task_status: str | None = None,
) -> None:
    """Keep the v2.3 status artifacts aligned with the current run metadata."""
    eval_payload, final_payload = _artifact_status_payload(metadata, task_status=task_status)

    eval_results_path = metadata.get("eval_results_path")
    if eval_results_path:
        Path(str(eval_results_path)).write_text(
            json.dumps(eval_payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    final_path = metadata.get("final_path")
    if final_path:
        Path(str(final_path)).write_text(
            json.dumps(final_payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )


__all__ = [
    "SandboxPolicy",
    "default_sandbox_policy",
    "runtime_manifest",
    "sync_runtime_status_artifacts",
    "write_runtime_scaffold",
]

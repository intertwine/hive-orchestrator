"""Observe-console state loaders for Hive v2.3."""

from __future__ import annotations

import json
from pathlib import Path

from src.hive.control import portfolio_status, recommend_next_task
from src.hive.drivers.registry import normalize_driver_name
from src.hive.runtime.approvals import list_approvals
from src.hive.runs.engine import refresh_run_driver_state
from src.hive.scheduler.query import dependency_summary
from src.hive.store.campaigns import list_campaigns
from src.hive.store.events import load_events


def _run_metadata_paths(base_path: Path) -> list[Path]:
    runs_root = base_path / ".hive" / "runs"
    if not runs_root.exists():
        return []
    return sorted(runs_root.glob("run_*/metadata.json"))


def list_runs(
    base_path: Path,
    *,
    project_id: str | None = None,
    driver: str | None = None,
    health: str | None = None,
    campaign_id: str | None = None,
) -> list[dict]:
    """Return normalized runs for the observe console."""
    runs: list[dict] = []
    requested_driver = normalize_driver_name(driver)
    for metadata_path in _run_metadata_paths(base_path):
        run = refresh_run_driver_state(base_path, metadata_path.parent.name)
        if project_id and run.get("project_id") != project_id:
            continue
        if requested_driver and normalize_driver_name(str(run.get("driver") or "")) != requested_driver:
            continue
        if health and run.get("health") != health:
            continue
        if campaign_id and run.get("campaign_id") != campaign_id:
            continue
        runs.append(run)
    runs.sort(key=lambda item: item.get("started_at") or item["id"], reverse=True)
    return runs


def load_run_timeline(base_path: Path, run_id: str) -> list[dict]:
    """Load a per-run event timeline, falling back to the global audit log."""
    timeline_path = base_path / ".hive" / "runs" / run_id / "events.jsonl"
    if timeline_path.exists():
        return [
            json.loads(line)
            for line in timeline_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    return [event for event in load_events(base_path) if event.get("run_id") == run_id]


def _load_json(path_value: str | None) -> dict | list | None:
    if not path_value:
        return None
    path = Path(path_value)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _read_preview(path_value: str | None, *, limit: int = 12000) -> str | None:
    if not path_value:
        return None
    path = Path(path_value)
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")[:limit]


def _compiled_context_details(run_root: Path, context_manifest: dict) -> dict[str, object]:
    compiled_entries = list(context_manifest.get("entries") or [])
    memory_entries = [entry for entry in compiled_entries if entry.get("source_type") == "memory"]
    search_entries = [
        entry for entry in compiled_entries if entry.get("source_type") == "search-hit"
    ]
    skill_entries = [
        entry
        for entry in compiled_entries
        if entry.get("source_type") in {"skill", "skill-meta", "skills"}
    ]
    search_hits = _load_json(str(run_root / "context" / "compiled" / "search-hits.json")) or {}
    skills_manifest = (
        _load_json(str(run_root / "context" / "compiled" / "skills-manifest.json")) or {}
    )
    return {
        "compiled_entries": compiled_entries,
        "memory_entries": memory_entries,
        "search_entries": search_entries,
        "skill_entries": skill_entries,
        "search_hits": search_hits.get("results", []),
        "skills_manifest": skills_manifest,
    }


def _artifact_paths(run_root: Path, run: dict) -> dict[str, str | None]:
    return {
        "manifest": run.get("runtime_manifest_path"),
        "capability_snapshot": run.get("capability_snapshot_path"),
        "sandbox_policy": run.get("sandbox_policy_path"),
        "plan": run.get("plan_path"),
        "launch": run.get("launch_path"),
        "context_manifest": run.get("context_manifest_path"),
        "context_compiled_dir": run.get("context_compiled_dir"),
        "transcript": run.get("transcript_path"),
        "transcript_ndjson": run.get("transcript_ndjson_path"),
        "patch": run.get("workspace_patch_path") or run.get("patch_path"),
        "changed_files": run.get("workspace_changed_files_path"),
        "summary": run.get("summary_path"),
        "review": run.get("review_path"),
        "events": run.get("events_path"),
        "events_ndjson": run.get("events_ndjson_path"),
        "approvals": run.get("approvals_path"),
        "retrieval_trace": run.get("retrieval_trace_path"),
        "retrieval_hits": run.get("retrieval_hits_path"),
        "handoff_manifest": run.get("handoff_manifest_path"),
        "reroute_bundle": run.get("reroute_bundle_path"),
        "reroute_summary": run.get("reroute_summary_path"),
        "scheduler_candidate_set": run.get("scheduler_candidate_set_path"),
        "scheduler_decision": run.get("scheduler_decision_path"),
        "eval_results": run.get("eval_results_path"),
        "final": run.get("final_path"),
        "logs": run.get("logs_dir"),
        "run_brief": str(run_root / "context" / "compiled" / "run-brief.md"),
        "skills_manifest": str(run_root / "context" / "compiled" / "skills-manifest.json"),
        "search_hits": str(run_root / "context" / "compiled" / "search-hits.json"),
        "stdout": str(run_root / "logs" / "stdout.txt"),
        "stderr": str(run_root / "logs" / "stderr.txt"),
    }


def _artifact_preview(artifacts: dict[str, str | None], run: dict) -> dict[str, str | None]:
    return {
        "run_brief": _read_preview(artifacts["run_brief"]),
        "review_summary": _read_preview(run.get("summary_path")),
        "review_notes": _read_preview(run.get("review_path")),
        "diff": _read_preview(run.get("workspace_patch_path") or run.get("patch_path")),
        "stdout": _read_preview(artifacts["stdout"]),
        "stderr": _read_preview(artifacts["stderr"]),
    }


def build_inbox(base_path: Path) -> list[dict]:
    """Return typed attention items for the operator inbox."""
    items: list[dict] = []
    for run in list_runs(base_path):
        approvals = [
            approval
            for approval in list_approvals(base_path, run["id"])
            if approval.get("status") == "pending"
        ]
        for approval in approvals:
            items.append(
                {
                    "kind": "approval-request",
                    "priority": 0,
                    "run_id": run["id"],
                    "project_id": run.get("project_id"),
                    "approval_id": approval.get("approval_id"),
                    "title": str(approval.get("title") or f"Approval needed for {run['id']}"),
                    "reason": str(approval.get("summary") or "Driver requested approval."),
                }
            )
        status = str(run.get("status", ""))
        if status == "awaiting_review":
            items.append(
                {
                    "kind": "run-review",
                    "priority": 0,
                    "run_id": run["id"],
                    "project_id": run.get("project_id"),
                    "title": f"Review run {run['id']}",
                    "reason": "Evaluator results are ready and a promotion decision is pending.",
                }
            )
        elif status == "awaiting_input":
            items.append(
                {
                    "kind": "run-input",
                    "priority": 1,
                    "run_id": run["id"],
                    "project_id": run.get("project_id"),
                    "title": f"Attach driver for {run['id']}",
                    "reason": (
                        f"Driver {run.get('driver', 'unknown')} staged the run and is waiting."
                    ),
                }
            )
        elif status in {"escalated", "failed", "blocked"}:
            items.append(
                {
                    "kind": f"run-{status}",
                    "priority": 1,
                    "run_id": run["id"],
                    "project_id": run.get("project_id"),
                    "title": f"{status.title()} run {run['id']}",
                    "reason": run.get("exit_reason") or f"Run status is {status}.",
                }
            )
    for project in dependency_summary(base_path).get("projects", []):
        if project.get("effectively_blocked"):
            items.append(
                {
                    "kind": "project-blocked",
                    "priority": 2,
                    "project_id": project["project_id"],
                    "title": f"Blocked project {project['project_id']}",
                    "reason": "; ".join(project.get("blocking_reasons", [])),
                }
            )
    items.sort(key=lambda item: (item["priority"], item["title"]))
    return items


def build_home_view(base_path: Path) -> dict:
    """Answer the five core operator questions from one payload."""
    status = portfolio_status(base_path)
    deps = dependency_summary(base_path)
    inbox = build_inbox(base_path)
    accepted = [run for run in list_runs(base_path) if run.get("status") == "accepted"][:5]
    blocked_projects = [
        project for project in deps.get("projects", []) if project.get("effectively_blocked")
    ]
    return {
        "workspace": str(base_path),
        "recommended_next": recommend_next_task(base_path),
        "projects": status["projects"],
        "active_runs": status["active_runs"],
        "evaluating_runs": status["evaluating_runs"],
        "inbox": inbox,
        "blocked_projects": blocked_projects,
        "recent_accepts": accepted,
        "recent_events": status["recent_events"],
        "campaigns": [
            {
                "id": campaign.id,
                "title": campaign.title,
                "goal": campaign.goal,
                "status": campaign.status,
                "type": campaign.campaign_type,
                "driver": campaign.driver,
                "sandbox_profile": campaign.sandbox_profile or "default",
                "brief_cadence": campaign.brief_cadence,
                "lane_quotas": dict(campaign.lane_quotas),
                "project_ids": campaign.project_ids,
            }
            for campaign in list_campaigns(base_path)
        ],
    }


def load_run_detail(base_path: Path, run_id: str) -> dict:
    """Return the detail payload for a single run."""
    run = refresh_run_driver_state(base_path, run_id)
    run_root = base_path / ".hive" / "runs" / run_id
    timeline = load_run_timeline(base_path, run_id)
    context_manifest = _load_json(run.get("context_manifest_path")) or {}
    changed_files = _load_json(run.get("workspace_changed_files_path")) or {}
    driver_metadata = _load_json(run.get("driver_metadata_path")) or {}
    capability_snapshot = _load_json(run.get("capability_snapshot_path")) or {}
    sandbox_policy = _load_json(run.get("sandbox_policy_path")) or {}
    runtime_manifest = _load_json(run.get("runtime_manifest_path")) or {}
    retrieval_trace = _load_json(run.get("retrieval_trace_path")) or {}
    handoff_manifest = _load_json(run.get("handoff_manifest_path")) or {}
    reroute_bundle = _load_json(run.get("reroute_bundle_path")) or {}
    scheduler_decision = _load_json(run.get("scheduler_decision_path")) or {}
    eval_results = _load_json(run.get("eval_results_path")) or {}
    final_state = _load_json(run.get("final_path")) or {}
    context_details = _compiled_context_details(run_root, context_manifest)
    artifacts = _artifact_paths(run_root, run)
    steering_history = [
        event for event in timeline if str(event.get("type", "")).startswith("steering.")
    ]
    promotion_decision = run.get("metadata_json", {}).get("promotion_decision")
    approvals = list_approvals(base_path, run_id)
    return {
        "run": run,
        "timeline": timeline,
        "context_manifest": context_manifest,
        "changed_files": changed_files,
        "context_entries": context_details["compiled_entries"],
        "memory_entries": context_details["memory_entries"],
        "search_entries": context_details["search_entries"],
        "skill_entries": context_details["skill_entries"],
        "inspector": {
            "memory_entries": context_details["memory_entries"],
            "skill_entries": context_details["skill_entries"],
            "search_entries": context_details["search_entries"],
            "search_hits": context_details["search_hits"],
            "skills_manifest": context_details["skills_manifest"],
            "capability_snapshot": capability_snapshot,
            "sandbox_policy": sandbox_policy,
            "runtime_manifest": runtime_manifest,
            "retrieval_trace": retrieval_trace,
            "handoff_manifest": handoff_manifest,
            "reroute_bundle": reroute_bundle,
            "scheduler_decision": scheduler_decision,
            "outputs": context_manifest.get("outputs", []),
        },
        "steering_history": steering_history,
        "approvals": approvals,
        "artifacts": artifacts,
        "driver_metadata": driver_metadata,
        "capability_snapshot": capability_snapshot,
        "sandbox_policy": sandbox_policy,
        "runtime_manifest": runtime_manifest,
        "retrieval_trace": retrieval_trace,
        "handoff_manifest": handoff_manifest,
        "reroute_bundle": reroute_bundle,
        "scheduler_decision": scheduler_decision,
        "eval_results": eval_results,
        "final_state": final_state,
        "promotion_decision": promotion_decision,
        "artifact_preview": _artifact_preview(artifacts, run),
        "evaluations": run.get("metadata_json", {}).get("evaluations", []),
    }

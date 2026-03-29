"""Observe-console state loaders for Hive v2.3."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.hive.control import portfolio_status, recommend_next_task
from src.hive.drivers.registry import normalize_driver_name
from src.hive.runtime.approvals import list_approvals
from src.hive.runs.engine import refresh_run_driver_state
from src.hive.scheduler.query import dependency_summary
from src.hive.store.campaigns import list_campaigns
from src.hive.store.events import load_events
from src.hive.trajectory.writer import load_trajectory


def _run_metadata_paths(base_path: Path) -> list[Path]:
    runs_root = base_path / ".hive" / "runs"
    if not runs_root.exists():
        return []
    return sorted(runs_root.glob("run_*/metadata.json"))


def _delegate_manifest_paths(base_path: Path) -> list[Path]:
    delegates_root = base_path / ".hive" / "delegates"
    if not delegates_root.exists():
        return []
    return sorted(delegates_root.glob("*/manifest.json"))


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
    for metadata_path in _run_metadata_paths(base_path):
        run = refresh_run_driver_state(base_path, metadata_path.parent.name)
        runs.append(run)
    runs.extend(
        _delegate_entries(
            base_path,
            project_id=project_id,
            driver=driver,
            health=health,
            campaign_id=campaign_id,
        )
    )
    requested_driver = normalize_driver_name(driver)
    filtered: list[dict] = []
    for run in runs:
        if project_id and run.get("project_id") != project_id:
            continue
        if (
            requested_driver
            and normalize_driver_name(str(run.get("driver") or "")) != requested_driver
        ):
            continue
        if health and run.get("health") != health:
            continue
        if campaign_id and run.get("campaign_id") != campaign_id:
            continue
        filtered.append(run)
    filtered.sort(key=lambda item: item.get("started_at") or item["id"], reverse=True)
    return filtered


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


def _load_jsonl_records(path_value: str | Path | None) -> list[dict[str, Any]]:
    if not path_value:
        return []
    path = Path(path_value)
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _delegate_status(manifest: dict[str, Any], final_state: dict[str, Any]) -> str:
    return str(final_state.get("status") or manifest.get("status") or "attached")


def _delegate_health(status: str) -> str:
    if status in {"attached", "active"}:
        return "healthy"
    if status in {"failed", "blocked"}:
        return status
    return "idle"


def _delegate_task_title(manifest: dict[str, Any]) -> str:
    task_id = str(manifest.get("task_id") or "").strip()
    if task_id:
        return task_id
    adapter_name = str(manifest.get("adapter_name") or "delegate")
    native_session_ref = str(manifest.get("native_session_ref") or "").strip()
    if native_session_ref:
        return f"{adapter_name} session {native_session_ref}"
    return f"{adapter_name} delegate session"


def _delegate_sandbox_owner(manifest: dict[str, Any]) -> str:
    metadata = dict(manifest.get("metadata") or {})
    if metadata.get("sandbox_owner"):
        return str(metadata["sandbox_owner"])
    return str(manifest.get("adapter_name") or "external")


def _delegate_entry(manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    session_dir = manifest_path.parent
    final_state = _load_json(str(session_dir / "final.json")) or {}
    delegate_session_id = str(
        manifest.get("delegate_session_id") or manifest.get("session_id") or session_dir.name
    )
    status = _delegate_status(manifest, final_state)
    sandbox_owner = _delegate_sandbox_owner(manifest)
    return {
        "id": delegate_session_id,
        "entry_kind": "delegate_session",
        "driver": str(manifest.get("adapter_name") or "delegate"),
        "driver_handle": str(manifest.get("native_session_ref") or "") or None,
        "project_id": manifest.get("project_id"),
        "task_id": manifest.get("task_id"),
        "campaign_id": None,
        "status": status,
        "health": _delegate_health(status),
        "started_at": manifest.get("attached_at"),
        "finished_at": final_state.get("detached_at") or final_state.get("completed_at"),
        "metadata_json": {
            "task_title": _delegate_task_title(manifest),
            "entry_kind": "delegate_session",
            "adapter_family": manifest.get("adapter_family"),
            "native_session_ref": manifest.get("native_session_ref"),
            "governance_mode": manifest.get("governance_mode"),
            "integration_level": manifest.get("integration_level"),
            "sandbox_owner": sandbox_owner,
        },
        "delegate_session_id": delegate_session_id,
        "native_session_ref": manifest.get("native_session_ref"),
        "adapter_family": manifest.get("adapter_family"),
        "integration_level": manifest.get("integration_level"),
        "governance_mode": manifest.get("governance_mode"),
        "sandbox_owner": sandbox_owner,
        "capability_snapshot_path": str(session_dir / "capability-snapshot.json"),
        "trajectory_path": str(session_dir / "trajectory.jsonl"),
        "steering_path": str(session_dir / "steering.ndjson"),
        "final_path": str(session_dir / "final.json"),
        "manifest_path": str(manifest_path),
    }


def _delegate_entries(
    base_path: Path,
    *,
    project_id: str | None = None,
    driver: str | None = None,
    health: str | None = None,
    campaign_id: str | None = None,
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    requested_driver = normalize_driver_name(driver)
    for manifest_path in _delegate_manifest_paths(base_path):
        entry = _delegate_entry(manifest_path)
        if project_id and entry.get("project_id") != project_id:
            continue
        if campaign_id:
            continue
        if (
            requested_driver
            and normalize_driver_name(str(entry.get("driver") or "")) != requested_driver
        ):
            continue
        if health and entry.get("health") != health:
            continue
        entries.append(entry)
    return entries


def _run_native_session_handle(run: dict[str, Any]) -> str | None:
    metadata_json = dict(run.get("metadata_json") or {})
    driver_status = dict(metadata_json.get("driver_status") or {})
    session = dict(driver_status.get("session") or {})
    native_session_ref = str(session.get("native_session_ref") or "").strip()
    if native_session_ref:
        return native_session_ref
    driver_handle = str(run.get("driver_handle") or "").strip()
    return driver_handle or None


def _run_sandbox_owner(run: dict[str, Any], governance_mode: str) -> str:
    metadata_json = dict(run.get("metadata_json") or {})
    driver_status = dict(metadata_json.get("driver_status") or {})
    session = dict(driver_status.get("session") or {})
    sandbox_owner = str(session.get("sandbox_owner") or "").strip()
    if sandbox_owner:
        return sandbox_owner
    return "hive" if governance_mode == "governed" else str(run.get("driver") or "external")


def _delegate_steering_history(session_dir: Path) -> list[dict[str, Any]]:
    action_to_type = {
        "pause": "steering.pause",
        "resume": "steering.resume",
        "note": "steering.note_added",
        "cancel": "steering.cancel",
        "reroute": "steering.rerouted",
        "finish": "steering.finish",
    }
    records = _load_jsonl_records(session_dir / "steering.ndjson")
    history: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        action = str(record.get("action") or record.get("action_type") or "note")
        history.append(
            {
                "event_id": f"steering-{index}",
                "type": action_to_type.get(action, f"steering.{action}"),
                "ts": str(record.get("ts") or ""),
                "payload": record,
            }
        )
    return history


def _delegate_timeline(
    base_path: Path,
    delegate_session_id: str,
    steering_history: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    timeline = [
        {
            "event_id": f"trajectory-{event.seq}",
            "type": f"trajectory.{event.kind}",
            "ts": event.ts,
            "payload": event.to_dict(),
        }
        for event in load_trajectory(base_path, delegate_session_id=delegate_session_id)
    ]
    timeline.extend(steering_history)
    timeline.sort(key=lambda item: (str(item.get("ts") or ""), str(item.get("event_id") or "")))
    return timeline


def _load_delegate_detail(base_path: Path, delegate_session_id: str) -> dict[str, Any]:
    session_dir = base_path / ".hive" / "delegates" / delegate_session_id
    manifest_path = session_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Run not found: {delegate_session_id}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    capability_snapshot = _load_json(str(session_dir / "capability-snapshot.json")) or {}
    final_state = _load_json(str(session_dir / "final.json")) or {}
    steering_history = _delegate_steering_history(session_dir)
    trajectory = [
        event.to_dict()
        for event in load_trajectory(base_path, delegate_session_id=delegate_session_id)
    ]
    sandbox_owner = _delegate_sandbox_owner(manifest)
    return {
        "run": _delegate_entry(manifest_path),
        "detail_kind": "delegate_session",
        "timeline": _delegate_timeline(base_path, delegate_session_id, steering_history),
        "context_manifest": {},
        "changed_files": {},
        "context_entries": [],
        "memory_entries": [],
        "search_entries": [],
        "skill_entries": [],
        "inspector": {
            "memory_entries": [],
            "skill_entries": [],
            "search_entries": [],
            "search_hits": [],
            "skills_manifest": {},
            "capability_snapshot": capability_snapshot,
            "sandbox_policy": {},
            "runtime_manifest": {},
            "retrieval_trace": {},
            "handoff_manifest": {},
            "reroute_bundle": {},
            "scheduler_decision": {},
            "outputs": [],
        },
        "steering_history": steering_history,
        "approvals": [],
        "artifacts": {
            "manifest": str(manifest_path),
            "capability_snapshot": str(session_dir / "capability-snapshot.json"),
            "trajectory": str(session_dir / "trajectory.jsonl"),
            "steering": str(session_dir / "steering.ndjson"),
            "final": str(session_dir / "final.json"),
        },
        "driver_metadata": {},
        "capability_snapshot": capability_snapshot,
        "sandbox_policy": {},
        "runtime_manifest": {},
        "retrieval_trace": {},
        "handoff_manifest": {},
        "reroute_bundle": {},
        "scheduler_decision": {},
        "eval_results": {},
        "final_state": final_state,
        "promotion_decision": {},
        "artifact_preview": {
            "trajectory": _read_preview(str(session_dir / "trajectory.jsonl")),
            "steering": _read_preview(str(session_dir / "steering.ndjson")),
        },
        "evaluations": [],
        "harness": str(manifest.get("adapter_name") or capability_snapshot.get("driver") or ""),
        "native_session_handle": str(manifest.get("native_session_ref") or "") or None,
        "sandbox_owner": sandbox_owner,
        "governance_mode": str(
            manifest.get("governance_mode")
            or capability_snapshot.get("governance_mode")
            or "advisory"
        ),
        "integration_level": str(
            manifest.get("integration_level")
            or capability_snapshot.get("integration_level")
            or "attach"
        ),
        "adapter_family": str(
            manifest.get("adapter_family")
            or capability_snapshot.get("adapter_family")
            or "delegate_gateway"
        ),
        "trajectory": trajectory,
    }


def _compiled_context_details(
    run_root: Path, context_manifest: dict
) -> dict[str, object]:
    compiled_entries = list(context_manifest.get("entries") or [])
    memory_entries = [
        entry for entry in compiled_entries if entry.get("source_type") == "memory"
    ]
    search_entries = [
        entry for entry in compiled_entries if entry.get("source_type") == "search-hit"
    ]
    skill_entries = [
        entry
        for entry in compiled_entries
        if entry.get("source_type") in {"skill", "skill-meta", "skills"}
    ]
    search_hits = (
        _load_json(str(run_root / "context" / "compiled" / "search-hits.json")) or {}
    )
    skills_manifest = (
        _load_json(str(run_root / "context" / "compiled" / "skills-manifest.json"))
        or {}
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
        "trajectory": run.get("trajectory_path"),
        "steering": run.get("steering_path"),
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
        "skills_manifest": str(
            run_root / "context" / "compiled" / "skills-manifest.json"
        ),
        "search_hits": str(run_root / "context" / "compiled" / "search-hits.json"),
        "stdout": str(run_root / "logs" / "stdout.txt"),
        "stderr": str(run_root / "logs" / "stderr.txt"),
    }


def _artifact_preview(
    artifacts: dict[str, str | None], run: dict
) -> dict[str, str | None]:
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
        if run.get("entry_kind") == "delegate_session":
            continue
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
                    "title": str(
                        approval.get("title") or f"Approval needed for {run['id']}"
                    ),
                    "reason": str(
                        approval.get("summary") or "Driver requested approval."
                    ),
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
    active_runs = list(status["active_runs"]) + [
        run for run in _delegate_entries(base_path) if run.get("status") == "attached"
    ]
    active_runs.sort(key=lambda item: item.get("started_at") or item["id"], reverse=True)
    accepted = [run for run in list_runs(base_path) if run.get("status") == "accepted"][
        :5
    ]
    blocked_projects = [
        project
        for project in deps.get("projects", [])
        if project.get("effectively_blocked")
    ]
    return {
        "workspace": str(base_path),
        "recommended_next": recommend_next_task(base_path),
        "projects": status["projects"],
        "active_runs": active_runs,
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
    try:
        run = refresh_run_driver_state(base_path, run_id)
    except FileNotFoundError:
        return _load_delegate_detail(base_path, run_id)
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
    trajectory = [event.to_dict() for event in load_trajectory(base_path, run_id=run_id)]
    steering_history = [
        event
        for event in timeline
        if str(event.get("type", "")).startswith("steering.")
    ]
    promotion_decision = run.get("metadata_json", {}).get("promotion_decision")
    approvals = list_approvals(base_path, run_id)
    harness = str(capability_snapshot.get("driver") or run.get("driver") or "")
    governance_mode = str(capability_snapshot.get("governance_mode", "governed"))
    integration_level = str(capability_snapshot.get("integration_level", "managed"))
    adapter_family = str(capability_snapshot.get("adapter_family", "legacy_driver"))
    return {
        "run": run,
        "detail_kind": "run",
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
        "harness": harness,
        "native_session_handle": _run_native_session_handle(run),
        "sandbox_owner": _run_sandbox_owner(run, governance_mode),
        "trajectory": trajectory,
        # v2.4 adapter-family truth — extracted from capability snapshot with safe defaults.
        "governance_mode": governance_mode,
        "integration_level": integration_level,
        "adapter_family": adapter_family,
    }

"""Observe-console state loaders for Agent Hive."""

from __future__ import annotations

from collections import Counter
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
from src.hive.store.projects import discover_projects
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
    runs.extend(_delegate_entries(base_path))
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
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for manifest_path in _delegate_manifest_paths(base_path):
        entry = _delegate_entry(manifest_path)
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


def _changed_path_list(changed_files: Any) -> list[str]:
    if isinstance(changed_files, dict):
        touched_paths = changed_files.get("touched_paths")
        if isinstance(touched_paths, list):
            return sorted(str(path) for path in touched_paths if str(path).strip())
    return []


def _evaluation_summary(evaluations: Any) -> dict[str, Any]:
    if not isinstance(evaluations, list):
        return {"total": 0, "by_status": {}}
    status_counts = Counter(
        str(item.get("status") or "unknown")
        for item in evaluations
        if isinstance(item, dict)
    )
    return {
        "total": len(evaluations),
        "by_status": dict(sorted(status_counts.items())),
    }


def _comparison_snapshot(base_path: Path, run: dict[str, Any]) -> dict[str, Any]:
    run_id = str(run.get("id") or "")
    run_root = base_path / ".hive" / "runs" / run_id
    changed_files = _load_json(run.get("workspace_changed_files_path")) or {}
    evaluations = run.get("metadata_json", {}).get("evaluations", [])
    return {
        "run_id": run_id,
        "title": _run_title(run),
        "project_id": str(run.get("project_id") or "") or None,
        "driver": str(run.get("driver") or ""),
        "status": str(run.get("status") or ""),
        "health": str(run.get("health") or ""),
        "started_at": str(run.get("started_at") or ""),
        "finished_at": str(run.get("finished_at") or run.get("updated_at") or ""),
        "promotion_decision": run.get("metadata_json", {}).get("promotion_decision") or {},
        "changed_paths": _changed_path_list(changed_files),
        "changed_files": changed_files,
        "evaluation_summary": _evaluation_summary(evaluations),
        "evaluations": evaluations,
        "artifact_preview": _artifact_preview(_artifact_paths(run_root, run), run),
    }


def load_run_comparison(base_path: Path, run_id: str) -> dict[str, Any]:
    """Return a review-oriented comparison between a run and the latest accepted sibling."""
    run = refresh_run_driver_state(base_path, run_id)
    project_id = str(run.get("project_id") or "") or None
    current = _comparison_snapshot(base_path, run)
    accepted_runs = [
        candidate
        for candidate in list_runs(base_path, project_id=project_id)
        if candidate.get("status") == "accepted"
        and candidate.get("id") != run_id
        and candidate.get("entry_kind") != "delegate_session"
    ]
    accepted_runs.sort(
        key=lambda candidate: (
            str(candidate.get("finished_at") or ""),
            str(candidate.get("updated_at") or ""),
            str(candidate.get("started_at") or ""),
            str(candidate.get("id") or ""),
        ),
        reverse=True,
    )
    baseline = _comparison_snapshot(base_path, accepted_runs[0]) if accepted_runs else None
    current_paths = set(current["changed_paths"])
    baseline_paths = set(baseline["changed_paths"]) if baseline else set()
    return {
        "current": current,
        "baseline": baseline,
        "diff": {
            "current_only": sorted(current_paths - baseline_paths),
            "baseline_only": sorted(baseline_paths - current_paths),
            "shared": sorted(current_paths & baseline_paths),
        },
        "summary": {
            "has_baseline": baseline is not None,
            "baseline_label": baseline["title"] if baseline else "No accepted baseline yet.",
            "current_label": current["title"],
        },
    }


def _delegate_inbox_note_visible(record: dict[str, Any]) -> bool:
    if bool(
        record.get("inbox_visible")
        or record.get("surface_to_inbox")
        or record.get("raise_in_inbox")
    ):
        return True
    direction = str(record.get("direction") or record.get("flow") or "").strip().lower()
    if direction in {"inbound", "from_delegate", "delegate_to_hive", "native_to_hive"}:
        return True
    source = str(
        record.get("source")
        or record.get("origin")
        or record.get("author")
        or record.get("actor")
        or ""
    ).strip().lower()
    return source in {
        "assistant",
        "delegate",
        "harness",
        "hermes",
        "native",
        "openclaw",
        "session",
    }


def _delegate_inbox_note_text(record: dict[str, Any]) -> str:
    note = str(record.get("note") or "").strip()
    if note:
        return note
    payload = record.get("payload")
    if isinstance(payload, dict):
        return str(
            payload.get("note")
            or payload.get("message")
            or payload.get("summary")
            or ""
        ).strip()
    return ""


def _delegate_inbox_label(run: dict[str, Any]) -> str:
    metadata_json = dict(run.get("metadata_json") or {})
    task_title = str(metadata_json.get("task_title") or "").strip()
    if task_title:
        return task_title
    native_session_ref = str(
        run.get("native_session_ref") or run.get("driver_handle") or ""
    ).strip()
    harness = str(run.get("driver") or "delegate")
    if native_session_ref:
        return f"{harness} session {native_session_ref}"
    return f"{harness} attached session"


def _delegate_status_reason(final_state: dict[str, Any], status: str) -> str:
    for key in ("reason", "message", "error", "summary"):
        reason = str(final_state.get(key) or "").strip()
        if reason:
            return reason
    return f"Attached advisory session is {status}."


def _delegate_inbox_items(base_path: Path, run: dict[str, Any]) -> list[dict[str, Any]]:
    delegate_session_id = str(
        run.get("delegate_session_id") or run.get("id") or ""
    ).strip()
    if not delegate_session_id:
        return []
    harness = str(run.get("driver") or "delegate")
    native_session_ref = str(
        run.get("native_session_ref") or run.get("driver_handle") or ""
    ).strip()
    final_state = _load_json(str(run.get("final_path") or "")) or {}
    label = _delegate_inbox_label(run)
    items: list[dict[str, Any]] = []

    status = str(run.get("status") or "")
    if status in {"escalated", "failed", "blocked"}:
        items.append(
            {
                "kind": f"delegate-{status}",
                "priority": 1,
                "run_id": run["id"],
                "project_id": run.get("project_id"),
                "delegate_session_id": delegate_session_id,
                "native_session_ref": native_session_ref or None,
                "title": f"{status.title()} {label}",
                "reason": _delegate_status_reason(final_state, status),
            }
        )

    seen_notes: set[tuple[str, str]] = set()
    for record in _load_jsonl_records(run.get("steering_path")):
        if not _delegate_inbox_note_visible(record):
            continue
        note = _delegate_inbox_note_text(record)
        if not note:
            continue
        title = str(record.get("title") or f"Note from {label}")
        note_key = (title, note)
        if note_key in seen_notes:
            continue
        seen_notes.add(note_key)
        items.append(
            {
                "kind": "delegate-note",
                "priority": 1,
                "run_id": run["id"],
                "project_id": run.get("project_id"),
                "delegate_session_id": delegate_session_id,
                "native_session_ref": native_session_ref or None,
                "title": title,
                "reason": note,
            }
        )

    latest_approval: dict[str, Any] | None = None
    latest_error: dict[str, Any] | None = None
    for event in reversed(load_trajectory(base_path, delegate_session_id=delegate_session_id)):
        if latest_approval is None and event.kind == "approval_request":
            latest_approval = event.to_dict()
        elif latest_error is None and event.kind == "error":
            latest_error = event.to_dict()
        if latest_approval is not None and latest_error is not None:
            break

    if latest_approval is not None:
        payload = dict(latest_approval.get("payload") or {})
        items.append(
            {
                "kind": "delegate-approval",
                "priority": 0,
                "run_id": run["id"],
                "project_id": run.get("project_id"),
                "delegate_session_id": delegate_session_id,
                "native_session_ref": native_session_ref or None,
                "title": f"Approval requested by {label}",
                "reason": str(
                    payload.get("summary")
                    or payload.get("message")
                    or payload.get("title")
                    or "Attached advisory session requested approval."
                ),
            }
        )

    if latest_error is not None:
        payload = dict(latest_error.get("payload") or {})
        items.append(
            {
                "kind": "delegate-error",
                "priority": 1,
                "run_id": run["id"],
                "project_id": run.get("project_id"),
                "delegate_session_id": delegate_session_id,
                "native_session_ref": native_session_ref or None,
                "title": f"Error in {label}",
                "reason": str(
                    payload.get("message")
                    or payload.get("error")
                    or payload.get("summary")
                    or "Attached advisory session emitted an error."
                ),
            }
        )

    return items


SEVERITY_RANK = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "info": 4,
}

DECISION_LABELS = {
    "approval": "Approval",
    "review": "Review",
    "input": "Input",
    "failure": "Failure",
    "blocker": "Blocker",
    "delegate": "Delegate",
    "informational": "Informational",
}


def _project_titles(base_path: Path) -> dict[str, str]:
    return {
        project.id: str(project.title or project.slug or project.id)
        for project in discover_projects(base_path)
    }


def _run_title(run: dict[str, Any]) -> str:
    metadata = run.get("metadata_json") or {}
    if isinstance(metadata, dict):
        title = str(metadata.get("task_title") or "").strip()
        if title:
            return title
    return str(run.get("id") or "Run")


def _attention_decision_type(kind: str) -> str:
    if kind in {"approval-request", "delegate-approval"}:
        return "approval"
    if kind in {"run-review", "delegate-blocked"}:
        return "review"
    if kind == "run-input":
        return "input"
    if kind in {"run-escalated", "run-failed", "run-blocked", "delegate-error"}:
        return "failure"
    if kind == "project-blocked":
        return "blocker"
    if kind == "delegate-note":
        return "delegate"
    return "informational"


def _attention_severity(kind: str, priority: int) -> str:
    if kind in {"approval-request", "run-review", "delegate-approval"}:
        return "critical"
    if kind in {"run-escalated", "run-failed", "run-blocked", "delegate-error"}:
        return "high"
    if kind in {"run-input", "delegate-blocked", "project-blocked"}:
        return "medium"
    if kind == "delegate-note":
        return "low"
    if priority <= 0:
        return "critical"
    if priority == 1:
        return "high"
    if priority == 2:
        return "medium"
    return "info"


def _attention_explanation(kind: str, *, run_label: str, project_label: str) -> str:
    if kind == "approval-request":
        return f"{run_label} is waiting on an explicit operator approval before it can continue."
    if kind == "run-review":
        return f"{run_label} finished evaluation and needs a promotion decision."
    if kind == "run-input":
        return f"{run_label} is staged and waiting for a live operator input or attach decision."
    if kind in {"run-escalated", "run-failed", "run-blocked"}:
        return f"{run_label} surfaced a run-level exception that needs operator attention."
    if kind == "project-blocked":
        return f"{project_label} is effectively blocked by unresolved dependencies."
    if kind == "delegate-blocked":
        return f"{run_label} represents an attached delegate session that explicitly asked for review."
    if kind == "delegate-note":
        return f"{run_label} emitted a delegate note marked as inbox-worthy."
    if kind == "delegate-approval":
        return f"{run_label} surfaced an approval request from an attached delegate harness."
    if kind == "delegate-error":
        return f"{run_label} emitted an attached delegate error that could affect delivery."
    return f"{run_label} surfaced an operator notification."


def _attention_ignore_impact(kind: str, *, run_label: str, project_label: str) -> str:
    if kind in {"approval-request", "delegate-approval"}:
        return f"Ignoring this leaves {run_label} blocked until someone approves or rejects it."
    if kind == "run-review":
        return f"Ignoring this delays promotion or rejection for {run_label}."
    if kind == "run-input":
        return f"Ignoring this leaves {run_label} waiting in a staged state."
    if kind in {"run-escalated", "run-failed", "run-blocked", "delegate-error"}:
        return f"Ignoring this risks leaving {run_label} in an unhealthy or stalled state."
    if kind == "project-blocked":
        return f"Ignoring this leaves {project_label} blocked and can hide downstream delivery risk."
    if kind == "delegate-note":
        return f"Ignoring this may hide context the delegate session considered important."
    if kind == "delegate-blocked":
        return f"Ignoring this keeps the delegate session waiting without a human review path."
    return "Ignoring this removes it from view but does not change canonical Hive state."


def _attention_available_actions(kind: str) -> list[str]:
    actions = ["dismiss", "snooze", "assign"]
    if kind in {
        "approval-request",
        "run-review",
        "run-input",
        "run-escalated",
        "run-failed",
        "run-blocked",
        "project-blocked",
        "delegate-blocked",
        "delegate-error",
    }:
        return ["resolve", *actions]
    return actions


def _attention_deep_link(kind: str, *, run_id: str | None, project_id: str | None) -> str | None:
    if run_id:
        return f"/runs/{run_id}"
    if kind == "project-blocked" and project_id:
        return f"/projects/{project_id}"
    return None


def _attention_item(
    *,
    kind: str,
    priority: int,
    title: str,
    reason: str,
    project_id: str | None = None,
    project_label: str | None = None,
    run_id: str | None = None,
    run_label: str | None = None,
    approval_id: str | None = None,
    delegate_session_id: str | None = None,
    native_session_ref: str | None = None,
    occurred_at: str | None = None,
    source: str = "workspace",
    notification_tier: str = "actionable",
) -> dict[str, Any]:
    severity = _attention_severity(kind, priority)
    decision_type = _attention_decision_type(kind)
    decision_label = DECISION_LABELS.get(decision_type, decision_type.replace("-", " ").title())
    normalized_run_label = str(run_label or run_id or "This run")
    normalized_project_label = str(project_label or project_id or "This project")
    identifier_parts = [
        kind,
        run_id or "",
        approval_id or "",
        delegate_session_id or "",
        native_session_ref or "",
        occurred_at or "",
        title,
    ]
    item_id = "::".join(part for part in identifier_parts if part)
    return {
        "id": item_id,
        "kind": kind,
        "priority": priority,
        "severity": severity,
        "severity_rank": SEVERITY_RANK[severity],
        "severity_label": severity.title(),
        "decision_type": decision_type,
        "decision_label": decision_label,
        "group_key": f"{severity}:{decision_type}",
        "group_label": f"{severity.title()} · {decision_label}",
        "title": title,
        "summary": reason,
        "reason": reason,
        "why_visible": _attention_explanation(
            kind,
            run_label=normalized_run_label,
            project_label=normalized_project_label,
        ),
        "ignore_impact": _attention_ignore_impact(
            kind,
            run_label=normalized_run_label,
            project_label=normalized_project_label,
        ),
        "notification_tier": notification_tier,
        "source": source,
        "status": "pending",
        "bulk_actions": _attention_available_actions(kind),
        "deep_link": _attention_deep_link(kind, run_id=run_id, project_id=project_id),
        "occurred_at": occurred_at,
        "project_id": project_id,
        "project_label": normalized_project_label,
        "run_id": run_id,
        "run_label": normalized_run_label if run_id else None,
        "approval_id": approval_id,
        "delegate_session_id": delegate_session_id,
        "native_session_ref": native_session_ref,
    }


def _sort_attention_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(items, key=lambda item: str(item.get("title") or ""))
    ordered = sorted(ordered, key=lambda item: str(item.get("occurred_at") or ""), reverse=True)
    return sorted(
        ordered,
        key=lambda item: (
            int(item.get("severity_rank", item.get("priority", 99))),
            not bool(item.get("occurred_at")),
        ),
    )


def load_attention_context(base_path: Path) -> dict[str, Any]:
    """Load shared attention inputs once for inbox, notifications, and activity views."""
    return {
        "project_titles": _project_titles(base_path),
        "recent_events": portfolio_status(base_path).get("recent_events", []),
        "runs": list_runs(base_path),
    }


def summarize_attention_items(items: list[dict[str, Any]]) -> dict[str, Any]:
    severity_counts = Counter(str(item.get("severity") or "info") for item in items)
    decision_counts = Counter(str(item.get("decision_type") or "informational") for item in items)
    tier_counts = Counter(str(item.get("notification_tier") or "actionable") for item in items)
    return {
        "total": len(items),
        "by_severity": dict(sorted(severity_counts.items(), key=lambda entry: SEVERITY_RANK.get(entry[0], 99))),
        "by_decision_type": dict(sorted(decision_counts.items())),
        "by_notification_tier": dict(sorted(tier_counts.items())),
    }


def build_inbox(
    base_path: Path,
    *,
    project_titles: dict[str, str] | None = None,
    runs: list[dict[str, Any]] | None = None,
) -> list[dict]:
    """Return typed attention items for the operator inbox."""
    project_titles = project_titles if project_titles is not None else _project_titles(base_path)
    runs = runs if runs is not None else list_runs(base_path)
    items: list[dict] = []
    for run in runs:
        if run.get("entry_kind") == "delegate_session":
            for item in _delegate_inbox_items(base_path, run):
                items.append(
                    _attention_item(
                        kind=str(item.get("kind") or "delegate-note"),
                        priority=int(item.get("priority") or 0),
                        title=str(item.get("title") or "Delegate attention item"),
                        reason=str(item.get("reason") or "Attached delegate session needs attention."),
                        project_id=str(item.get("project_id") or "") or None,
                        project_label=project_titles.get(str(item.get("project_id") or "")),
                        run_id=str(item.get("run_id") or "") or None,
                        run_label=str(item.get("title") or item.get("run_id") or "Delegate session"),
                        delegate_session_id=str(item.get("delegate_session_id") or "") or None,
                        native_session_ref=str(item.get("native_session_ref") or "") or None,
                        source="delegate",
                    )
                )
            continue
        run_label = _run_title(run)
        project_id = str(run.get("project_id") or "") or None
        approvals = [
            approval
            for approval in list_approvals(base_path, run["id"])
            if approval.get("status") == "pending"
        ]
        for approval in approvals:
            items.append(
                _attention_item(
                    kind="approval-request",
                    priority=0,
                    run_id=str(run["id"]),
                    run_label=run_label,
                    project_id=project_id,
                    project_label=project_titles.get(project_id or ""),
                    approval_id=str(approval.get("approval_id") or "") or None,
                    title=str(approval.get("title") or f"Approve next step for {run_label}"),
                    reason=str(approval.get("summary") or "Driver requested approval."),
                    occurred_at=str(approval.get("requested_at") or approval.get("created_at") or ""),
                    source="approval",
                )
            )
        status = str(run.get("status", ""))
        if status == "awaiting_review":
            items.append(
                _attention_item(
                    kind="run-review",
                    priority=0,
                    run_id=str(run["id"]),
                    run_label=run_label,
                    project_id=project_id,
                    project_label=project_titles.get(project_id or ""),
                    title=f"Review {run_label}",
                    reason="Evaluator results are ready and a promotion decision is pending.",
                    occurred_at=str(run.get("updated_at") or run.get("started_at") or ""),
                    source="run",
                )
            )
        elif status == "awaiting_input":
            items.append(
                _attention_item(
                    kind="run-input",
                    priority=1,
                    run_id=str(run["id"]),
                    run_label=run_label,
                    project_id=project_id,
                    project_label=project_titles.get(project_id or ""),
                    title=f"Attach live driver for {run_label}",
                    reason=(
                        f"Driver {run.get('driver', 'unknown')} staged the run and is waiting."
                    ),
                    occurred_at=str(run.get("updated_at") or run.get("started_at") or ""),
                    source="run",
                )
            )
        elif status in {"escalated", "failed", "blocked"}:
            items.append(
                _attention_item(
                    kind=f"run-{status}",
                    priority=1,
                    run_id=str(run["id"]),
                    run_label=run_label,
                    project_id=project_id,
                    project_label=project_titles.get(project_id or ""),
                    title=f"{status.title()} {run_label}",
                    reason=str(run.get("exit_reason") or f"Run status is {status}."),
                    occurred_at=str(run.get("updated_at") or run.get("finished_at") or run.get("started_at") or ""),
                    source="run",
                )
            )
    for project in dependency_summary(base_path).get("projects", []):
        if project.get("effectively_blocked"):
            items.append(
                _attention_item(
                    kind="project-blocked",
                    priority=2,
                    project_id=str(project["project_id"]),
                    project_label=project_titles.get(str(project["project_id"]), str(project["project_id"])),
                    title=f"Blocked {project_titles.get(str(project['project_id']), str(project['project_id']))}",
                    reason="; ".join(project.get("blocking_reasons", [])),
                    source="project",
                )
            )
    return _sort_attention_items(items)


def build_notifications(
    base_path: Path,
    *,
    inbox_items: list[dict[str, Any]] | None = None,
    project_titles: dict[str, str] | None = None,
    recent_events: list[dict[str, Any]] | None = None,
    runs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return a persistent notification-center payload backed by the same event model."""
    project_titles = project_titles if project_titles is not None else _project_titles(base_path)
    runs = runs if runs is not None else list_runs(base_path)
    recent_events = (
        recent_events
        if recent_events is not None
        else portfolio_status(base_path).get("recent_events", [])
    )
    inbox_items = (
        inbox_items
        if inbox_items is not None
        else build_inbox(base_path, project_titles=project_titles, runs=runs)
    )
    notifications: list[dict[str, Any]] = [
        {**item, "notification_tier": "actionable"} for item in inbox_items
    ]
    for event in recent_events:
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        run_id = str(event.get("run_id") or payload.get("run_id") or "") or None
        project_id = str(event.get("project_id") or payload.get("project_id") or "") or None
        notifications.append(
            _attention_item(
                kind="event-notification",
                priority=3,
                title=str(payload.get("message") or event.get("type") or "Workspace event"),
                reason=str(
                    payload.get("summary")
                    or payload.get("message")
                    or "Recent manager event recorded."
                ),
                project_id=project_id,
                project_label=project_titles.get(project_id or "", project_id or "Project"),
                run_id=run_id,
                run_label=run_id or "Workspace event",
                occurred_at=str(event.get("ts") or event.get("occurred_at") or ""),
                source="event",
                notification_tier="informational",
            )
        )
    for run in [run for run in runs if run.get("status") == "accepted"][:6]:
        project_id = str(run.get("project_id") or "") or None
        run_label = _run_title(run)
        notifications.append(
            _attention_item(
                kind="accepted-run",
                priority=3,
                title=f"Accepted {run_label}",
                reason=f"{run_label} was accepted on driver {run.get('driver', 'unknown')}.",
                project_id=project_id,
                project_label=project_titles.get(project_id or "", project_id or "Project"),
                run_id=str(run.get("id") or "") or None,
                run_label=run_label,
                occurred_at=str(run.get("finished_at") or run.get("updated_at") or run.get("started_at") or ""),
                source="run",
                notification_tier="informational",
            )
        )
    deduped: dict[str, dict[str, Any]] = {}
    for item in notifications:
        deduped[str(item["id"])] = item
    items = _sort_attention_items(list(deduped.values()))
    return {
        "items": items,
        "summary": summarize_attention_items(items),
    }


def build_activity_feed(
    base_path: Path,
    *,
    project_titles: dict[str, str] | None = None,
    recent_events: list[dict[str, Any]] | None = None,
    runs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return a compact recent-activity feed for the command center."""
    items: list[dict[str, Any]] = []
    project_titles = project_titles if project_titles is not None else _project_titles(base_path)
    recent_events = (
        recent_events
        if recent_events is not None
        else portfolio_status(base_path).get("recent_events", [])
    )
    runs = runs if runs is not None else list_runs(base_path)
    for event in recent_events:
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        run_id = str(event.get("run_id") or payload.get("run_id") or "") or None
        project_id = str(event.get("project_id") or payload.get("project_id") or "") or None
        items.append(
            {
                "id": f"activity::{event.get('event_id') or event.get('id')}",
                "kind": "event",
                "title": str(payload.get("message") or event.get("type") or "Workspace event"),
                "summary": str(
                    payload.get("summary")
                    or payload.get("message")
                    or "Recent workspace activity was recorded."
                ),
                "occurred_at": str(event.get("ts") or event.get("occurred_at") or ""),
                "source": "event",
                "run_id": run_id,
                "project_id": project_id,
                "project_label": project_titles.get(project_id or "", project_id or "Project"),
                "deep_link": _attention_deep_link("event-notification", run_id=run_id, project_id=project_id),
            }
        )
    for run in [run for run in runs if run.get("status") == "accepted"][:8]:
        project_id = str(run.get("project_id") or "") or None
        run_label = _run_title(run)
        items.append(
            {
                "id": f"activity::accepted::{run.get('id')}",
                "kind": "accepted-run",
                "title": f"Accepted {run_label}",
                "summary": f"{run_label} was accepted on driver {run.get('driver', 'unknown')}.",
                "occurred_at": str(run.get("finished_at") or run.get("updated_at") or run.get("started_at") or ""),
                "source": "run",
                "run_id": str(run.get("id") or "") or None,
                "project_id": project_id,
                "project_label": project_titles.get(project_id or "", project_id or "Project"),
                "deep_link": _attention_deep_link(
                    "accepted-run",
                    run_id=str(run.get("id") or "") or None,
                    project_id=project_id,
                ),
            }
        )
    items.sort(key=lambda item: str(item.get("id") or ""))
    items.sort(key=lambda item: str(item.get("occurred_at") or ""), reverse=True)
    items.sort(key=lambda item: not bool(item.get("occurred_at")))
    return {
        "items": items[:20],
        "summary": {
            "total": len(items[:20]),
        },
    }


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

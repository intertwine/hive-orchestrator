"""Structured approval broker helpers for v2.3 runtime scaffolding."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any, cast

from src.hive.clock import utc_now_iso
from src.hive.ids import new_id
from src.hive.store.events import emit_event


@dataclass
class ApprovalRequest:
    """One structured approval item emitted by a driver or sandbox."""

    approval_id: str
    run_id: str
    project_id: str | None
    task_id: str | None
    campaign_id: str | None
    driver: str
    kind: str
    title: str
    summary: str
    requested_at: str = field(default_factory=utc_now_iso)
    requested_by: str = "system"
    status: str = "pending"
    payload: dict[str, Any] = field(default_factory=dict)
    resolved_at: str | None = None
    resolved_by: str | None = None
    resolution: str | None = None
    resolution_note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the approval request."""
        return asdict(self)


def _approval_file(metadata: dict[str, Any]) -> Path:
    return Path(str(metadata["approvals_path"]))


def _read_approvals(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    target = _approval_file(metadata)
    if not target.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in target.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def _write_approvals(metadata: dict[str, Any], approvals: list[dict[str, Any]]) -> None:
    target = _approval_file(metadata)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as handle:
        for item in approvals:
            handle.write(json.dumps(item, sort_keys=True) + "\n")


def list_approvals(path: str | Path | None, run_id: str) -> list[dict[str, Any]]:
    """Return all approval requests for a run."""
    from src.hive.runs.metadata import load_run

    metadata = load_run(path, run_id)
    return _read_approvals(metadata)


def pending_approvals(path: str | Path | None, run_id: str) -> list[dict[str, Any]]:
    """Return unresolved approval requests for a run."""
    return [item for item in list_approvals(path, run_id) if item.get("status") == "pending"]


def request_approval(
    path: str | Path | None,
    run_id: str,
    *,
    kind: str,
    title: str,
    summary: str,
    requested_by: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append one approval request to a run and emit the matching event."""
    from src.hive.runs.metadata import load_run, save_run

    metadata = load_run(path, run_id)
    approval = ApprovalRequest(
        approval_id=new_id("approval"),
        run_id=run_id,
        project_id=metadata.get("project_id"),
        task_id=metadata.get("task_id"),
        campaign_id=metadata.get("campaign_id"),
        driver=str(metadata.get("driver") or "unknown"),
        kind=kind,
        title=title,
        summary=summary,
        requested_by=requested_by,
        payload=dict(payload or {}),
    )
    approvals = _read_approvals(metadata)
    approvals.append(approval.to_dict())
    _write_approvals(metadata, approvals)
    metadata.setdefault("metadata_json", {}).setdefault("approvals", []).append(approval.to_dict())
    save_run(path, run_id, metadata)
    emit_event(
        path,
        actor={"kind": "system", "id": requested_by},
        entity_type="run",
        entity_id=run_id,
        event_type="approval.requested",
        source="runtime.approval",
        payload=approval.to_dict(),
        run_id=run_id,
        task_id=metadata.get("task_id"),
        project_id=metadata.get("project_id"),
        campaign_id=metadata.get("campaign_id"),
    )
    return approval.to_dict()


def resolve_approval(
    path: str | Path | None,
    run_id: str,
    approval_id: str,
    *,
    resolution: str,
    actor: str,
    note: str | None = None,
) -> dict[str, Any]:
    """Resolve a pending approval request and emit the matching event."""
    from src.hive.runs.metadata import load_run, save_run

    if resolution not in {"approved", "rejected"}:
        raise ValueError(f"Unsupported approval resolution: {resolution}")
    metadata = load_run(path, run_id)
    approvals = _read_approvals(metadata)
    updated: dict[str, Any] | None = None
    for item in approvals:
        if item.get("approval_id") != approval_id:
            continue
        if item.get("status") != "pending":
            raise ValueError(f"Approval {approval_id} is already resolved")
        item["status"] = resolution
        item["resolution"] = resolution
        item["resolved_at"] = utc_now_iso()
        item["resolved_by"] = actor
        item["resolution_note"] = note
        updated = dict(item)
        break
    if updated is None:
        raise FileNotFoundError(f"Approval not found: {approval_id}")
    _write_approvals(metadata, approvals)
    metadata.setdefault("metadata_json", {})["approvals"] = approvals
    save_run(path, run_id, metadata)
    emit_event(
        path,
        actor={"kind": "human", "id": actor},
        entity_type="run",
        entity_id=run_id,
        event_type="approval.resolved",
        source="runtime.approval",
        payload=updated,
        run_id=run_id,
        task_id=metadata.get("task_id"),
        project_id=metadata.get("project_id"),
        campaign_id=metadata.get("campaign_id"),
    )
    return updated


def resolve_pending_approvals(
    path: str | Path | None,
    run_id: str,
    *,
    resolution: str,
    actor: str,
    note: str | None = None,
) -> list[dict[str, Any]]:
    """Resolve every still-pending approval for a run and emit per-item events."""
    from src.hive.runs.metadata import load_run, save_run

    if resolution not in {"approved", "rejected"}:
        raise ValueError(f"Unsupported approval resolution: {resolution}")
    metadata = load_run(path, run_id)
    approvals = _read_approvals(metadata)
    resolved: list[dict[str, Any]] = []
    for item in approvals:
        if item.get("status") != "pending":
            continue
        item["status"] = resolution
        item["resolution"] = resolution
        item["resolved_at"] = utc_now_iso()
        item["resolved_by"] = actor
        item["resolution_note"] = note
        resolved.append(dict(item))
    if not resolved:
        return []
    _write_approvals(metadata, approvals)
    metadata.setdefault("metadata_json", {})["approvals"] = approvals
    save_run(path, run_id, metadata)
    for item in resolved:
        emit_event(
            path,
            actor={"kind": "human", "id": actor},
            entity_type="run",
            entity_id=run_id,
            event_type="approval.resolved",
            source="runtime.approval",
            payload=item,
            run_id=run_id,
            task_id=metadata.get("task_id"),
            project_id=metadata.get("project_id"),
            campaign_id=metadata.get("campaign_id"),
        )
    return resolved


def bridge_approval_resolution(
    path: str | Path,
    metadata: dict[str, Any],
    *,
    approval: dict[str, Any],
    action: str,
    actor: str | None,
    request: Any,
) -> dict[str, Any] | None:
    """Forward one resolved approval to the driver channel and record it in run metadata."""
    from src.hive.drivers import get_driver
    from src.hive.runs.driver_state import (
        _active_driver_handle,
        _append_transcript_entry,
    )
    from src.hive.store.events import emit_event

    driver_ack: dict[str, Any] | None = None
    try:
        handle = _active_driver_handle(metadata)
    except ValueError:
        handle = None
    if handle is not None:
        driver = get_driver(str(metadata.get("driver", handle.driver)))
        driver_ack = cast(
            dict[str, Any],
            driver.submit_approval_resolution(handle, cast(dict[str, Any], approval)),
        )
    metadata.setdefault("metadata_json", {}).setdefault("approval_resolutions", []).append(approval)
    metadata.setdefault("metadata_json", {}).setdefault("approval_forwarding", []).append(
        {
            "approval_id": approval.get("approval_id"),
            "resolution": approval.get("resolution"),
            "driver_ack": driver_ack,
        }
    )
    if driver_ack is not None:
        resolution = str(approval.get("resolution") or action)
        transcript_path_value = str(metadata.get("transcript_path") or "").strip()
        if transcript_path_value:
            _append_transcript_entry(
                Path(transcript_path_value),
                {
                    "ts": utc_now_iso(),
                    "kind": "system",
                    "driver": metadata.get("driver"),
                    "message": (
                        f"Approval {approval.get('approval_id')} was {resolution} and forwarded "
                        "to the driver channel."
                    ),
                    "approval_id": approval.get("approval_id"),
                    "resolution": resolution,
                },
            )
        emit_event(
            path,
            actor={"kind": "human", "id": actor or "operator"},
            entity_type="run",
            entity_id=str(metadata["id"]),
            event_type="approval.forwarded",
            source="runtime.approval",
            payload={"approval": approval, "driver_ack": driver_ack},
            run_id=str(metadata["id"]),
            task_id=metadata.get("task_id"),
            project_id=metadata.get("project_id"),
            campaign_id=metadata.get("campaign_id"),
        )
    return driver_ack


__all__ = [
    "ApprovalRequest",
    "bridge_approval_resolution",
    "list_approvals",
    "pending_approvals",
    "request_approval",
    "resolve_approval",
    "resolve_pending_approvals",
]

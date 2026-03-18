"""Run steering helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from src.hive.clock import utc_now_iso
from src.hive.constants import RUN_TERMINAL_STATUSES
from src.hive.drivers import SteeringRequest, get_driver
from src.hive.runs.driver_state import (
    _active_driver_handle,
    _append_transcript_entry,
    _build_reroute_launch_request,
    _load_driver_handles,
    _record_driver_status,
    _record_steering_history,
    _save_driver_handles,
    _steering_event_type,
)
from src.hive.runs.metadata import load_run, save_run
from src.hive.store.events import emit_event
from src.hive.store.task_files import get_task, save_task


def steer_run(
    path: str | Path | None,
    run_id: str,
    request: SteeringRequest,
    *,
    actor: str | None = None,
) -> dict[str, object]:
    """Apply a steering action that does not change run acceptance state."""
    root = Path(path or Path.cwd()).resolve()

    metadata = load_run(root, run_id)
    action = request.action
    if action not in {
        "pause",
        "resume",
        "cancel",
        "reroute",
        "note",
        "approve",
        "reject",
    }:
        raise ValueError(f"Unsupported steering action {action!r}")
    if action in {"approve", "reject"}:
        raise ValueError("Approval and rejection are handled by the lifecycle wrapper.")
    if action != "note" and metadata.get("status") in RUN_TERMINAL_STATUSES:
        raise ValueError(f"Cannot steer terminal run with status {metadata.get('status')!r}")

    driver = get_driver(str(metadata.get("driver", "local")))
    handle = _active_driver_handle(metadata)
    timeline_entry = _record_steering_history(
        metadata,
        action=action,
        actor=actor,
        reason=request.reason,
        note=request.note,
        target=cast(dict[str, object] | None, request.target),
        budget_delta=cast(dict[str, object] | None, request.budget_delta),
    )
    ack: dict[str, object] | None = None

    if action in {"pause", "resume", "cancel"}:
        ack = driver.interrupt(handle, action)
        timeline_entry["driver_ack"] = ack
        if action == "pause":
            metadata["health"] = "paused"
            metadata.setdefault("metadata_json", {})["paused"] = True
        elif action == "resume":
            metadata["health"] = "healthy"
            metadata.setdefault("metadata_json", {})["paused"] = False
        else:
            metadata["status"] = "cancelled"
            metadata["health"] = "cancelled"
            metadata["finished_at"] = utc_now_iso()
            metadata["exit_reason"] = request.reason
            task = get_task(root, metadata["task_id"])
            task.status = "ready"
            task.owner = None
            task.claimed_until = None
            save_task(root, task)
    elif action == "note":
        ack = driver.steer(handle, request)
        timeline_entry["driver_ack"] = ack
    elif action == "reroute":
        target_driver = str((request.target or {}).get("driver", "")).strip()
        if not target_driver:
            raise ValueError("Reroute requires target.driver")
        emit_event(
            root,
            actor={"kind": "human", "id": actor or "operator"},
            entity_type="run",
            entity_id=run_id,
            event_type="steering.reroute_requested",
            source="run.steer",
            payload={"request": request.to_dict()},
            run_id=run_id,
            task_id=metadata.get("task_id"),
            project_id=metadata.get("project_id"),
            campaign_id=metadata.get("campaign_id"),
        )
        new_driver = get_driver(target_driver)
        new_request = _build_reroute_launch_request(
            root,
            metadata,
            driver_name=target_driver,
            model=str((request.target or {}).get("model") or "") or None,
        )
        new_handle = new_driver.launch(new_request)
        new_status = new_driver.status(new_handle)
        handles = _load_driver_handles(metadata)
        history = list(handles.get("history", []))
        history.append(
            {
                "driver": metadata.get("driver"),
                "driver_handle": metadata.get("driver_handle"),
                "status": metadata.get("status"),
                "rerouted_at": utc_now_iso(),
            }
        )
        history.append(new_handle.to_dict())
        handles["active"] = new_handle.to_dict()
        handles["history"] = history
        _save_driver_handles(metadata, handles)
        Path(metadata["driver_metadata_path"]).write_text(
            json.dumps(new_driver.probe().to_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        if metadata.get("capability_snapshot_path"):
            new_probe = new_driver.probe()
            if new_probe.capability_snapshot is not None:
                Path(metadata["capability_snapshot_path"]).write_text(
                    json.dumps(new_probe.capability_snapshot.to_dict(), indent=2, sort_keys=True),
                    encoding="utf-8",
                )
                metadata.setdefault("metadata_json", {}).setdefault("runtime_v2", {})[
                    "capability_snapshot"
                ] = new_probe.capability_snapshot.to_dict()
        if metadata.get("runtime_manifest_path"):
            manifest_path = Path(str(metadata["runtime_manifest_path"]))
            if manifest_path.exists():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest["driver"] = target_driver
                manifest["driver_mode"] = (
                    new_driver.probe().capability_snapshot.effective.launch_mode
                    if new_driver.probe().capability_snapshot is not None
                    else "staged"
                )
                manifest_path.write_text(
                    json.dumps(manifest, indent=2, sort_keys=True),
                    encoding="utf-8",
                )
        metadata["driver"] = target_driver
        metadata["driver_handle"] = new_handle.driver_handle
        metadata["status"] = new_status.state
        metadata["health"] = new_status.health
        _record_driver_status(metadata, new_status.to_dict())
        ack = {
            "ok": True,
            "from": driver.name,
            "to": target_driver,
            "new_handle": new_handle.to_dict(),
        }
        timeline_entry["driver_ack"] = ack
        _append_transcript_entry(
            Path(metadata["transcript_path"]),
            {
                "ts": utc_now_iso(),
                "kind": "system",
                "driver": target_driver,
                "message": f"Run rerouted from {driver.name} to {target_driver}",
                "state": new_status.state,
            },
        )

    if ack is not None:
        timeline_entry["driver_ack"] = ack
    emit_event(
        root,
        actor={"kind": "human", "id": actor or "operator"},
        entity_type="run",
        entity_id=run_id,
        event_type=_steering_event_type(action),
        source="run.steer",
        payload={"request": request.to_dict(), "ack": ack},
        run_id=run_id,
        task_id=metadata.get("task_id"),
        project_id=metadata.get("project_id"),
        campaign_id=metadata.get("campaign_id"),
    )
    if action == "cancel":
        emit_event(
            root,
            actor={"kind": "human", "id": actor or "operator"},
            entity_type="run",
            entity_id=run_id,
            event_type="run.cancelled",
            source="run.steer",
            payload={"reason": request.reason},
            run_id=run_id,
            task_id=metadata.get("task_id"),
            project_id=metadata.get("project_id"),
            campaign_id=metadata.get("campaign_id"),
        )
    if action in {"pause", "resume", "reroute"}:
        emit_event(
            root,
            actor={"kind": "human", "id": actor or "operator"},
            entity_type="run",
            entity_id=run_id,
            event_type="run.status.changed",
            source="run.steer",
            payload={"state": metadata.get("status"), "health": metadata.get("health")},
            run_id=run_id,
            task_id=metadata.get("task_id"),
            project_id=metadata.get("project_id"),
            campaign_id=metadata.get("campaign_id"),
        )
    save_run(root, run_id, metadata)
    return {
        "run": metadata,
        "action": action,
        "request": request.to_dict(),
        "driver_ack": ack,
    }

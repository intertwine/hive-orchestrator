"""Driver and steering state helpers for runs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.hive.clock import utc_now_iso
from src.hive.drivers import RunHandle, RunLaunchRequest, get_driver
from src.hive.runs.program import _build_reroute_launch_request, _run_program_policy
from src.hive.store.events import emit_event


def _emit_context_compiled_events(
    root: Path,
    *,
    run_id: str,
    task_id: str,
    project_id: str,
    manifest_path: str,
) -> None:
    """Emit both run-scoped and context-scoped context-compilation events."""
    payload = {"manifest_path": manifest_path}
    emit_event(
        root,
        actor={"kind": "system", "id": "hive"},
        entity_type="run",
        entity_id=run_id,
        event_type="run.context_compiled",
        source="run.start",
        payload=payload,
        run_id=run_id,
        task_id=task_id,
        project_id=project_id,
    )
    emit_event(
        root,
        actor={"kind": "system", "id": "hive"},
        entity_type="run",
        entity_id=run_id,
        event_type="context.compiled",
        source="run.start",
        payload=payload,
        run_id=run_id,
        task_id=task_id,
        project_id=project_id,
    )


def _append_transcript_entry(path: Path, record: dict[str, object]) -> None:
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    ndjson_path = path.parent.parent / "transcript.ndjson"
    with open(ndjson_path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def _load_driver_handles(metadata: dict) -> dict[str, object]:
    handles_path_value = metadata.get("driver_handles_path")
    if not handles_path_value:
        return {"active": None, "history": []}
    handles_path = Path(handles_path_value)
    if not handles_path.exists():
        return {"active": None, "history": []}
    return json.loads(handles_path.read_text(encoding="utf-8"))


def _save_driver_handles(metadata: dict, handles: dict[str, object]) -> None:
    handles_path = Path(metadata["driver_handles_path"])
    handles_path.write_text(json.dumps(handles, indent=2, sort_keys=True), encoding="utf-8")


def _active_driver_handle(metadata: dict) -> RunHandle:
    handles = _load_driver_handles(metadata)
    active = handles.get("active")
    if not isinstance(active, dict):
        raise ValueError(f"Run {metadata['id']} does not have an active driver handle")
    return RunHandle(**active)


def _record_driver_status(metadata: dict, status: dict[str, object]) -> None:
    metadata.setdefault("metadata_json", {})["driver_status"] = status


def _update_active_handle_from_status(metadata: dict, status_payload: dict[str, object]) -> None:
    handles = _load_driver_handles(metadata)
    active = handles.get("active")
    if not isinstance(active, dict):
        return
    active["status"] = status_payload.get("state")
    if status_payload.get("event_cursor") is not None:
        active["event_cursor"] = status_payload.get("event_cursor")
    session = status_payload.get("session")
    if isinstance(session, dict):
        if session.get("transport") is not None:
            active["transport"] = session.get("transport")
        if session.get("session_id") is not None:
            active["session_id"] = session.get("session_id")
        if session.get("thread_id") is not None:
            active["thread_id"] = session.get("thread_id")
    handles["active"] = active
    history = list(handles.get("history") or [])
    if history and isinstance(history[-1], dict) and history[-1].get("driver_handle") == active.get(
        "driver_handle"
    ):
        # Keep one mutable latest-state record per live handle; events remain the audit log.
        history[-1] = dict(active)
        handles["history"] = history
    _save_driver_handles(metadata, handles)


def _import_driver_last_message(metadata: dict, status_payload: dict[str, object]) -> None:
    if status_payload.get("state") not in {"completed_candidate", "failed", "cancelled"}:
        return
    artifacts = status_payload.get("artifacts")
    if not isinstance(artifacts, dict):
        return
    message_path_value = artifacts.get("last_message_path")
    if not isinstance(message_path_value, str) or not message_path_value.strip():
        return
    message_path = Path(message_path_value)
    if not message_path.exists():
        return
    content = message_path.read_text(encoding="utf-8").strip()
    if not content:
        return
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    imports = metadata.setdefault("metadata_json", {}).setdefault("driver_imports", {})
    if imports.get("last_message_sha256") == digest:
        return
    _append_transcript_entry(
        Path(metadata["transcript_path"]),
        {
            "ts": utc_now_iso(),
            "kind": "assistant",
            "driver": metadata.get("driver"),
            "message": content,
            "state": status_payload.get("state"),
        },
    )
    imports["last_message_sha256"] = digest


def _refresh_live_driver_status(metadata: dict) -> dict[str, object] | None:
    handle = _active_driver_handle(metadata)
    if handle.launch_mode not in {"exec", "app_server", "sdk", "rpc"}:
        return None
    driver = get_driver(str(metadata.get("driver", handle.driver)))
    previous = dict(metadata.get("metadata_json", {}).get("driver_status") or {})
    status = driver.status(handle)
    status_payload = status.to_dict()
    _record_driver_status(metadata, status_payload)
    _update_active_handle_from_status(metadata, status_payload)
    _import_driver_last_message(metadata, status_payload)
    return {"previous": previous, "current": status_payload}


def _record_steering_history(
    metadata: dict,
    *,
    action: str,
    actor: str | None,
    reason: str | None,
    note: str | None,
    target: dict[str, object] | None,
    budget_delta: dict[str, object] | None,
    ack: dict[str, object] | None = None,
) -> dict[str, object]:
    entry: dict[str, object] = {
        "ts": utc_now_iso(),
        "action": action,
        "actor": actor or "operator",
        "reason": reason,
        "note": note,
        "target": dict(target or {}),
        "budget_delta": dict(budget_delta or {}),
    }
    if ack is not None:
        entry["driver_ack"] = ack
    metadata.setdefault("metadata_json", {}).setdefault("steering_history", []).append(entry)
    return entry


def _steering_event_type(action: str) -> str:
    if action == "note":
        return "steering.note_added"
    if action == "reroute":
        return "steering.rerouted"
    return f"steering.{action}"


def load_driver_metadata(metadata: dict) -> RunHandle:
    """Return the active driver handle for a run."""
    return _active_driver_handle(metadata)


def build_reroute_launch_request(
    root: Path,
    metadata: dict,
    *,
    driver_name: str,
    model: str | None = None,
) -> RunLaunchRequest:
    """Build a reroute launch request for a typed steering action."""
    return _build_reroute_launch_request(root, metadata, driver_name=driver_name, model=model)


def run_program_policy(program) -> dict[str, object]:
    """Return the normalized policy payload used to launch or reroute a run."""
    return _run_program_policy(program)


__all__ = [
    "build_reroute_launch_request",
    "load_driver_metadata",
    "run_program_policy",
]

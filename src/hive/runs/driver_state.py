"""Driver and steering state helpers for runs."""

from __future__ import annotations

import json
from pathlib import Path

from src.hive.clock import utc_now_iso
from src.hive.drivers import RunHandle, RunLaunchRequest
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

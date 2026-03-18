"""Event log helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.hive.clock import utc_now, utc_now_iso
from src.hive.ids import new_id
from src.hive.store.layout import events_dir


def event_file(path: str | Path | None = None) -> Path:
    """Return today's event log path."""
    return events_dir(path) / f"{utc_now().date().isoformat()}.jsonl"


def _normalize_actor(value: str | dict[str, Any] | None) -> tuple[dict[str, str], str]:
    """Return a structured actor payload plus a legacy text field."""
    if isinstance(value, dict):
        kind = str(value.get("kind") or "system")
        actor_id = str(value.get("id") or "unknown")
        return {"kind": kind, "id": actor_id}, actor_id
    actor_id = str(value or "hive")
    kind = "human"
    if actor_id.startswith(("driver:", "hive", "system")):
        kind = "system"
    return {"kind": kind, "id": actor_id}, actor_id


def run_event_file(path: str | Path | None, run_id: str) -> Path:
    """Return the per-run timeline path."""
    return Path(path or Path.cwd()).resolve() / ".hive" / "runs" / run_id / "events.jsonl"


def run_event_ndjson_file(path: str | Path | None, run_id: str) -> Path:
    """Return the v2.3 per-run timeline path."""
    return Path(path or Path.cwd()).resolve() / ".hive" / "runs" / run_id / "events.ndjson"


def emit_event(
    path: str | Path | None,
    *,
    actor: str | dict[str, Any],
    entity_type: str,
    entity_id: str,
    event_type: str,
    source: str,
    payload: dict[str, Any] | None = None,
    run_id: str | None = None,
    task_id: str | None = None,
    project_id: str | None = None,
    campaign_id: str | None = None,
) -> dict[str, Any]:
    """Append an event to the JSONL audit log."""
    actor_ref, actor_text = _normalize_actor(actor)
    event_id = new_id("evt")
    ts = utc_now_iso()
    # Keep both normalized v2.2 fields and backward-compatible aliases while packaged tooling
    # finishes converging on a single event vocabulary.
    record = {
        "event_id": event_id,
        "ts": ts,
        "type": event_type,
        "run_id": run_id,
        "task_id": task_id,
        "project_id": project_id,
        "campaign_id": campaign_id,
        "actor": actor_ref,
        "payload": payload or {},
        "id": event_id,
        "occurred_at": ts,
        "actor_text": actor_text,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "event_type": event_type,
        "source": source,
        "payload_json": payload or {},
    }
    target = event_file(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    if run_id:
        run_target = run_event_file(path, run_id)
        run_target.parent.mkdir(parents=True, exist_ok=True)
        with open(run_target, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        run_target_ndjson = run_event_ndjson_file(path, run_id)
        run_target_ndjson.parent.mkdir(parents=True, exist_ok=True)
        with open(run_target_ndjson, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def load_events(path: str | Path | None = None) -> list[dict[str, Any]]:
    """Load all JSONL events."""
    directory = events_dir(path)
    if not directory.exists():
        return []
    events: list[dict[str, Any]] = []
    for file_path in sorted(directory.glob("*.jsonl")):
        for line in file_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line))
    return events

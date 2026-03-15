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


def emit_event(
    path: str | Path | None,
    *,
    actor: str,
    entity_type: str,
    entity_id: str,
    event_type: str,
    source: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append an event to the JSONL audit log."""
    record = {
        "id": new_id("evt"),
        "occurred_at": utc_now_iso(),
        "actor": actor,
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

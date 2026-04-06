"""Shared utilities for Hive v2."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HIVE_VERSION = "2.4.0"

MARKER_PROJECTS_BEGIN = "<!-- hive:begin projects -->"
MARKER_PROJECTS_END = "<!-- hive:end projects -->"
MARKER_TASK_ROLLUP_BEGIN = "<!-- hive:begin task-rollup -->"
MARKER_TASK_ROLLUP_END = "<!-- hive:end task-rollup -->"
MARKER_RECENT_RUNS_BEGIN = "<!-- hive:begin recent-runs -->"
MARKER_RECENT_RUNS_END = "<!-- hive:end recent-runs -->"
MARKER_AGENTS_BEGIN = "<!-- hive:begin agents -->"
MARKER_AGENTS_END = "<!-- hive:end agents -->"


def utc_now() -> datetime:
    """Return the current UTC time."""
    return datetime.now(timezone.utc)


def isoformat_z(value: datetime | None = None) -> str:
    """Format a datetime as a compact UTC timestamp."""
    timestamp = value or utc_now()
    return timestamp.isoformat().replace("+00:00", "Z")


def ensure_directory(path: Path) -> Path:
    """Create a directory if needed and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_json(path: Path, default: Any = None) -> Any:
    """Read JSON from disk with a default value."""
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, payload: Any) -> None:
    """Write stable JSON to disk."""
    ensure_directory(path.parent)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def serialize_value(value: Any) -> Any:
    """Convert a value into a JSON-safe structure."""
    if is_dataclass(value):
        return {key: serialize_value(item) for key, item in asdict(value).items()}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return isoformat_z(value)
    if isinstance(value, dict):
        return {key: serialize_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [serialize_value(item) for item in value]
    return value


def json_payload(payload: Any) -> str:
    """Serialize a payload for CLI JSON output."""
    return json.dumps(serialize_value(payload), indent=2, sort_keys=True)

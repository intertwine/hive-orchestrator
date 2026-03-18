"""Run metadata load/save helpers."""

from __future__ import annotations

import json
from pathlib import Path

from src.hive.models.run import RunRecord
from src.hive.runs.paths import metadata_path as _metadata_path_impl
from src.hive.runs.paths import run_dir as _run_dir_impl


def load_run(path: str | Path | None, run_id: str) -> dict:
    """Load run metadata."""
    metadata_file = _metadata_path_impl(path, run_id)
    if not metadata_file.exists():
        raise FileNotFoundError(f"Run not found: {run_id}")
    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    metadata.setdefault("driver", metadata.get("executor", "local"))
    metadata.setdefault("health", "healthy")
    metadata.setdefault("workspace_patch_path", metadata.get("patch_path"))
    metadata.setdefault("workspace_changed_files_path", None)
    metadata.setdefault("events_path", str(_run_dir_impl(path, run_id) / "events.jsonl"))
    metadata.setdefault("metadata_json", {})
    metadata.setdefault("campaign_id", None)
    if metadata.get("status") == "evaluating":
        metadata["status"] = "awaiting_review"
    return metadata


def save_run(path: str | Path | None, run_id: str, metadata: dict) -> dict:
    """Persist run metadata."""
    _metadata_path_impl(path, run_id).write_text(
        json.dumps(metadata, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return metadata


def run_record_to_json(run: RunRecord) -> str:
    """Serialize a run record for storage."""
    return json.dumps(run.to_dict(), indent=2, sort_keys=True)

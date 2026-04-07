"""Shared delegate-session loaders for search and console surfaces."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _delegate_manifest_paths(base_path: Path) -> list[Path]:
    delegates_root = base_path / ".hive" / "delegates"
    if not delegates_root.exists():
        return []
    return sorted(delegates_root.glob("*/manifest.json"))


def _load_json(path: Path) -> dict[str, Any] | list[Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


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


def load_delegate_entry(manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    session_dir = manifest_path.parent
    final_state = _load_json(session_dir / "final.json")
    if not isinstance(final_state, dict):
        final_state = {}
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


def list_delegate_entries(base_path: Path) -> list[dict[str, Any]]:
    """Return normalized delegate-session entries."""
    return [load_delegate_entry(manifest_path) for manifest_path in _delegate_manifest_paths(base_path)]

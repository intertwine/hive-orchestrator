"""Materialized handoff artifacts for context compilation and reroutes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.hive.clock import utc_now_iso
from src.hive.runs.metadata import load_run
from src.hive.store.layout import runs_dir
from src.hive.store.task_files import list_tasks


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_ndjson(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _preview(path_value: str | None, *, limit: int = 800) -> str | None:
    if not path_value:
        return None
    path = Path(path_value)
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")[:limit].strip() or None


def _lineage(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    handles_path = Path(str(metadata.get("driver_handles_path") or ""))
    if not handles_path.exists():
        return []
    payload = _read_json(handles_path)
    history = payload.get("history") or []
    return [item for item in history if isinstance(item, dict)]


def compile_context_handoffs(
    root: Path,
    *,
    project_id: str,
    task,
    run_directory: Path,
    limit: int = 6,
) -> dict[str, Any]:
    """Collect accepted dependency artifacts and persist them for a new run."""
    dependency_ids = {
        candidate.id
        for candidate in list_tasks(root)
        if candidate.project_id == project_id and task.id in (candidate.edges.get("blocks", []) or [])
    }
    dependency_ids.update(
        str(value).strip() for value in (getattr(task, "metadata", {}) or {}).get("blocked_by", [])
    )
    dependency_ids = {value for value in dependency_ids if value}
    if not dependency_ids:
        return {"items": [], "manifest_path": None, "summary_path": None}

    items: list[dict[str, Any]] = []
    for metadata_path in sorted(runs_dir(root).glob("run_*/metadata.json"), reverse=True):
        run = load_run(root, metadata_path.parent.name)
        if str(run.get("project_id") or "") != project_id:
            continue
        if str(run.get("status") or "") != "accepted":
            continue
        task_id = str(run.get("task_id") or "")
        if task_id not in dependency_ids:
            continue
        items.append(
            {
                "run_id": str(run["id"]),
                "task_id": task_id,
                "task_title": str((run.get("metadata_json") or {}).get("task_title") or task_id),
                "reason": "accepted dependency run",
                "summary_path": run.get("summary_path"),
                "review_path": run.get("review_path"),
                "final_path": run.get("final_path"),
                "context_manifest_path": run.get("context_manifest_path"),
                "workspace_patch_path": run.get("workspace_patch_path") or run.get("patch_path"),
                "summary_preview": _preview(run.get("summary_path")),
                "review_preview": _preview(run.get("review_path")),
            }
        )
        if len(items) >= limit:
            break

    if not items:
        return {"items": [], "manifest_path": None, "summary_path": None}

    compiled_dir = run_directory / "context" / "compiled"
    compiled_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = compiled_dir / "handoffs.json"
    summary_path = compiled_dir / "handoff-summary.md"
    manifest = {
        "generated_at": utc_now_iso(),
        "run_count": len(items),
        "dependency_task_ids": sorted(dependency_ids),
        "runs": items,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Handoff Summary",
        "",
        "These accepted dependency runs were attached as explicit context for this run.",
        "",
    ]
    for item in items:
        lines.extend(
            [
                f"## {item['task_title']}",
                "",
                f"- Run: `{item['run_id']}`",
                f"- Task: `{item['task_id']}`",
                f"- Summary: `{item['summary_path']}`" if item.get("summary_path") else "- Summary: none",
                (
                    f"- Patch: `{item['workspace_patch_path']}`"
                    if item.get("workspace_patch_path")
                    else "- Patch: none"
                ),
                "",
                item.get("summary_preview") or item.get("review_preview") or "_No preview available._",
                "",
            ]
        )
    summary_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return {
        "items": items,
        "manifest_path": str(manifest_path),
        "summary_path": str(summary_path),
    }


def export_reroute_bundle(
    root: Path,
    metadata: dict[str, Any],
    *,
    target_driver: str,
    target_model: str | None = None,
) -> dict[str, Any]:
    """Materialize a reroute bundle that can be handed to another driver."""
    run_id = str(metadata["id"])
    run_root = runs_dir(root) / run_id
    handoff_dir = run_root / "handoff"
    handoff_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = handoff_dir / "reroute-bundle.json"
    summary_path = handoff_dir / "reroute-summary.md"

    approvals = [
        approval
        for approval in _read_ndjson(Path(str(metadata.get("approvals_path") or "")))
        if str(approval.get("status") or "") == "pending"
    ]
    skills_manifest = _read_json(
        Path(str(metadata.get("context_compiled_dir") or "")) / "skills-manifest.json"
    )
    bundle = {
        "generated_at": utc_now_iso(),
        "run_id": run_id,
        "project_id": metadata.get("project_id"),
        "task_id": metadata.get("task_id"),
        "source_driver": metadata.get("driver"),
        "target_driver": target_driver,
        "target_model": target_model,
        "lineage": _lineage(metadata),
        "artifacts": {
            "transcript": metadata.get("transcript_path"),
            "plan": metadata.get("plan_path"),
            "workspace_patch": metadata.get("workspace_patch_path") or metadata.get("patch_path"),
            "context_manifest": metadata.get("context_manifest_path"),
            "retrieval_trace": metadata.get("retrieval_trace_path"),
            "scheduler_decision": metadata.get("scheduler_decision_path"),
            "approvals": metadata.get("approvals_path"),
            "skills_manifest": (
                str(Path(str(metadata.get("context_compiled_dir") or "")) / "skills-manifest.json")
                if metadata.get("context_compiled_dir")
                else None
            ),
        },
        "pending_approvals": approvals,
        "selected_skills": list(skills_manifest.get("skills") or []),
        "state": {
            "status": metadata.get("status"),
            "health": metadata.get("health"),
            "steering_history": list((metadata.get("metadata_json") or {}).get("steering_history", [])),
        },
        "previews": {
            "summary": _preview(metadata.get("summary_path")),
            "review": _preview(metadata.get("review_path")),
            "transcript": _preview(metadata.get("transcript_path")),
        },
    }
    bundle_path.write_text(json.dumps(bundle, indent=2, sort_keys=True), encoding="utf-8")
    summary_lines = [
        "# Reroute Bundle",
        "",
        f"- Run: `{run_id}`",
        f"- From: `{metadata.get('driver')}`",
        f"- To: `{target_driver}`",
        f"- Pending approvals: `{len(approvals)}`",
        "",
        "## Materialized Artifacts",
    ]
    for name, path_value in bundle["artifacts"].items():
        summary_lines.append(f"- {name}: `{path_value}`" if path_value else f"- {name}: none")
    summary_lines.extend(
        [
            "",
            "## Transcript Preview",
            bundle["previews"]["transcript"] or "_No transcript preview available._",
            "",
        ]
    )
    summary_path.write_text("\n".join(summary_lines).strip() + "\n", encoding="utf-8")
    return {
        "bundle": bundle,
        "bundle_path": str(bundle_path),
        "summary_path": str(summary_path),
    }


__all__ = ["compile_context_handoffs", "export_reroute_bundle"]

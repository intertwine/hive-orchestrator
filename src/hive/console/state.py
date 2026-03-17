"""Observe-console state loaders for Hive 2.2."""

from __future__ import annotations

import json
from pathlib import Path

from src.hive.control import portfolio_status, recommend_next_task
from src.hive.runs.engine import load_run
from src.hive.scheduler.query import dependency_summary
from src.hive.store.campaigns import list_campaigns
from src.hive.store.events import load_events


def _run_metadata_paths(base_path: Path) -> list[Path]:
    runs_root = base_path / ".hive" / "runs"
    if not runs_root.exists():
        return []
    return sorted(runs_root.glob("run_*/metadata.json"))


def list_runs(
    base_path: Path,
    *,
    project_id: str | None = None,
    driver: str | None = None,
    health: str | None = None,
    campaign_id: str | None = None,
) -> list[dict]:
    """Return normalized runs for the observe console."""
    runs: list[dict] = []
    for metadata_path in _run_metadata_paths(base_path):
        run = load_run(base_path, metadata_path.parent.name)
        if project_id and run.get("project_id") != project_id:
            continue
        if driver and run.get("driver") != driver:
            continue
        if health and run.get("health") != health:
            continue
        if campaign_id and run.get("campaign_id") != campaign_id:
            continue
        runs.append(run)
    runs.sort(key=lambda item: item.get("started_at") or item["id"], reverse=True)
    return runs


def load_run_timeline(base_path: Path, run_id: str) -> list[dict]:
    """Load a per-run event timeline, falling back to the global audit log."""
    timeline_path = base_path / ".hive" / "runs" / run_id / "events.jsonl"
    if timeline_path.exists():
        return [
            json.loads(line)
            for line in timeline_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    return [event for event in load_events(base_path) if event.get("run_id") == run_id]


def _load_json(path_value: str | None) -> dict | list | None:
    if not path_value:
        return None
    path = Path(path_value)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _read_preview(path_value: str | None, *, limit: int = 12000) -> str | None:
    if not path_value:
        return None
    path = Path(path_value)
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")[:limit]


def build_inbox(base_path: Path) -> list[dict]:
    """Return typed attention items for the operator inbox."""
    items: list[dict] = []
    for run in list_runs(base_path):
        status = str(run.get("status", ""))
        if status == "awaiting_review":
            items.append(
                {
                    "kind": "run-review",
                    "priority": 0,
                    "run_id": run["id"],
                    "project_id": run.get("project_id"),
                    "title": f"Review run {run['id']}",
                    "reason": "Evaluator results are ready and a promotion decision is pending.",
                }
            )
        elif status == "awaiting_input":
            items.append(
                {
                    "kind": "run-input",
                    "priority": 1,
                    "run_id": run["id"],
                    "project_id": run.get("project_id"),
                    "title": f"Attach driver for {run['id']}",
                    "reason": f"Driver {run.get('driver', 'unknown')} staged the run and is waiting.",
                }
            )
        elif status in {"escalated", "failed", "blocked"}:
            items.append(
                {
                    "kind": f"run-{status}",
                    "priority": 1,
                    "run_id": run["id"],
                    "project_id": run.get("project_id"),
                    "title": f"{status.title()} run {run['id']}",
                    "reason": run.get("exit_reason") or f"Run status is {status}.",
                }
            )
    for project in dependency_summary(base_path).get("projects", []):
        if project.get("effectively_blocked"):
            items.append(
                {
                    "kind": "project-blocked",
                    "priority": 2,
                    "project_id": project["project_id"],
                    "title": f"Blocked project {project['project_id']}",
                    "reason": "; ".join(project.get("blocking_reasons", [])),
                }
            )
    items.sort(key=lambda item: (item["priority"], item["title"]))
    return items


def build_home_view(base_path: Path) -> dict:
    """Answer the five core operator questions from one payload."""
    status = portfolio_status(base_path)
    deps = dependency_summary(base_path)
    inbox = build_inbox(base_path)
    accepted = [run for run in list_runs(base_path) if run.get("status") == "accepted"][:5]
    return {
        "workspace": str(base_path),
        "recommended_next": recommend_next_task(base_path),
        "projects": status["projects"],
        "active_runs": status["active_runs"],
        "evaluating_runs": status["evaluating_runs"],
        "inbox": inbox,
        "blocked_projects": [
            project for project in deps.get("projects", []) if project.get("effectively_blocked")
        ],
        "recent_accepts": accepted,
        "recent_events": status["recent_events"],
        "campaigns": [
            {
                "id": campaign.id,
                "title": campaign.title,
                "goal": campaign.goal,
                "status": campaign.status,
                "driver": campaign.driver,
                "brief_cadence": campaign.brief_cadence,
                "project_ids": campaign.project_ids,
            }
            for campaign in list_campaigns(base_path)
        ],
    }


def load_run_detail(base_path: Path, run_id: str) -> dict:
    """Return the detail payload for a single run."""
    run = load_run(base_path, run_id)
    run_root = base_path / ".hive" / "runs" / run_id
    timeline = load_run_timeline(base_path, run_id)
    context_manifest = _load_json(run.get("context_manifest_path")) or {}
    changed_files = _load_json(run.get("workspace_changed_files_path")) or {}
    driver_metadata = _load_json(run.get("driver_metadata_path")) or {}
    steering_history = [
        event for event in timeline if str(event.get("type", "")).startswith("steering.")
    ]
    compiled_entries = list(context_manifest.get("entries") or [])
    memory_entries = [entry for entry in compiled_entries if entry.get("source_type") == "memory"]
    search_entries = [entry for entry in compiled_entries if entry.get("source_type") == "search-hit"]
    skill_entries = [
        entry
        for entry in compiled_entries
        if entry.get("source_type") in {"skill", "skill-meta", "skills"}
    ]
    search_hits = _load_json(str(run_root / "context" / "compiled" / "search-hits.json")) or {}
    skills_manifest = _load_json(str(run_root / "context" / "compiled" / "skills-manifest.json")) or {}
    artifacts = {
        "plan": run.get("plan_path"),
        "launch": run.get("launch_path"),
        "context_manifest": run.get("context_manifest_path"),
        "context_compiled_dir": run.get("context_compiled_dir"),
        "transcript": run.get("transcript_path"),
        "patch": run.get("workspace_patch_path") or run.get("patch_path"),
        "changed_files": run.get("workspace_changed_files_path"),
        "summary": run.get("summary_path"),
        "review": run.get("review_path"),
        "events": run.get("events_path"),
        "logs": run.get("logs_dir"),
        "run_brief": str(run_root / "context" / "compiled" / "run-brief.md"),
        "skills_manifest": str(run_root / "context" / "compiled" / "skills-manifest.json"),
        "search_hits": str(run_root / "context" / "compiled" / "search-hits.json"),
        "stdout": str(run_root / "logs" / "stdout.txt"),
        "stderr": str(run_root / "logs" / "stderr.txt"),
    }
    promotion_decision = run.get("metadata_json", {}).get("promotion_decision")
    return {
        "run": run,
        "timeline": timeline,
        "context_manifest": context_manifest,
        "changed_files": changed_files,
        "context_entries": compiled_entries,
        "memory_entries": memory_entries,
        "search_entries": search_entries,
        "skill_entries": skill_entries,
        "inspector": {
            "memory_entries": memory_entries,
            "skill_entries": skill_entries,
            "search_entries": search_entries,
            "search_hits": search_hits.get("results", []),
            "skills_manifest": skills_manifest,
            "outputs": context_manifest.get("outputs", []),
        },
        "steering_history": steering_history,
        "artifacts": artifacts,
        "driver_metadata": driver_metadata,
        "promotion_decision": promotion_decision,
        "artifact_preview": {
            "run_brief": _read_preview(artifacts["run_brief"]),
            "review_summary": _read_preview(run.get("summary_path")),
            "review_notes": _read_preview(run.get("review_path")),
            "diff": _read_preview(run.get("workspace_patch_path") or run.get("patch_path")),
            "stdout": _read_preview(artifacts["stdout"]),
            "stderr": _read_preview(artifacts["stderr"]),
        },
        "evaluations": run.get("metadata_json", {}).get("evaluations", []),
    }

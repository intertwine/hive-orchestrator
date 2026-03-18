"""Run path helpers."""

from __future__ import annotations

from pathlib import Path


def _task_display(task_id: str) -> str:
    suffix = task_id.removeprefix("task_")
    return f"t-{suffix[:8].lower()}"


def run_dir(path: str | Path | None, run_id: str) -> Path:
    """Return the run artifact directory."""
    return Path(path or Path.cwd()).resolve() / ".hive" / "runs" / run_id


def metadata_path(path: str | Path | None, run_id: str) -> Path:
    """Return the canonical run metadata path."""
    return run_dir(path, run_id) / "metadata.json"


def branch_name(project_slug: str, task_id: str, run_id: str) -> str:
    """Return the Git branch name used for a run."""
    return f"hive/{project_slug}/{_task_display(task_id)}/{run_id}"


def run_paths(run_directory: Path) -> dict[str, Path]:
    """Return the standard run artifact paths."""
    plan_dir = run_directory / "plan"
    review_dir = run_directory / "review"
    context_dir = run_directory / "context"
    transcript_dir = run_directory / "transcript"
    workspace_dir = run_directory / "workspace"
    driver_dir = run_directory / "driver"
    logs_dir = run_directory / "logs"
    eval_dir = run_directory / "eval"
    for directory in (
        plan_dir,
        review_dir,
        context_dir / "compiled",
        transcript_dir / "raw",
        workspace_dir,
        driver_dir,
        logs_dir,
        eval_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    return {
        "plan_path": plan_dir / "plan.md",
        "plan_json_path": plan_dir / "plan.json",
        "legacy_plan_json_path": run_directory / "plan.json",
        "launch_path": run_directory / "launch.json",
        "summary_path": review_dir / "summary.md",
        "legacy_summary_path": run_directory / "summary.md",
        "review_path": review_dir / "review.md",
        "legacy_review_path": run_directory / "review.md",
        "patch_path": workspace_dir / "patch.diff",
        "legacy_patch_path": run_directory / "patch.diff",
        "changed_files_path": workspace_dir / "changed_files.json",
        "command_log_path": logs_dir / "command-log.jsonl",
        "stdout_path": logs_dir / "stdout.txt",
        "stderr_path": logs_dir / "stderr.txt",
        "logs_dir": logs_dir,
        "eval_dir": eval_dir,
        "transcript_path": transcript_dir / "normalized.jsonl",
        "transcript_raw_dir": transcript_dir / "raw",
        "driver_metadata_path": driver_dir / "driver-metadata.json",
        "driver_handles_path": driver_dir / "handles.json",
        "events_path": run_directory / "events.jsonl",
    }

def artifact_payload(metadata: dict) -> dict[str, object]:
    """Return the normalized artifact map for a run."""
    return {
        "plan": metadata.get("plan_path"),
        "launch": metadata.get("launch_path"),
        "context_manifest": metadata.get("context_manifest_path"),
        "context_compiled_dir": metadata.get("context_compiled_dir"),
        "transcript": metadata.get("transcript_path"),
        "transcript_raw_dir": metadata.get("transcript_raw_dir"),
        "patch": metadata.get("workspace_patch_path") or metadata.get("patch_path"),
        "changed_files": metadata.get("workspace_changed_files_path"),
        "summary": metadata.get("summary_path"),
        "review": metadata.get("review_path"),
        "driver_metadata": metadata.get("driver_metadata_path"),
        "driver_handles": metadata.get("driver_handles_path"),
        "events": metadata.get("events_path"),
        "logs": metadata.get("logs_dir"),
    }

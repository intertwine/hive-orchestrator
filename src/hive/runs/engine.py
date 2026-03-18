"""Hive 2.0 run engine."""

from __future__ import annotations

from datetime import datetime
from fnmatch import fnmatch
from hashlib import sha256
from pathlib import Path

from src.hive.drivers import RunHandle, RunLaunchRequest
from src.hive.models.program import ProgramRecord
from src.hive.runs.lifecycle import (
    accept_run as _accept_run_impl,
    cleanup_run as _cleanup_run_impl,
    cleanup_terminal_runs as _cleanup_terminal_runs_impl,
    escalate_run as _escalate_run_impl,
    eval_run as _eval_run_impl,
    promote_run as _promote_run_impl,
    reject_run as _reject_run_impl,
    run_artifacts as _run_artifacts_impl,
    start_run as _start_run_impl,
    steer_run as _steer_run_impl,
)
from src.hive.runs.metadata import load_run as _load_run_impl, save_run as _save_run_impl
from src.hive.runs.driver_state import (
    _active_driver_handle as _active_driver_handle_impl,
    _append_transcript_entry as _append_transcript_entry_impl,
    _build_reroute_launch_request as _build_reroute_launch_request_impl,
    _emit_context_compiled_events as _emit_context_compiled_events_impl,
    _load_driver_handles as _load_driver_handles_impl,
    _record_driver_status as _record_driver_status_impl,
    _record_steering_history as _record_steering_history_impl,
    _save_driver_handles as _save_driver_handles_impl,
    _steering_event_type as _steering_event_type_impl,
)
from src.hive.runs.paths import (
    artifact_payload as _artifact_payload_impl,
    branch_name as _branch_name_impl,
    metadata_path as _metadata_path_impl,
    run_dir as _run_dir_impl,
    run_paths as _run_paths_impl,
    _task_display as _task_display_impl,
)
from src.hive.runs.program import (
    _load_run_program as _load_run_program_impl,
    _preflight_program_for_run as _preflight_program_for_run_impl,
    _run_program_policy as _run_program_policy_impl,
    load_program as _load_program_impl,
)
from src.hive.runs.state import (
    _artifact_exists as _artifact_exists_impl,
    _filtered_dirty_paths as _filtered_dirty_paths_impl,
    _parse_iso as _parse_iso_impl,
    _promotion_decision as _promotion_decision_impl,
    _read_command_log as _read_command_log_impl,
    _refresh_workspace_state as _refresh_workspace_state_impl,
    _task_title as _task_title_impl,
    _write_review_and_summary as _write_review_and_summary_impl,
)


def load_program(project_path: Path) -> ProgramRecord:
    """Load and validate PROGRAM.md."""
    return _load_program_impl(project_path)


def _program_sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _load_run_program(metadata: dict) -> ProgramRecord:
    """Load the recorded run contract and reject policy drift."""
    return _load_run_program_impl(metadata)


def _preflight_program_for_run(root: Path, project_path: Path) -> ProgramRecord:
    """Validate the run contract and repo state before scaffolding."""
    return _preflight_program_for_run_impl(root, project_path)


def _run_dir(path: str | Path | None, run_id: str) -> Path:
    return _run_dir_impl(path, run_id)


def _metadata_path(path: str | Path | None, run_id: str) -> Path:
    return _metadata_path_impl(path, run_id)


def _task_display(task_id: str) -> str:
    return _task_display_impl(task_id)


def _branch_name(project_slug: str, task_id: str, run_id: str) -> str:
    return _branch_name_impl(project_slug, task_id, run_id)


def _read_command_log(command_log_path: Path) -> list[dict]:
    return _read_command_log_impl(command_log_path)


def _parse_iso(value: str | None) -> datetime | None:
    return _parse_iso_impl(value)


def _matches_path(path: str, pattern: str) -> bool:
    return fnmatch(path, pattern)


def _refresh_workspace_state(root: Path, metadata: dict) -> dict[str, object]:
    return _refresh_workspace_state_impl(root, metadata)


def _task_title(metadata: dict) -> str:
    return _task_title_impl(metadata)


def _filtered_dirty_paths(root: Path, metadata: dict) -> dict[str, list[str]]:
    """Filter local manager-generated artifacts out of dirty-path checks."""
    return _filtered_dirty_paths_impl(root, metadata)


def _artifact_exists(path_value: str | None) -> bool:
    return _artifact_exists_impl(path_value)


def _promotion_decision(program: ProgramRecord, metadata: dict) -> dict[str, object]:
    return _promotion_decision_impl(program, metadata)


def _write_review_and_summary(metadata: dict, promotion: dict[str, object]) -> None:
    _write_review_and_summary_impl(metadata, promotion)


def _run_paths(run_directory: Path) -> dict[str, Path]:
    return _run_paths_impl(run_directory)


def _run_program_policy(program: ProgramRecord) -> dict[str, object]:
    return _run_program_policy_impl(program)


def _emit_context_compiled_events(
    root: Path,
    *,
    run_id: str,
    task_id: str,
    project_id: str,
    manifest_path: str,
) -> None:
    _emit_context_compiled_events_impl(
        root,
        run_id=run_id,
        task_id=task_id,
        project_id=project_id,
        manifest_path=manifest_path,
    )


def _append_transcript_entry(path: Path, record: dict[str, object]) -> None:
    _append_transcript_entry_impl(path, record)


def _load_driver_handles(metadata: dict) -> dict[str, object]:
    return _load_driver_handles_impl(metadata)


def _save_driver_handles(metadata: dict, handles: dict[str, object]) -> None:
    _save_driver_handles_impl(metadata, handles)


def _active_driver_handle(metadata: dict) -> RunHandle:
    return _active_driver_handle_impl(metadata)


def _record_driver_status(metadata: dict, status: dict[str, object]) -> None:
    _record_driver_status_impl(metadata, status)


def _record_steering_history(*args, **kwargs) -> dict[str, object]:
    return _record_steering_history_impl(*args, **kwargs)


def _steering_event_type(action: str) -> str:
    return _steering_event_type_impl(action)


def _build_reroute_launch_request(
    root: Path,
    metadata: dict,
    *,
    driver_name: str,
    model: str | None = None,
) -> RunLaunchRequest:
    return _build_reroute_launch_request_impl(
        root,
        metadata,
        driver_name=driver_name,
        model=model,
    )


def _artifact_payload(metadata: dict) -> dict[str, object]:
    return _artifact_payload_impl(metadata)


def start_run(*args, **kwargs):
    """Start a governed run."""
    return _start_run_impl(*args, **kwargs)


def load_run(path: str | Path | None, run_id: str) -> dict:
    """Load run metadata."""
    return _load_run_impl(path, run_id)


def _save_run(path: str | Path | None, run_id: str, metadata: dict) -> dict:
    return _save_run_impl(path, run_id, metadata)


def eval_run(*args, **kwargs):
    """Evaluate a governed run."""
    return _eval_run_impl(*args, **kwargs)


def accept_run(*args, **kwargs):
    """Accept a governed run after promotion gates pass."""
    return _accept_run_impl(*args, **kwargs)


def run_artifacts(*args, **kwargs):
    """Return a run's canonical artifact map."""
    return _run_artifacts_impl(*args, **kwargs)


def promote_run(*args, **kwargs):
    """Promote an accepted run back into the workspace branch."""
    return _promote_run_impl(*args, **kwargs)


def reject_run(*args, **kwargs):
    """Reject a run and restore the task to ready."""
    return _reject_run_impl(*args, **kwargs)


def escalate_run(*args, **kwargs):
    """Escalate a run for human review."""
    return _escalate_run_impl(*args, **kwargs)


def steer_run(*args, **kwargs):
    """Apply a typed steering action to a run."""
    return _steer_run_impl(*args, **kwargs)


def cleanup_run(*args, **kwargs):
    """Remove a terminal run's linked worktree."""
    return _cleanup_run_impl(*args, **kwargs)


def cleanup_terminal_runs(*args, **kwargs):
    """Remove linked worktrees for all terminal runs in the workspace."""
    return _cleanup_terminal_runs_impl(*args, **kwargs)

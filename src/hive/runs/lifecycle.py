"""Run lifecycle helpers for governed execution."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import cast

from src.hive.clock import utc_now_iso
from src.hive.constants import RUN_ACTIVE_STATUSES, RUN_TERMINAL_STATUSES
from src.hive.drivers import RunBudget, RunLaunchRequest, RunWorkspace, SteeringRequest, get_driver
from src.hive.ids import new_id
from src.hive.models.run import RunRecord
from src.hive.retrieval_trace import build_retrieval_artifacts
from src.hive.runtime.approvals import (
    bridge_approval_resolution as _bridge_approval_resolution,
    pending_approvals,
    resolve_approval,
)
from src.hive.runtime.capabilities import CapabilitySnapshot
from src.hive.runtime.runpack import (
    runtime_manifest,
    sync_runtime_status_artifacts,
    write_runtime_scaffold,
)
from src.hive.sandbox import resolve_sandbox_policy
from src.hive.runs.context import compile_run_context
from src.hive.runs.evaluators import run_evaluator, validate_evaluator_command
from src.hive.runs.executors import get_executor
from src.hive.runs.metadata import load_run, save_run
from src.hive.runs.metadata import run_record_to_json
from src.hive.runs.paths import artifact_payload as _artifact_payload_impl
from src.hive.runs.paths import branch_name as _branch_name_impl
from src.hive.runs.paths import metadata_path as _metadata_path_impl
from src.hive.runs.paths import run_dir as _run_dir_impl
from src.hive.runs.paths import run_paths as _run_paths_impl
from src.hive.runs.paths import _task_display as _task_display_impl
from src.hive.runs.program import (
    _load_run_program as _load_run_program_impl,
    _preflight_program_for_run as _preflight_program_for_run_impl,
    _program_sha,
    _run_program_policy as _run_program_policy_impl,
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
from src.hive.runs.steering import steer_run as _steer_run_impl
from src.hive.runs.driver_state import (
    _active_driver_handle as _active_driver_handle_impl,
    _append_transcript_entry as _append_transcript_entry_impl,
    _build_reroute_launch_request as _build_reroute_launch_request_impl,
    _emit_context_compiled_events as _emit_context_compiled_events_impl,
    _load_driver_handles as _load_driver_handles_impl,
    _refresh_live_driver_status as _refresh_live_driver_status_impl,
    _record_driver_status as _record_driver_status_impl,
    _record_steering_history as _record_steering_history_impl,
    _save_driver_handles as _save_driver_handles_impl,
    _steering_event_type as _steering_event_type_impl,
)
from src.hive.runs.worktree import (
    commit_paths,
    create_run_worktree,
    current_branch,
    current_head,
    delete_branch,
    merge_branch,
    remove_worktree,
    restore_derived_state,
)
from src.hive.store.events import emit_event
from src.hive.store.layout import runs_dir, worktrees_dir
from src.hive.store.projects import get_project
from src.hive.store.task_files import get_task, save_task


def _load_run_program(metadata: dict):
    return _load_run_program_impl(metadata)


def _preflight_program_for_run(root: Path, project_path: Path):
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


def _refresh_workspace_state(root: Path, metadata: dict) -> dict[str, object]:
    return _refresh_workspace_state_impl(root, metadata)


def _task_title(metadata: dict) -> str:
    return _task_title_impl(metadata)


def _filtered_dirty_paths(root: Path, metadata: dict) -> dict[str, list[str]]:
    return _filtered_dirty_paths_impl(root, metadata)


def _artifact_exists(path_value: str | None) -> bool:
    return _artifact_exists_impl(path_value)


def _promotion_decision(program, metadata: dict) -> dict[str, object]:
    return _promotion_decision_impl(program, metadata)


def _write_review_and_summary(metadata: dict, promotion: dict[str, object]) -> None:
    _write_review_and_summary_impl(metadata, promotion)


def _run_paths(run_directory: Path) -> dict[str, Path]:
    return _run_paths_impl(run_directory)


def _run_program_policy(program) -> dict[str, object]:
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


def _active_driver_handle(metadata: dict):
    return _active_driver_handle_impl(metadata)


def _record_driver_status(metadata: dict, status: dict[str, object]) -> None:
    _record_driver_status_impl(metadata, status)


def _refresh_live_driver_status(metadata: dict) -> dict[str, object] | None:
    return _refresh_live_driver_status_impl(Path.cwd(), metadata)


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
    return _record_steering_history_impl(
        metadata,
        action=action,
        actor=actor,
        reason=reason,
        note=note,
        target=target,
        budget_delta=budget_delta,
        ack=ack,
    )


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


def _selected_pending_approval(
    pending: list[dict[str, object]],
    request: SteeringRequest,
) -> dict[str, object] | None:
    target_id = str((request.target or {}).get("approval_id") or "").strip()
    if target_id:
        for item in pending:
            if str(item.get("approval_id") or "") == target_id:
                return cast(dict[str, object], item)
        raise FileNotFoundError(f"Pending approval not found: {target_id}")
    if not pending:
        return None
    if len(pending) > 1:
        raise ValueError("Multiple pending approvals require an explicit approval_id.")
    return cast(dict[str, object], pending[0])


def start_run(
    path: str | Path | None,
    task_id: str,
    *,
    driver_name: str | None = None,
    model: str | None = None,
    campaign_id: str | None = None,
    profile: str = "default",
    attach_native_session_ref: str | None = None,
    scheduler_candidate_set: dict[str, object] | None = None,
    scheduler_decision: dict[str, object] | None = None,
) -> RunRecord:
    root = Path(path or Path.cwd()).resolve()
    task = get_task(root, task_id)
    if task.status not in {"proposed", "ready", "claimed"}:
        raise ValueError(f"Cannot start run on task with status {task.status!r}")
    project = get_project(root, task.project_id)
    program = _preflight_program_for_run(root, project.program_path)
    executor_name = program.metadata.get("default_executor", "local")
    get_executor(executor_name)
    driver = get_driver(driver_name or "local")
    driver_info = driver.probe()

    run_id = new_id("run")
    run_directory = _run_dir(root, run_id)
    branch_name = _branch_name(project.slug, task.id, run_id)
    base_branch = current_branch(root)
    worktree_root = worktrees_dir(root) / run_id
    sandbox_policy = resolve_sandbox_policy(
        worktree_path=str(worktree_root),
        artifacts_path=str(run_directory),
        profile=profile,
    )
    worktree_path = create_run_worktree(
        root,
        branch_name=branch_name,
        worktree_path=worktree_root,
    )
    base_commit = current_head(root)

    run_directory.mkdir(parents=True, exist_ok=True)
    paths = _run_paths(run_directory)
    context_bundle = compile_run_context(
        root,
        run_id=run_id,
        project=project,
        task=task,
        run_directory=run_directory,
        driver=driver.name,
        profile=profile,
    )
    capability_snapshot = driver_info.capability_snapshot or CapabilitySnapshot(driver=driver.name)
    manifest = runtime_manifest(
        run_id=run_id,
        task_id=task.id,
        project_id=project.id,
        campaign_id=campaign_id,
        driver=driver.name,
        driver_mode=capability_snapshot.effective.launch_mode,
        sandbox_backend=sandbox_policy.backend,
        sandbox_profile=sandbox_policy.profile,
        repo_root=str(root),
        worktree_path=str(worktree_path),
        base_branch=base_branch,
        compiled_context_manifest=str(context_bundle["manifest_path"]),
        capability_snapshot_path=str(paths["capability_snapshot_path"]),
        scheduler_decision_path=str(paths["scheduler_decision_path"]),
        retrieval_trace_path=str(paths["retrieval_trace_path"]),
    )
    paths.update(
        write_runtime_scaffold(
            run_directory,
            manifest=manifest,
            capability_snapshot=capability_snapshot,
            sandbox_policy=sandbox_policy,
        )
    )
    candidates = list(context_bundle.get("retrieval_candidates") or [])
    dense_count = sum(1 for c in candidates if c.get("dense_match"))
    retrieval_hits, retrieval_trace = build_retrieval_artifacts(
        str(context_bundle.get("query_text") or ""),
        selected_hits=list(context_bundle.get("search_hits") or []),
        candidate_hits=candidates,
        dense_candidate_count=dense_count,
    )
    paths["retrieval_hits_path"].write_text(
        json.dumps(retrieval_hits, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    paths["retrieval_trace_path"].write_text(
        json.dumps(retrieval_trace, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    default_candidate_set = {
        "candidates": [
            {
                "candidate_id": task.id,
                "lane": "exploit",
                "scores": {
                    "campaign_alignment": 1.0 if campaign_id else 0.5,
                    "readiness": 1.0,
                },
                "recommended_driver": driver.name,
                "recommended_sandbox": sandbox_policy.backend,
            }
        ]
    }
    default_decision = {
        "selected_candidate_id": task.id,
        "reason": (
            "run started from an explicit task launch"
            if campaign_id is None
            else "run launched under the current campaign task selection"
        ),
    }
    paths["scheduler_candidate_set_path"].write_text(
        json.dumps(scheduler_candidate_set or default_candidate_set, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    paths["scheduler_decision_path"].write_text(
        json.dumps(scheduler_decision or default_decision, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    paths["plan_path"].write_text(
        "\n".join(
            [
                "# Run plan",
                "",
                f"Task: `{task.title}`",
                f"Driver: `{driver.name}`",
                f"Branch: `{branch_name}`",
                f"Worktree: `{worktree_path}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    paths["plan_json_path"].write_text(
        json.dumps(
            {
                "task_id": task.id,
                "title": task.title,
                "branch_name": branch_name,
                "worktree_path": str(worktree_path),
                "executor": executor_name,
                "driver": driver.name,
                "base_branch": base_branch,
                "base_commit": base_commit,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    paths["legacy_plan_json_path"].write_text(
        paths["plan_json_path"].read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    paths["patch_path"].write_text("", encoding="utf-8")
    paths["legacy_patch_path"].write_text("", encoding="utf-8")
    paths["changed_files_path"].write_text('{\n  "files": []\n}\n', encoding="utf-8")
    paths["summary_path"].write_text(
        "# Summary\n\nPending evaluator results.\n",
        encoding="utf-8",
    )
    paths["legacy_summary_path"].write_text(
        "# Summary\n\nPending evaluator results.\n",
        encoding="utf-8",
    )
    paths["review_path"].write_text(
        "# Review\n\nPending promotion decision.\n",
        encoding="utf-8",
    )
    paths["legacy_review_path"].write_text(
        "# Review\n\nPending promotion decision.\n",
        encoding="utf-8",
    )
    paths["command_log_path"].write_text("", encoding="utf-8")
    paths["stdout_path"].write_text("", encoding="utf-8")
    paths["stderr_path"].write_text("", encoding="utf-8")
    paths["transcript_path"].write_text("", encoding="utf-8")
    paths["trajectory_path"].write_text("", encoding="utf-8")
    paths["steering_path"].write_text("", encoding="utf-8")
    paths["approval_channel_path"].write_text("", encoding="utf-8")

    launch_request = RunLaunchRequest(
        run_id=run_id,
        task_id=task.id,
        project_id=project.id,
        campaign_id=campaign_id,
        driver=driver.name,
        model=model,
        budget=RunBudget(
            max_tokens=int(program.metadata.get("budgets", {}).get("max_tokens", 0)),
            max_cost_usd=float(program.metadata.get("budgets", {}).get("max_cost_usd", 0.0)),
            max_wall_minutes=int(
                float(program.metadata.get("budgets", {}).get("max_wall_clock_minutes", 0))
            ),
        ),
        workspace=RunWorkspace(
            repo_root=str(root),
            worktree_path=str(worktree_path),
            base_branch=base_branch,
        ),
        compiled_context_path=str(context_bundle["compiled_dir"]),
        artifacts_path=str(run_directory),
        program_policy=_run_program_policy(program),
        metadata={
            "initiator": "human",
            "source": "hive run start",
            "task_title": task.title,
            "approval_channel": str(paths["approval_channel_path"]),
            "attach_native_session_ref": attach_native_session_ref,
            "handoff_manifest_path": context_bundle["handoff_bundle"].get("manifest_path"),
            "handoff_summary_path": context_bundle["handoff_bundle"].get("summary_path"),
            "handoff_runs": list(context_bundle["handoff_bundle"].get("items") or []),
        },
    )
    handle = driver.launch(launch_request)
    run_status = driver.status(handle)
    capability_snapshot = (
        CapabilitySnapshot.from_dict(handle.metadata["capability_snapshot"])
        if isinstance(handle.metadata.get("capability_snapshot"), dict)
        else capability_snapshot
    )
    manifest["driver_mode"] = capability_snapshot.effective.launch_mode
    paths["manifest_path"].write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    paths["launch_path"].write_text(
        json.dumps(launch_request.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    paths["driver_metadata_path"].write_text(
        json.dumps(driver_info.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    paths["driver_handles_path"].write_text(
        json.dumps(
            {"active": handle.to_dict(), "history": [handle.to_dict()]},
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    _append_transcript_entry(
        paths["transcript_path"],
        {
            "ts": utc_now_iso(),
            "kind": "system",
            "driver": driver.name,
            "message": run_status.progress.message,
            "state": run_status.state,
        },
    )

    run = RunRecord(
        id=run_id,
        project_id=project.id,
        task_id=task.id,
        driver=driver.name,
        driver_handle=handle.driver_handle,
        campaign_id=campaign_id,
        status=run_status.state,
        health=run_status.health,
        executor=executor_name,
        branch_name=branch_name,
        worktree_path=str(worktree_path),
        program_path=str(project.program_path),
        program_sha256=_program_sha(project.program_path),
        runtime_manifest_path=str(paths["manifest_path"]),
        capability_snapshot_path=str(paths["capability_snapshot_path"]),
        sandbox_policy_path=str(paths["sandbox_policy_path"]),
        launch_path=str(paths["launch_path"]),
        context_manifest_path=str(context_bundle["manifest_path"]),
        context_compiled_dir=str(context_bundle["compiled_dir"]),
        transcript_path=str(paths["transcript_path"]),
        transcript_ndjson_path=str(paths["transcript_ndjson_path"]),
        transcript_raw_dir=str(paths["transcript_raw_dir"]),
        trajectory_path=str(paths["trajectory_path"]),
        steering_path=str(paths["steering_path"]),
        workspace_patch_path=str(paths["patch_path"]),
        workspace_changed_files_path=str(paths["changed_files_path"]),
        driver_metadata_path=str(paths["driver_metadata_path"]),
        driver_handles_path=str(paths["driver_handles_path"]),
        approval_channel_path=str(paths["approval_channel_path"]),
        events_path=str(paths["events_path"]),
        events_ndjson_path=str(paths["events_ndjson_path"]),
        approvals_path=str(paths["approvals_path"]),
        retrieval_trace_path=str(paths["retrieval_trace_path"]),
        retrieval_hits_path=str(paths["retrieval_hits_path"]),
        handoff_manifest_path=context_bundle["handoff_bundle"].get("manifest_path"),
        scheduler_candidate_set_path=str(paths["scheduler_candidate_set_path"]),
        scheduler_decision_path=str(paths["scheduler_decision_path"]),
        eval_results_path=str(paths["eval_results_path"]),
        plan_path=str(paths["plan_path"]),
        summary_path=str(paths["summary_path"]),
        review_path=str(paths["review_path"]),
        patch_path=str(paths["patch_path"]),
        command_log_path=str(paths["command_log_path"]),
        logs_dir=str(paths["logs_dir"]),
        final_path=str(paths["final_path"]),
        metadata={
            "task_title": task.title,
            "base_branch": base_branch,
            "base_commit": base_commit,
            "touched_paths": [],
            "commands": [],
            "command_count": 0,
            "driver_status": run_status.to_dict(),
            "context_manifest": context_bundle["manifest"],
            "runtime_v2": {
                "manifest": manifest,
                "sandbox_policy": sandbox_policy.to_dict(),
                "capability_snapshot": capability_snapshot.to_dict(),
                "approval_channel": str(paths["approval_channel_path"]),
                "handoff_manifest_path": context_bundle["handoff_bundle"].get("manifest_path"),
                "handoff_summary_path": context_bundle["handoff_bundle"].get("summary_path"),
                "handoff_runs": list(context_bundle["handoff_bundle"].get("items") or []),
                "scheduler_candidate_set": scheduler_candidate_set or default_candidate_set,
                "scheduler_decision": scheduler_decision or default_decision,
            },
        },
    )
    run_file = _metadata_path(root, run_id)
    run_file.write_text(run_record_to_json(run), encoding="utf-8")
    task.status = "in_progress"
    save_task(root, task)
    sync_runtime_status_artifacts(run.to_dict(), task_status=task.status)
    emit_event(
        root,
        actor={"kind": "system", "id": "hive"},
        entity_type="run",
        entity_id=run.id,
        event_type="run.queued",
        source="run.start",
        payload={
            "task_id": task.id,
            "branch_name": branch_name,
            "executor": executor_name,
            "driver": driver.name,
        },
        run_id=run.id,
        task_id=task.id,
        project_id=project.id,
    )
    _emit_context_compiled_events(
        root,
        run_id=run.id,
        task_id=task.id,
        project_id=project.id,
        manifest_path=str(context_bundle["manifest_path"]),
    )
    emit_event(
        root,
        actor={"kind": "system", "id": f"driver:{driver.name}"},
        entity_type="run",
        entity_id=run.id,
        event_type="run.launch_started",
        source="run.start",
        payload={"launch_path": str(paths["launch_path"])},
        run_id=run.id,
        task_id=task.id,
        project_id=project.id,
    )
    emit_event(
        root,
        actor={"kind": "system", "id": f"driver:{driver.name}"},
        entity_type="run",
        entity_id=run.id,
        event_type="run.launched",
        source="run.start",
        payload={"handle": handle.to_dict()},
        run_id=run.id,
        task_id=task.id,
        project_id=project.id,
    )
    emit_event(
        root,
        actor={"kind": "system", "id": f"driver:{driver.name}"},
        entity_type="run",
        entity_id=run.id,
        event_type="run.status.changed",
        source="run.start",
        payload={"state": run_status.state, "health": run_status.health},
        run_id=run.id,
        task_id=task.id,
        project_id=project.id,
    )
    emit_event(
        root,
        actor={"kind": "system", "id": "hive"},
        entity_type="run",
        entity_id=run.id,
        event_type="sandbox.selected",
        source="run.start",
        payload=sandbox_policy.to_dict(),
        run_id=run.id,
        task_id=task.id,
        project_id=project.id,
        campaign_id=campaign_id,
    )
    if run_status.state == "awaiting_input":
        emit_event(
            root,
            actor={"kind": "system", "id": f"driver:{driver.name}"},
            entity_type="run",
            entity_id=run.id,
            event_type="run.awaiting_input",
            source="run.start",
            payload={"waiting_on": run_status.waiting_on, "message": run_status.progress.message},
            run_id=run.id,
            task_id=task.id,
            project_id=project.id,
        )
    return run


def refresh_run_driver_state(path: str | Path | None, run_id: str) -> dict:
    """Refresh persisted status for live driver-backed runs."""
    root = Path(path or Path.cwd()).resolve()
    metadata = load_run(root, run_id)
    refreshed = _refresh_live_driver_status_impl(root, metadata)
    if refreshed is None:
        return metadata

    current = refreshed["current"]
    previous = refreshed["previous"]
    metadata["status"] = current.get("state", metadata.get("status"))
    metadata["health"] = current.get("health", metadata.get("health"))
    if metadata["status"] in {"completed_candidate", "failed", "cancelled"}:
        metadata["finished_at"] = metadata.get("finished_at") or utc_now_iso()
    save_run(root, run_id, metadata)
    task_status = None
    if metadata.get("task_id"):
        task_status = get_task(root, metadata["task_id"]).status
    sync_runtime_status_artifacts(metadata, task_status=task_status)
    if previous.get("state") != current.get("state") or previous.get("health") != current.get(
        "health"
    ):
        emit_event(
            root,
            actor={"kind": "system", "id": f"driver:{metadata.get('driver', 'unknown')}"},
            entity_type="run",
            entity_id=run_id,
            event_type="run.status.changed",
            source="run.status",
            payload={"state": metadata.get("status"), "health": metadata.get("health")},
            run_id=run_id,
            task_id=metadata.get("task_id"),
            project_id=metadata.get("project_id"),
            campaign_id=metadata.get("campaign_id"),
        )
        event_type = {
            "completed_candidate": "run.completed_candidate",
            "failed": "run.failed",
            "cancelled": "run.cancelled",
        }.get(str(current.get("state") or ""))
        if event_type:
            emit_event(
                root,
                actor={"kind": "system", "id": f"driver:{metadata.get('driver', 'unknown')}"},
                entity_type="run",
                entity_id=run_id,
                event_type=event_type,
                source="run.status",
                payload={"driver_status": current},
                run_id=run_id,
                task_id=metadata.get("task_id"),
                project_id=metadata.get("project_id"),
                campaign_id=metadata.get("campaign_id"),
            )
    return metadata


def eval_run(path: str | Path | None, run_id: str) -> dict:
    root = Path(path or Path.cwd()).resolve()

    metadata = refresh_run_driver_state(root, run_id)
    if metadata.get("status") not in {"running", "awaiting_input", "completed_candidate"}:
        raise ValueError(f"Cannot evaluate run with status {metadata.get('status')!r}")
    program = _load_run_program(metadata)
    run_directory = _run_dir(root, run_id)
    command_log_path = Path(metadata["command_log_path"])
    timeout_seconds = max(
        1,
        int(float(program.metadata.get("budgets", {}).get("max_wall_clock_minutes", 30)) * 60),
    )
    executor = get_executor(
        metadata.get("executor", program.metadata["default_executor"]),
        sandbox_policy=metadata.get("sandbox_policy_path"),
    )
    results = []
    seq = len(_read_command_log(command_log_path)) + 1
    commands_policy = program.metadata.get("commands", {})
    emit_event(
        root,
        actor={"kind": "system", "id": "hive"},
        entity_type="run",
        entity_id=run_id,
        event_type="eval.started",
        source="run.eval",
        payload={},
        run_id=run_id,
        task_id=metadata.get("task_id"),
        project_id=metadata.get("project_id"),
    )
    for evaluator in program.metadata.get("evaluators", []):
        validate_evaluator_command(evaluator["command"], commands_policy)
        result = run_evaluator(
            executor,
            evaluator["command"],
            Path(metadata["worktree_path"]),
            run_directory / "eval",
            evaluator["id"],
            bool(evaluator.get("required", True)),
            command_log_path=command_log_path,
            seq=seq,
            timeout_seconds=timeout_seconds,
        )
        seq += 1
        results.append(result)

    metadata["status"] = "awaiting_review"
    metadata_json = _refresh_workspace_state(root, metadata)
    metadata_json["evaluations"] = results
    promotion = _promotion_decision(program, metadata)
    metadata_json["promotion_decision"] = promotion
    _write_review_and_summary(metadata, promotion)
    save_run(root, run_id, metadata)
    task = get_task(root, metadata["task_id"])
    sync_runtime_status_artifacts(metadata, task_status=task.status)
    emit_event(
        root,
        actor={"kind": "system", "id": "hive"},
        entity_type="run",
        entity_id=run_id,
        event_type="eval.completed",
        source="run.eval",
        payload={"results": results, "promotion_decision": promotion},
        run_id=run_id,
        task_id=metadata.get("task_id"),
        project_id=metadata.get("project_id"),
    )
    emit_event(
        root,
        actor={"kind": "system", "id": "hive"},
        entity_type="run",
        entity_id=run_id,
        event_type="run.completed_candidate",
        source="run.eval",
        payload={"promotion_decision": promotion},
        run_id=run_id,
        task_id=metadata.get("task_id"),
        project_id=metadata.get("project_id"),
    )
    emit_event(
        root,
        actor={"kind": "system", "id": "hive"},
        entity_type="run",
        entity_id=run_id,
        event_type="run.awaiting_review",
        source="run.eval",
        payload={"promotion_decision": promotion},
        run_id=run_id,
        task_id=metadata.get("task_id"),
        project_id=metadata.get("project_id"),
    )
    emit_event(
        root,
        actor={"kind": "system", "id": "hive"},
        entity_type="run",
        entity_id=run_id,
        event_type="review.summary_generated",
        source="run.eval",
        payload={
            "summary_path": metadata.get("summary_path"),
            "review_path": metadata.get("review_path"),
        },
        run_id=run_id,
        task_id=metadata.get("task_id"),
        project_id=metadata.get("project_id"),
    )
    return {"run": metadata, "evaluations": results, "promotion_decision": promotion}


def accept_run(path: str | Path | None, run_id: str) -> dict:
    root = Path(path or Path.cwd()).resolve()

    metadata = load_run(root, run_id)
    if metadata.get("status") != "awaiting_review":
        raise ValueError(f"Cannot accept run with status {metadata.get('status')!r}")

    program = _load_run_program(metadata)
    metadata_json = _refresh_workspace_state(root, metadata)
    promotion = _promotion_decision(program, metadata)
    metadata_json["promotion_decision"] = promotion
    _write_review_and_summary(metadata, promotion)
    if promotion["decision"] != "accept":
        reasons = "; ".join(promotion["reasons"]) or "promotion gates failed"
        save_run(root, run_id, metadata)
        raise ValueError(f"Run cannot be accepted: {reasons}")

    metadata["status"] = "accepted"
    metadata["finished_at"] = utc_now_iso()
    save_run(root, run_id, metadata)
    task = get_task(root, metadata["task_id"])
    auto_close = bool(program.metadata.get("promotion", {}).get("auto_close_task", False))
    task.status = "done" if auto_close else "review"
    task.owner = None
    task.claimed_until = None
    save_task(root, task)
    sync_runtime_status_artifacts(metadata, task_status=task.status)
    emit_event(
        root,
        actor={"kind": "system", "id": "hive"},
        entity_type="run",
        entity_id=run_id,
        event_type="run.accepted",
        source="run.accept",
        payload={"task_id": task.id},
        run_id=run_id,
        task_id=task.id,
        project_id=metadata.get("project_id"),
    )
    return metadata


def run_artifacts(path: str | Path | None, run_id: str) -> dict[str, object]:
    metadata = load_run(path, run_id)
    return {"run": metadata, "artifacts": _artifact_payload_impl(metadata)}


def promote_run(
    path: str | Path | None,
    run_id: str,
    *,
    cleanup_worktree: bool = False,
) -> dict[str, object]:
    root = Path(path or Path.cwd()).resolve()

    metadata = load_run(root, run_id)
    if metadata.get("status") != "accepted":
        raise ValueError(f"Cannot promote run with status {metadata.get('status')!r}")

    branch_name = metadata.get("branch_name")
    if not branch_name:
        raise ValueError(f"Run {run_id} does not have a mergeable branch")

    dirty = _filtered_dirty_paths(root, metadata)
    if dirty["noncanonical"]:
        details = ", ".join(dirty["noncanonical"][:5])
        raise ValueError(
            "Run promotion requires a clean repo outside of canonical Hive state files. "
            f"Dirty paths: {details}"
        )

    title = _task_title(metadata)
    state_commit = commit_paths(
        root,
        paths=dirty["canonical"],
        message=f"Accept {title} run",
    )
    merge_result = merge_branch(root, branch_name=branch_name, message=f"Merge {title} run")
    cleanup_result = None
    worktree_path = metadata.get("worktree_path")
    if cleanup_worktree and worktree_path:
        cleanup_result = cleanup_run(root, run_id)
    can_delete_branch = cleanup_worktree or not worktree_path or not Path(worktree_path).exists()
    if can_delete_branch:
        branch_cleanup = delete_branch(root, branch_name)
    else:
        branch_cleanup = {
            "deleted": False,
            "already_missing": False,
            "branch_name": branch_name,
            "warning": (
                "Branch kept because the linked run worktree still exists. "
                "Re-run promotion with `--cleanup-worktree` or remove the worktree first."
            ),
        }
    derived_cleanup = restore_derived_state(root)

    return {
        "run": metadata,
        "branch_name": branch_name,
        "state_commit": state_commit,
        "merge": merge_result,
        "branch_cleanup": branch_cleanup,
        "cleanup": cleanup_result,
        "derived_cleanup": derived_cleanup,
    }


def reject_run(path: str | Path | None, run_id: str, reason: str | None = None) -> dict:
    root = Path(path or Path.cwd()).resolve()

    metadata = load_run(root, run_id)
    if metadata.get("status") not in RUN_ACTIVE_STATUSES:
        raise ValueError(f"Cannot reject run with status {metadata.get('status')!r}")
    _refresh_workspace_state(root, metadata)
    metadata["status"] = "rejected"
    metadata["finished_at"] = utc_now_iso()
    metadata["exit_reason"] = reason
    save_run(root, run_id, metadata)
    task = get_task(root, metadata["task_id"])
    task.status = "ready"
    task.owner = None
    task.claimed_until = None
    save_task(root, task)
    sync_runtime_status_artifacts(metadata, task_status=task.status)
    emit_event(
        root,
        actor={"kind": "system", "id": "hive"},
        entity_type="run",
        entity_id=run_id,
        event_type="run.rejected",
        source="run.reject",
        payload={"task_id": task.id, "reason": reason},
        run_id=run_id,
        task_id=task.id,
        project_id=metadata.get("project_id"),
    )
    return metadata


def escalate_run(path: str | Path | None, run_id: str, reason: str | None = None) -> dict:
    root = Path(path or Path.cwd()).resolve()

    metadata = load_run(root, run_id)
    if metadata.get("status") not in RUN_ACTIVE_STATUSES:
        raise ValueError(f"Cannot escalate run with status {metadata.get('status')!r}")
    _refresh_workspace_state(root, metadata)
    metadata["status"] = "escalated"
    metadata["finished_at"] = utc_now_iso()
    metadata["exit_reason"] = reason
    save_run(root, run_id, metadata)
    task = get_task(root, metadata["task_id"])
    task.status = "review"
    task.owner = None
    task.claimed_until = None
    save_task(root, task)
    sync_runtime_status_artifacts(metadata, task_status=task.status)
    emit_event(
        root,
        actor={"kind": "system", "id": "hive"},
        entity_type="run",
        entity_id=run_id,
        event_type="run.escalated",
        source="run.escalate",
        payload={"task_id": task.id, "reason": reason},
        run_id=run_id,
        task_id=task.id,
        project_id=metadata.get("project_id"),
    )
    return metadata


def steer_run(
    path: str | Path | None,
    run_id: str,
    request: SteeringRequest,
    *,
    actor: str | None = None,
) -> dict[str, object]:
    root = Path(path or Path.cwd()).resolve()

    metadata = load_run(root, run_id)
    action = request.action
    if action not in {
        "pause",
        "resume",
        "cancel",
        "reroute",
        "note",
        "approve",
        "reject",
    }:
        raise ValueError(f"Unsupported steering action {action!r}")
    if (
        action not in {"note", "approve", "reject"}
        and metadata.get("status") in RUN_TERMINAL_STATUSES
    ):
        raise ValueError(f"Cannot steer terminal run with status {metadata.get('status')!r}")

    if action == "approve":
        pending = pending_approvals(root, run_id)
        selected = _selected_pending_approval(pending, request)
        if selected is not None:
            approval = resolve_approval(
                root,
                run_id,
                str(selected["approval_id"]),
                resolution="approved",
                actor=actor or "operator",
                note=request.note or request.reason,
            )
            driver_ack = _bridge_approval_resolution(
                root,
                metadata,
                approval=cast(dict[str, object], approval),
                action=action,
                actor=actor,
                request=request,
            )
            _record_steering_history(
                metadata,
                action=action,
                actor=actor,
                reason=request.reason,
                note=request.note,
                target=cast(dict[str, object] | None, request.target),
                budget_delta=cast(dict[str, object] | None, request.budget_delta),
                ack=driver_ack,
            )
            save_run(root, run_id, metadata)
            return {
                "run": load_run(root, run_id),
                "action": action,
                "request": request.to_dict(),
                "approval": approval,
                "driver_ack": driver_ack,
            }
        emit_event(
            root,
            actor={"kind": "human", "id": actor or "operator"},
            entity_type="run",
            entity_id=run_id,
            event_type="steering.approve",
            source="run.steer",
            payload={"request": request.to_dict()},
            run_id=run_id,
            task_id=metadata.get("task_id"),
            project_id=metadata.get("project_id"),
            campaign_id=metadata.get("campaign_id"),
        )
        accepted = accept_run(root, run_id)
        accepted_metadata = accepted.setdefault("metadata_json", {})
        accepted_metadata.setdefault("steering_history", []).append(
            _record_steering_history(
                metadata,
                action=action,
                actor=actor,
                reason=request.reason,
                note=request.note,
                target=cast(dict[str, object] | None, request.target),
                budget_delta=cast(dict[str, object] | None, request.budget_delta),
            )
        )
        save_run(root, run_id, accepted)
        return {"run": accepted, "action": action, "request": request.to_dict()}
    if action == "reject":
        pending = pending_approvals(root, run_id)
        selected = _selected_pending_approval(pending, request)
        if selected is not None:
            approval = resolve_approval(
                root,
                run_id,
                str(selected["approval_id"]),
                resolution="rejected",
                actor=actor or "operator",
                note=request.note or request.reason,
            )
            driver_ack = _bridge_approval_resolution(
                root,
                metadata,
                approval=cast(dict[str, object], approval),
                action=action,
                actor=actor,
                request=request,
            )
            _record_steering_history(
                metadata,
                action=action,
                actor=actor,
                reason=request.reason,
                note=request.note,
                target=cast(dict[str, object] | None, request.target),
                budget_delta=cast(dict[str, object] | None, request.budget_delta),
                ack=driver_ack,
            )
            save_run(root, run_id, metadata)
            return {
                "run": load_run(root, run_id),
                "action": action,
                "request": request.to_dict(),
                "approval": approval,
                "driver_ack": driver_ack,
            }
        emit_event(
            root,
            actor={"kind": "human", "id": actor or "operator"},
            entity_type="run",
            entity_id=run_id,
            event_type="steering.reject",
            source="run.steer",
            payload={"request": request.to_dict()},
            run_id=run_id,
            task_id=metadata.get("task_id"),
            project_id=metadata.get("project_id"),
            campaign_id=metadata.get("campaign_id"),
        )
        rejected = reject_run(root, run_id, reason=request.reason)
        rejected_metadata = rejected.setdefault("metadata_json", {})
        rejected_metadata.setdefault("steering_history", []).append(
            _record_steering_history(
                metadata,
                action=action,
                actor=actor,
                reason=request.reason,
                note=request.note,
                target=cast(dict[str, object] | None, request.target),
                budget_delta=cast(dict[str, object] | None, request.budget_delta),
            )
        )
        save_run(root, run_id, rejected)
        return {"run": rejected, "action": action, "request": request.to_dict()}
    return _steer_run_impl(root, run_id, request, actor=actor)


def cleanup_run(path: str | Path | None, run_id: str) -> dict[str, object]:
    root = Path(path or Path.cwd()).resolve()

    metadata = load_run(root, run_id)
    if metadata.get("status") not in RUN_TERMINAL_STATUSES:
        raise ValueError(f"Cannot clean up run with status {metadata.get('status')!r}")
    worktree_path = metadata.get("worktree_path")
    if not worktree_path:
        return {"run_id": run_id, "cleaned": False, "already_missing": True, "path": None}
    result = remove_worktree(root, worktree_path)
    return {
        "run_id": run_id,
        "cleaned": bool(result["removed"]),
        "already_missing": bool(result["already_missing"]),
        "manual_cleanup": bool(result["manual_cleanup"]),
        "path": result["path"],
        "warnings": list(result["warnings"]),
    }


def cleanup_terminal_runs(path: str | Path | None) -> list[dict[str, object]]:
    root = Path(path or Path.cwd()).resolve()

    results: list[dict[str, object]] = []
    for metadata_file in sorted(runs_dir(root).glob("run_*/metadata.json")):
        run_id = metadata_file.parent.name
        metadata = load_run(root, run_id)
        if metadata.get("status") in RUN_TERMINAL_STATUSES:
            results.append(cleanup_run(root, run_id))
    return results

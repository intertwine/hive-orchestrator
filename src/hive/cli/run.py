"""Run, steering, and program Hive CLI commands."""

# pylint: disable=line-too-long,too-many-lines,too-many-locals,too-many-statements
# pylint: disable=too-many-branches,too-many-return-statements

from __future__ import annotations

import sqlite3
from pathlib import Path

from src.hive.cli.common import emit, emit_error
from src.hive.drivers import SteeringRequest
from src.hive.program import add_evaluator_template, doctor_program
from src.hive.runtime import list_approvals
from src.hive.runs.engine import (
    accept_run,
    cleanup_run,
    cleanup_terminal_runs,
    escalate_run,
    eval_run,
    load_run,
    promote_run,
    refresh_run_driver_state,
    reject_run,
    run_artifacts,
    start_run,
    steer_run,
)
from src.hive.store.cache import CacheBusyError
from src.hive.workspace import WorkspaceBusyError, sync_workspace


def dispatch(args, root: Path) -> int:
    """Dispatch run, steer, and program commands."""
    try:
        if args.command == "run":
            if args.run_command in {"start", "launch"}:
                run = start_run(
                    root,
                    args.task_id,
                    driver_name=args.driver,
                    model=args.model,
                    campaign_id=args.campaign_id,
                    profile=args.profile,
                )
                sync_workspace(root)
                return emit({"ok": True, "run": run.to_dict()}, args.json)
            if args.run_command == "show":
                return emit({"ok": True, "run": load_run(root, args.run_id)}, args.json)
            if args.run_command == "status":
                run = refresh_run_driver_state(root, args.run_id)
                driver_status = run.get("metadata_json", {}).get("driver_status", {})
                pending = [
                    approval
                    for approval in list_approvals(root, args.run_id)
                    if approval.get("status") == "pending"
                ]
                status_payload = {
                    "state": run["status"],
                    "driver": run.get("driver"),
                    "started_at": run.get("started_at"),
                    "finished_at": run.get("finished_at") or run.get("started_at"),
                    "health": run.get("health", "healthy"),
                    "progress": driver_status.get("progress", {}),
                    "waiting_on": driver_status.get("waiting_on"),
                    "session": driver_status.get("session", {}),
                    "event_cursor": driver_status.get("event_cursor"),
                    "artifacts": driver_status.get("artifacts", {}),
                    "pending_approvals": pending,
                    "budget": driver_status.get(
                        "budget", {"spent_tokens": 0, "spent_cost_usd": 0.0, "wall_minutes": 0}
                    ),
                    "links": driver_status.get("links", {"driver_ui": None}),
                }
                return emit(
                    {
                        "ok": True,
                        "run": run,
                        "health": run.get("health", "healthy"),
                        "driver_status": driver_status,
                        "pending_approvals": pending,
                        "status": status_payload,
                        "summary": {"id": run["id"], **status_payload},
                    },
                    args.json,
                )
            if args.run_command == "artifacts":
                return emit({"ok": True} | run_artifacts(root, args.run_id), args.json)
            if args.run_command == "eval":
                payload = eval_run(root, args.run_id)
                sync_workspace(root)
                return emit({"ok": True} | payload, args.json)
            if args.run_command == "accept":
                payload = accept_run(root, args.run_id)
                sync_workspace(root)
                response: dict[str, object] = {"ok": True, "run": payload}
                if args.promote:
                    response["promotion"] = promote_run(
                        root,
                        args.run_id,
                        cleanup_worktree=args.cleanup_worktree,
                    )
                return emit(response, args.json)
            if args.run_command == "reject":
                payload = reject_run(root, args.run_id, args.reason)
                sync_workspace(root)
                return emit({"ok": True, "run": payload}, args.json)
            if args.run_command == "escalate":
                payload = escalate_run(root, args.run_id, args.reason)
                sync_workspace(root)
                return emit({"ok": True, "run": payload}, args.json)
            if args.run_command == "promote":
                payload = promote_run(
                    root,
                    args.run_id,
                    cleanup_worktree=args.cleanup_worktree,
                )
                return emit({"ok": True} | payload, args.json)
            if args.run_command == "reroute":
                payload = steer_run(
                    root,
                    args.run_id,
                    SteeringRequest(
                        action="reroute",
                        reason=args.reason,
                        target={"driver": args.driver, "model": args.model},
                    ),
                )
                sync_workspace(root)
                return emit({"ok": True} | payload, args.json)
            if args.run_command == "cleanup":
                if not args.run_id and not args.terminal:
                    raise ValueError("Specify a run ID or use `hive run cleanup --terminal`.")
                if args.run_id and args.terminal:
                    raise ValueError("Use either a run ID or `--terminal`, not both.")
                if args.terminal:
                    payload = {"cleanups": cleanup_terminal_runs(root)}
                else:
                    payload = {"cleanup": cleanup_run(root, args.run_id)}
                return emit({"ok": True} | payload, args.json)
        if args.command == "steer":
            request = SteeringRequest(action=args.steer_command)
            if args.steer_command in {"pause", "resume", "cancel"}:
                request.reason = getattr(args, "reason", None)
            elif args.steer_command == "note":
                request.action = "note"
                request.note = args.message
            elif args.steer_command == "approve":
                request.action = "approve"
            elif args.steer_command == "reject":
                request.action = "reject"
                request.reason = args.reason
            elif args.steer_command == "reroute":
                request.action = "reroute"
                request.reason = args.reason
                request.target = {"driver": args.driver, "model": args.model}
            payload = steer_run(
                root,
                args.run_id,
                request,
                actor=getattr(args, "owner", None),
            )
            sync_workspace(root)
            return emit(
                {
                    "ok": True,
                    "message": f"Applied steering action {request.action!r} to {args.run_id}",
                }
                | payload,
                args.json,
            )
        if args.command == "program":
            if args.program_command == "doctor":
                diagnosis = doctor_program(root, args.project_ref)
                return emit(
                    {
                        "ok": True,
                        "message": (
                            f"Inspected PROGRAM.md for project {diagnosis['project_id']} "
                            f"({diagnosis['status']})"
                        ),
                    }
                    | diagnosis,
                    args.json,
                )
            if args.program_command == "add-evaluator":
                diagnosis = add_evaluator_template(root, args.project_ref, args.template_id)
                sync_workspace(root)
                return emit(
                    {
                        "ok": True,
                        "message": (
                            f"Added evaluator template {args.template_id!r} to "
                            f"{diagnosis['project_id']}"
                        ),
                    }
                    | diagnosis,
                    args.json,
                )
    except (CacheBusyError, WorkspaceBusyError, FileNotFoundError, ValueError, sqlite3.Error) as exc:
        return emit_error(exc, args.json)
    return 0

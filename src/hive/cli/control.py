"""Control-plane Hive CLI commands."""

# pylint: disable=line-too-long,too-many-lines,too-many-locals,too-many-statements
# pylint: disable=too-many-branches,too-many-return-statements,unused-import

from __future__ import annotations

import sqlite3
from pathlib import Path

from src.hive.cli.common import (
    emit,
    emit_error,
    launch_console_api,
    launch_dashboard,
    load_execute_code,
    open_console,
)
from src.hive.console import build_home_view, build_inbox, list_runs, load_run_detail
from src.hive.drivers import get_driver, list_drivers
from src.hive.codemode.execute import execute_code
from src.hive.sandbox import sandbox_doctor
from src.hive.search import search_workspace
from src.hive.store.cache import CacheBusyError, rebuild_cache
from src.hive.store.task_files import get_task, list_tasks
from src.hive.workspace import WorkspaceBusyError, sync_workspace
from src.hive.control import finish_run_flow, recommend_next_task, work_on_task


def _sandbox_doctor_summary(payload: dict[str, object], backend: str | None = None) -> tuple[str, list[str]]:
    probes = [dict(item) for item in payload.get("backends", []) if isinstance(item, dict)]
    if backend and probes:
        probe = probes[0]
        blockers = [str(item) for item in probe.get("blockers", []) if str(item).strip()]
        warnings = [str(item) for item in probe.get("warnings", []) if str(item).strip()]
        notes = [str(item) for item in probe.get("notes", []) if str(item).strip()]
        status = "available" if probe.get("available") and not blockers else "blocked"
        headline = f"Sandbox backend {probe.get('backend')} is {status}."
        lines: list[str] = []
        if probe.get("supported_profiles"):
            lines.append(
                "profiles: " + ", ".join(str(item) for item in probe["supported_profiles"])
            )
        lines.extend(f"blocked: {item}" for item in blockers)
        lines.extend(f"warning: {item}" for item in warnings)
        lines.extend(f"note: {item}" for item in notes[:2])
        return headline, lines

    available = [
        str(probe.get("backend"))
        for probe in probes
        if probe.get("available") and not probe.get("blockers")
    ]
    blocked = []
    for probe in probes:
        if probe.get("available") and not probe.get("blockers"):
            continue
        reason = next(
            (str(item) for item in probe.get("blockers", []) if str(item).strip()),
            None,
        )
        label = str(probe.get("backend"))
        blocked.append(f"{label} ({reason})" if reason else label)
    headline = (
        f"Sandbox doctor found {len(available)} available backend(s) and "
        f"{len(blocked)} blocked or incomplete backend(s)."
    )
    lines: list[str] = []
    if available:
        lines.append("available: " + ", ".join(available))
    if blocked:
        lines.append("blocked: " + ", ".join(blocked))
    return headline, lines


def dispatch(args, root: Path) -> int:
    """Dispatch control, project, run, and knowledge commands."""
    try:
        if args.command == "next":
            recommendation = recommend_next_task(root, project_id=args.project_id)
            if recommendation is None:
                all_tasks = [
                    task
                    for task in list_tasks(root)
                    if args.project_id is None or task.project_id == args.project_id
                ]
                review_tasks = [t for t in all_tasks if t.status == "review"]
                proposed_tasks = [t for t in all_tasks if t.status == "proposed"]
                claimed_tasks = [t for t in all_tasks if t.status in ("claimed", "in_progress")]
                done_tasks = [t for t in all_tasks if t.status == "done"]

                # Build a human-readable explanation of why nothing is ready
                explanations: list[str] = []
                if review_tasks:
                    explanations.append(
                        f"{len(review_tasks)} task(s) in review — close them to unblock "
                        "downstream work"
                    )
                if claimed_tasks:
                    explanations.append(
                        f"{len(claimed_tasks)} task(s) already claimed or in progress"
                    )
                if proposed_tasks:
                    explanations.append(
                        f"{len(proposed_tasks)} task(s) proposed but blocked by dependencies"
                    )
                if done_tasks and not review_tasks and not proposed_tasks and not claimed_tasks:
                    explanations.append("All tasks are done — create new work to continue")

                message = "No ready task is available right now."
                if explanations:
                    message += " " + "; ".join(explanations) + "."

                next_steps = []
                if review_tasks:
                    next_steps.append(
                        f"hive task update {review_tasks[0].id} --status done  "
                        "(close the review task to unblock work)"
                    )
                if not all_tasks:
                    next_steps.append("hive onboard demo  (bootstrap a starter project)")
                next_steps.append("hive doctor  (diagnose workspace health)")
                return emit(
                    {
                        "ok": True,
                        "message": message,
                        "recommendation": None,
                        "next_steps": next_steps,
                    },
                    args.json,
                )
            assert isinstance(recommendation, dict)
            recommendation_payload = dict(recommendation)
            recommendation_task = dict(recommendation_payload["task"])
            return emit(
                {
                    "ok": True,
                    "message": (
                        "Recommended next task "
                        f"{recommendation_task['id']} for project "
                        f"{recommendation_task['project_id']}"
                    ),
                    "task": recommendation_task,
                    "project": recommendation_payload["project"],
                    "recommendation": recommendation_payload,
                    "next_steps": [
                        f"hive work {recommendation_task['id']} --owner <your-name>",
                    ],
                },
                args.json,
            )
        if args.command == "work":
            payload = work_on_task(
                root,
                task_id=args.task_id,
                project_id=args.project_id,
                owner=args.owner,
                ttl_minutes=args.ttl_minutes,
                driver=args.driver,
                model=args.model,
                campaign_id=args.campaign_id,
                profile=args.profile,
                output_path=args.output,
                checkpoint=not args.no_checkpoint,
                checkpoint_message=args.checkpoint_message,
            )
            startup_step = (
                f"hive context startup --project {payload['task']['project_id']} "
                f"--task {payload['task']['id']} --profile {args.profile} --output "
                "SESSION_CONTEXT.md"
                if payload["output_path"] is None
                else f"Review the startup bundle at {payload['output_path']}"
            )
            response = {
                "ok": True,
                "message": (
                    f"Started governed work on {payload['task']['id']} "
                    f"with run {payload['run']['id']}"
                ),
                "task": payload["task"],
                "run": payload["run"],
                "project": payload["project"],
                "recommendation": payload["recommendation"],
                "checkpoint": payload["checkpoint"],
                "output_path": payload["output_path"],
                "next_steps": [startup_step],
            }
            worktree_path = payload["run"].get("worktree_path")
            if worktree_path:
                response["next_steps"].append(
                    f"Make your changes inside the run worktree at {worktree_path}"
                )
            response["next_steps"].append(f"hive finish {payload['run']['id']}")
            if args.print_context:
                response["rendered_context"] = payload["rendered_context"]
            return emit(response, args.json)
        if args.command == "finish":
            payload = finish_run_flow(
                root,
                args.run_id,
                promote=not args.no_promote,
                cleanup_worktree=not args.keep_worktree,
                actor=args.owner,
            )
            decision = dict(payload["promotion_decision"])
            task = get_task(root, str(payload["run"]["task_id"]))
            reason_suffix = ""
            reasons = decision.get("reasons") or []
            if reasons:
                # Keep the headline compact; the full reason list still renders below.
                reason_suffix = f": {reasons[0]}"
            if payload["action"] == "reject":
                next_steps = []
                # Provide targeted guidance for common rejection reasons
                no_changes = any("did not produce workspace changes" in str(r) for r in reasons)
                no_evaluator = any("No evaluator results" in str(r) for r in reasons)
                if no_changes:
                    worktree = payload["run"].get("worktree_path", "")
                    next_steps.append(
                        "This run had no file changes. Make a change inside the run worktree"
                        + (f" at {worktree}" if worktree else "")
                        + ", then run hive finish again."
                    )
                if no_evaluator:
                    next_steps.append(
                        f"hive program doctor {payload['run']['project_id']}  "
                        "(add an evaluator to enable promotion)"
                    )
                next_steps.append(f"hive next --project-id {payload['run']['project_id']}")
                next_steps.append("hive doctor  (diagnose workspace health)")
            elif payload["action"] == "escalate":
                next_steps = [f"hive run show {args.run_id}"]
            elif payload["action"] == "accept":
                next_steps = [f"hive run promote {args.run_id}"]
            elif task.status == "review":
                next_steps = [
                    f"hive task update {task.id} --status done",
                    f"hive next --project-id {task.project_id}",
                ]
            else:
                next_steps = [f"hive next --project-id {task.project_id}"]
            message = (
                f"Finished run {args.run_id} with action {payload['action']!r}"
                f"{reason_suffix}"
            )
            if task.status == "review":
                message += (
                    " The task now sits in review; mark it done when you want downstream work "
                    "to unblock."
                )
            return emit(
                {
                    "ok": True,
                    "message": message,
                    "run": payload["run"],
                    "task": task.to_frontmatter() | {"path": str(task.path) if task.path else None},
                    "evaluation": payload["evaluation"],
                    "promotion_decision": decision,
                    "promotion": payload["promotion"],
                    "action": payload["action"],
                    "next_steps": next_steps,
                },
                args.json,
            )
        if args.command == "dashboard":
            return launch_dashboard(root, args.host, args.port, args.json)
        if args.command == "console":
            if args.console_command in {"api", "serve"}:
                return launch_console_api(root, args.host, args.port, args.json)
            if args.console_command == "open":
                return open_console(
                    root, args.host, args.port, args.json, no_browser=args.no_browser
                )
            if args.console_command == "home":
                sync_workspace(root)
                return emit({"ok": True, "home": build_home_view(root)}, args.json)
            if args.console_command == "inbox":
                sync_workspace(root)
                return emit({"ok": True, "items": build_inbox(root)}, args.json)
            if args.console_command == "runs":
                sync_workspace(root)
                return emit(
                    {
                        "ok": True,
                        "runs": list_runs(
                            root,
                            project_id=args.project_id,
                            driver=args.driver,
                            health=args.health,
                        ),
                    },
                    args.json,
                )
            if args.console_command == "run":
                sync_workspace(root)
                return emit({"ok": True, "detail": load_run_detail(root, args.run_id)}, args.json)
        if args.command == "search":
            return emit(
                {
                    "ok": True,
                    "message": f"Found search results for {args.query!r}",
                    "results": search_workspace(
                        root, args.query, scopes=args.scope, limit=args.limit
                    ),
                },
                args.json,
            )
        if args.command == "execute":
            try:
                code = load_execute_code(args)
            except ValueError as exc:
                return emit({"ok": False, "error": str(exc)}, args.json)
            payload = execute_code(
                root,
                language=args.language,
                code=code,
                profile=args.profile,
                timeout_seconds=args.timeout_seconds,
            )
            return emit(payload, args.json)
        if args.command == "cache" and args.cache_command == "rebuild":
            db_path = rebuild_cache(root)
            return emit(
                {
                    "ok": True,
                    "message": f"Rebuilt cache at {db_path}",
                    "path": str(db_path),
                },
                args.json,
            )
        if args.command == "drivers":
            if args.drivers_command == "list":
                return emit(
                    {
                        "ok": True,
                        "drivers": [driver.probe().to_dict() for driver in list_drivers()],
                    },
                    args.json,
                )
            if args.drivers_command == "probe":
                if args.driver:
                    drivers = [get_driver(args.driver).probe().to_dict()]
                else:
                    drivers = [driver.probe().to_dict() for driver in list_drivers()]
                return emit({"ok": True, "drivers": drivers}, args.json)
        if args.command == "driver" and args.driver_command == "doctor":
            if args.driver:
                drivers = [get_driver(args.driver).probe().to_dict()]
            else:
                drivers = [driver.probe().to_dict() for driver in list_drivers()]
            return emit(
                {
                    "ok": True,
                    "message": "Driver doctor inspected the current runtime integration surface.",
                    "drivers": drivers,
                },
                args.json,
            )
        if args.command == "sandbox" and args.sandbox_command == "doctor":
            payload = sandbox_doctor(args.backend)
            headline, summary_lines = _sandbox_doctor_summary(payload, backend=args.backend)
            payload["message"] = headline
            payload["summary_lines"] = summary_lines
            return emit(payload, args.json)
    except (
        CacheBusyError,
        WorkspaceBusyError,
        FileNotFoundError,
        ValueError,
        sqlite3.Error,
    ) as exc:
        return emit_error(exc, args.json)
    return 0

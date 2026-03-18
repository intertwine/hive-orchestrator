"""Control-plane Hive CLI commands."""

# pylint: disable=line-too-long,too-many-lines,too-many-locals,too-many-statements
# pylint: disable=too-many-branches,too-many-return-statements,unused-import

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, cast

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
from src.hive.search import search_workspace
from src.hive.store.cache import CacheBusyError, rebuild_cache
from src.hive.workspace import WorkspaceBusyError, sync_workspace
from src.hive.control import finish_run_flow, recommend_next_task, work_on_task


def dispatch(args, root: Path) -> int:
    """Dispatch control, project, run, and knowledge commands."""
    try:
        if args.command == "next":
            recommendation = recommend_next_task(root, project_id=args.project_id)
            if recommendation is None:
                return emit(
                    {
                        "ok": True,
                        "message": "No ready task is available right now.",
                        "recommendation": None,
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
                "next_steps": [
                    (
                        f"hive context startup --project {payload['task']['project_id']} "
                        f"--task {payload['task']['id']} --output SESSION_CONTEXT.md"
                    )
                    if payload["output_path"] is None
                    else f"Review the startup bundle at {payload['output_path']}"
                ],
            }
            response["next_steps"].append(f"hive finish {payload['run']['id']}")
            if payload["output_path"] is None and args.print_context:
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
            reason_suffix = ""
            reasons = decision.get("reasons") or []
            if reasons:
                # Keep the headline compact; the full reason list still renders below.
                reason_suffix = f": {reasons[0]}"
            return emit(
                {
                    "ok": True,
                    "message": (
                        f"Finished run {args.run_id} with action {payload['action']!r}"
                        f"{reason_suffix}"
                    ),
                    "run": payload["run"],
                    "evaluation": payload["evaluation"],
                    "promotion_decision": decision,
                    "promotion": payload["promotion"],
                    "action": payload["action"],
                    "next_steps": (
                        [f"hive next --project-id {payload['run']['project_id']}"]
                        if payload["action"] == "reject"
                        else [f"hive run show {args.run_id}"]
                        if payload["action"] == "escalate"
                        else ["hive next"]
                    ),
                },
                args.json,
            )
        if args.command == "dashboard":
            return launch_dashboard(root, args.host, args.port, args.json)
        if args.command == "console":
            if args.console_command in {"api", "serve"}:
                return launch_console_api(root, args.host, args.port, args.json)
            if args.console_command == "open":
                return open_console(root, args.host, args.port, args.json, no_browser=args.no_browser)
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
                    "results": search_workspace(root, args.query, scopes=args.scope, limit=args.limit),
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
                return emit({"ok": True, "drivers": [driver.probe().to_dict() for driver in list_drivers()]}, args.json)
            if args.drivers_command == "probe":
                if args.driver:
                    drivers = [get_driver(args.driver).probe().to_dict()]
                else:
                    drivers = [driver.probe().to_dict() for driver in list_drivers()]
                return emit({"ok": True, "drivers": drivers}, args.json)
    except (CacheBusyError, WorkspaceBusyError, FileNotFoundError, ValueError, sqlite3.Error) as exc:
        return emit_error(exc, args.json)
    return 0

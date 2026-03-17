"""Hive 2.0 CLI."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

from src.hive import __version__
from src.hive.cli.render import render_payload
from src.hive.codemode.execute import MAX_EXECUTE_BYTES, execute_code
from src.hive.console import build_home_view, build_inbox, list_runs, load_run_detail
from src.hive.control import (
    campaign_status,
    create_campaign_flow,
    finish_run_flow,
    generate_brief,
    portfolio_status,
    recommend_next_task,
    steer_project,
    tick_campaign,
    tick_portfolio,
    work_on_task,
)
from src.hive.drivers import SteeringRequest, get_driver, list_drivers
from src.hive.context_bundle import build_context_bundle
from src.hive.memory.observe import observe
from src.hive.memory.reflect import reflect
from src.hive.memory.review import accept_memory_review, reject_memory_review
from src.hive.memory.search import search
from src.hive.migrate.v1_to_v2 import migrate_v1_to_v2
from src.hive.onboarding import adopt_repository, onboard_workspace
from src.hive.program import add_evaluator_template, doctor_program
from src.hive.runs.engine import (
    accept_run,
    cleanup_run,
    cleanup_terminal_runs,
    escalate_run,
    eval_run,
    load_run,
    promote_run,
    reject_run,
    run_artifacts,
    start_run,
    steer_run,
)
from src.hive.scaffold import starter_task_specs
from src.hive.search import search_workspace
from src.hive.scheduler.query import dependency_summary, project_summary, ready_tasks
from src.hive.runs.worktree import create_checkpoint_commit
from src.hive.store.cache import CacheBusyError, rebuild_cache
from src.hive.store.events import emit_event
from src.hive.store.layout import bootstrap_workspace
from src.hive.store.projects import create_project, discover_projects, get_project
from src.hive.store.task_files import (
    claim_task,
    create_task,
    get_task,
    link_tasks,
    list_tasks,
    release_task,
    update_task,
)
from src.hive.workspace import WorkspaceBusyError, resolve_workspace_path, sync_workspace


def _emit(payload: dict, as_json: bool) -> int:
    payload.setdefault("version", __version__)
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(render_payload(payload))
    return 0


def _error_message(exc: Exception) -> str:
    """Convert expected exceptions into product-level CLI errors."""
    if isinstance(exc, WorkspaceBusyError):
        return str(exc)
    if isinstance(exc, CacheBusyError):
        return str(exc)
    if isinstance(exc, sqlite3.Error):
        return (
            "Hive hit a temporary cache refresh error while rebuilding derived state. "
            "Retry the command, or run `hive sync projections` once the workspace is idle."
        )
    return str(exc)


def _emit_error(exc: Exception, as_json: bool) -> int:
    message = _error_message(exc)
    _emit({"ok": False, "error": message, "message": message}, as_json)
    return 1


def _load_execute_code(args: argparse.Namespace) -> str:
    if args.file:
        file_path = Path(args.file)
        if file_path.stat().st_size > MAX_EXECUTE_BYTES:
            raise ValueError(f"Execute input exceeds {MAX_EXECUTE_BYTES} bytes: {file_path}")
        return file_path.read_text(encoding="utf-8")

    code = args.code or ""
    if len(code.encode("utf-8")) > MAX_EXECUTE_BYTES:
        raise ValueError(f"Execute input exceeds {MAX_EXECUTE_BYTES} bytes")
    return code


def _clean_string_list(values: list[str] | None) -> list[str]:
    cleaned: list[str] = []
    for value in values or []:
        stripped = value.strip()
        if stripped:
            cleaned.append(stripped)
    return cleaned


def _doctor_payload(root: Path) -> dict[str, object]:
    projects = discover_projects(root)
    tasks = list_tasks(root)
    ready = ready_tasks(root, limit=8)

    checks = {
        "git_repo": (root / ".git").exists(),
        "layout": (root / ".hive").exists(),
        "global_md": (root / "GLOBAL.md").exists(),
        "agents_md": (root / "AGENTS.md").exists(),
        "cache": (root / ".hive" / "cache" / "index.sqlite").exists(),
        "projects_dir": (root / "projects").exists(),
    }

    next_steps: list[str] = []
    if not checks["layout"]:
        next_steps.append(
            'Run `hive quickstart demo --title "Demo project"` '
            "to bootstrap a workspace with a starter project and ready task."
        )
        next_steps.append(
            "Run `hive init` to bootstrap an empty workspace without a starter project."
        )
    if checks["layout"] and not checks["global_md"]:
        next_steps.append("Run `hive sync projections` to create `GLOBAL.md`.")
    if checks["layout"] and not checks["agents_md"]:
        next_steps.append("Run `hive sync projections` to create `AGENTS.md`.")
    if checks["layout"] and not projects:
        next_steps.append(
            'Run `hive quickstart demo --title "Demo project"` '
            "to scaffold a working project with starter tasks."
        )
        next_steps.append(
            'Run `hive project create demo --title "Demo project"` '
            "to scaffold your first project."
        )
    elif projects and not tasks:
        first_project = projects[0]
        next_steps.append(
            "Run "
            f"`hive task create --project-id {first_project.id} "
            f'--title "Define the first slice"` '
            "to create canonical work."
        )
        next_steps.append(
            "If you still have legacy checkbox tasks, run "
            "`hive migrate v1-to-v2` to import them."
        )
    elif ready:
        top_task = ready[0]
        next_steps.append(
            "Run "
            f"`hive context startup --project {top_task['project_id']} "
            f"--task {top_task['id']}` "
            "to start work on the top ready task."
        )
    elif tasks:
        next_steps.append("Run `hive task list` to inspect blocked, claimed, or completed work.")
    if checks["layout"] and not checks["cache"]:
        next_steps.append("Run `hive sync projections` to rebuild the cache and refresh rollups.")

    message = (
        f"Hive workspace at {root}: {len(projects)} projects, "
        f"{len(tasks)} tasks, {len(ready)} ready"
    )
    return {
        "ok": True,
        "message": message,
        "workspace": str(root),
        "projects": len(projects),
        "tasks": len(tasks),
        "ready": len(ready),
        "checks": checks,
        "next_steps": next_steps,
    }


def build_parser() -> argparse.ArgumentParser:
    """Build the Hive CLI parser."""
    parser = argparse.ArgumentParser(prog="hive", description="Hive 2.2 control-plane CLI")
    parser.add_argument("--path", default=str(Path.cwd()), help="Workspace base path")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command")

    quickstart_parser = subparsers.add_parser("quickstart")
    quickstart_parser.add_argument("slug", nargs="?", default="demo")
    quickstart_parser.add_argument("--title")
    quickstart_parser.add_argument("--objective")
    onboard_parser = subparsers.add_parser("onboard")
    onboard_parser.add_argument("slug", nargs="?", default="demo")
    onboard_parser.add_argument("--title")
    onboard_parser.add_argument("--objective")
    adopt_parser = subparsers.add_parser("adopt")
    adopt_parser.add_argument("slug", nargs="?")
    adopt_parser.add_argument("--title")
    adopt_parser.add_argument("--objective")

    subparsers.add_parser("init")
    doctor_parser = subparsers.add_parser("doctor")
    doctor_subparsers = doctor_parser.add_subparsers(dest="doctor_command")
    doctor_subparsers.add_parser("workspace")
    doctor_program = doctor_subparsers.add_parser("program")
    doctor_program.add_argument("project_ref")
    next_parser = subparsers.add_parser("next")
    next_parser.add_argument("--project-id")
    work_parser = subparsers.add_parser("work")
    work_parser.add_argument("task_id", nargs="?")
    work_parser.add_argument("--project-id")
    work_parser.add_argument("--owner")
    work_parser.add_argument("--ttl-minutes", type=int, default=60)
    work_parser.add_argument("--driver", default="local")
    work_parser.add_argument("--model")
    work_parser.add_argument("--campaign-id")
    work_parser.add_argument("--profile", default="default")
    work_parser.add_argument("--output")
    work_parser.add_argument(
        "--no-checkpoint",
        action="store_true",
        help="Skip the automatic workspace checkpoint before starting work.",
    )
    work_parser.add_argument(
        "--checkpoint-message",
        help="Override the automatic checkpoint commit message used by `hive work`.",
    )
    finish_parser = subparsers.add_parser("finish")
    finish_parser.add_argument("run_id")
    finish_parser.add_argument("--owner")
    finish_parser.add_argument(
        "--no-promote",
        action="store_true",
        help="Accept the run without merging it back into the workspace branch.",
    )
    finish_parser.add_argument(
        "--keep-worktree",
        action="store_true",
        help="Keep the linked run worktree after promotion.",
    )
    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("query")
    search_parser.add_argument("--scope", action="append")
    search_parser.add_argument("--limit", type=int, default=8)
    dashboard_parser = subparsers.add_parser("dashboard")
    dashboard_parser.add_argument("--host", default="127.0.0.1")
    dashboard_parser.add_argument("--port", type=int, default=8787)
    console_parser = subparsers.add_parser("console")
    console_subparsers = console_parser.add_subparsers(dest="console_command")
    console_api = console_subparsers.add_parser("api")
    console_api.add_argument("--host", default="127.0.0.1")
    console_api.add_argument("--port", type=int, default=8787)
    console_serve = console_subparsers.add_parser("serve")
    console_serve.add_argument("--host", default="127.0.0.1")
    console_serve.add_argument("--port", type=int, default=8787)
    console_open = console_subparsers.add_parser("open")
    console_open.add_argument("--host", default="127.0.0.1")
    console_open.add_argument("--port", type=int, default=8787)
    console_open.add_argument(
        "--no-browser",
        action="store_true",
        help="Print the console URL without opening a browser.",
    )
    console_subparsers.add_parser("home")
    console_subparsers.add_parser("inbox")
    console_runs = console_subparsers.add_parser("runs")
    console_runs.add_argument("--project-id")
    console_runs.add_argument("--driver")
    console_runs.add_argument("--health")
    console_run = console_subparsers.add_parser("run")
    console_run.add_argument("run_id")
    execute_parser = subparsers.add_parser("execute")
    execute_parser.add_argument("--language", default="python")
    execute_parser.add_argument("--profile", default="default")
    execute_parser.add_argument("--timeout-seconds", type=int, default=20)
    execute_input = execute_parser.add_mutually_exclusive_group(required=True)
    execute_input.add_argument("--code")
    execute_input.add_argument("--file")

    cache_parser = subparsers.add_parser("cache")
    cache_subparsers = cache_parser.add_subparsers(dest="cache_command")
    cache_subparsers.add_parser("rebuild")

    drivers_parser = subparsers.add_parser("drivers")
    drivers_subparsers = drivers_parser.add_subparsers(dest="drivers_command")
    drivers_subparsers.add_parser("list")
    drivers_probe = drivers_subparsers.add_parser("probe")
    drivers_probe.add_argument("driver", nargs="?")

    project_parser = subparsers.add_parser("project")
    project_subparsers = project_parser.add_subparsers(dest="project_command")
    project_subparsers.add_parser("list")
    project_create = project_subparsers.add_parser("create")
    project_create.add_argument("slug")
    project_create.add_argument("--title")
    project_create.add_argument("--project-id")
    project_create.add_argument("--status", default="active")
    project_create.add_argument("--priority", type=int, default=2)
    project_create.add_argument("--objective")
    project_create.add_argument("--tag", action="append")
    project_show = project_subparsers.add_parser("show")
    project_show.add_argument("project_id")
    project_sync = project_subparsers.add_parser("sync")
    project_sync.add_argument("target", nargs="?")

    workspace_parser = subparsers.add_parser("workspace")
    workspace_subparsers = workspace_parser.add_subparsers(dest="workspace_command")
    workspace_checkpoint = workspace_subparsers.add_parser("checkpoint")
    workspace_checkpoint.add_argument(
        "--message",
        default="Checkpoint workspace",
        help="Git commit message for the checkpoint commit",
    )

    task_parser = subparsers.add_parser("task")
    task_subparsers = task_parser.add_subparsers(dest="task_command")
    task_list = task_subparsers.add_parser("list")
    task_list.add_argument("--project-id")
    task_list.add_argument("--status", action="append")
    task_show = task_subparsers.add_parser("show")
    task_show.add_argument("task_id")
    task_create = task_subparsers.add_parser("create")
    task_create.add_argument("--project-id", required=True)
    task_create.add_argument("--title", required=True)
    task_create.add_argument("--kind", default="task")
    task_create.add_argument("--status", default="ready")
    task_create.add_argument("--priority", type=int, default=2)
    task_create.add_argument("--parent-id")
    task_create.add_argument("--label", action="append")
    task_create.add_argument("--relevant-file", action="append")
    task_create.add_argument("--acceptance", action="append")
    task_create.add_argument("--summary")
    task_create.add_argument("--notes")
    task_create.add_argument("--history")
    task_update = task_subparsers.add_parser("update")
    task_update.add_argument("task_id")
    task_update.add_argument("--title")
    task_update.add_argument("--status")
    task_update.add_argument("--priority", type=int)
    task_update.add_argument("--parent-id")
    task_update.add_argument("--clear-parent", action="store_true")
    task_update.add_argument("--label", action="append")
    task_update.add_argument("--clear-labels", action="store_true")
    task_update.add_argument("--relevant-file", action="append")
    task_update.add_argument("--clear-relevant-files", action="store_true")
    task_update.add_argument("--acceptance", action="append")
    task_update.add_argument("--clear-acceptance", action="store_true")
    task_update.add_argument("--summary")
    task_update.add_argument("--notes")
    task_update.add_argument("--history")
    task_claim = task_subparsers.add_parser("claim")
    task_claim.add_argument("task_id")
    task_claim.add_argument("--owner", required=True)
    task_claim.add_argument("--ttl-minutes", type=int, default=30)
    task_release = task_subparsers.add_parser("release")
    task_release.add_argument("task_id")
    task_link = task_subparsers.add_parser("link")
    task_link.add_argument("src_id")
    task_link.add_argument("edge_type")
    task_link.add_argument("dst_id")
    task_ready = task_subparsers.add_parser("ready")
    task_ready.add_argument("--project-id")
    task_ready.add_argument("--limit", type=int)

    run_parser = subparsers.add_parser("run")
    run_subparsers = run_parser.add_subparsers(dest="run_command")
    run_start = run_subparsers.add_parser("start")
    run_start.add_argument("task_id")
    run_start.add_argument("--driver", default="local")
    run_start.add_argument("--model")
    run_start.add_argument("--campaign-id")
    run_start.add_argument("--profile", default="default")
    run_launch = run_subparsers.add_parser("launch")
    run_launch.add_argument("task_id")
    run_launch.add_argument("--driver", default="local")
    run_launch.add_argument("--model")
    run_launch.add_argument("--campaign-id")
    run_launch.add_argument("--profile", default="default")
    run_show = run_subparsers.add_parser("show")
    run_show.add_argument("run_id")
    run_status = run_subparsers.add_parser("status")
    run_status.add_argument("run_id")
    run_artifacts_parser = run_subparsers.add_parser("artifacts")
    run_artifacts_parser.add_argument("run_id")
    run_eval = run_subparsers.add_parser("eval")
    run_eval.add_argument("run_id")
    run_accept = run_subparsers.add_parser("accept")
    run_accept.add_argument("run_id")
    run_accept.add_argument("--promote", action="store_true")
    run_accept.add_argument("--cleanup-worktree", action="store_true")
    run_reject = run_subparsers.add_parser("reject")
    run_reject.add_argument("run_id")
    run_reject.add_argument("--reason")
    run_escalate = run_subparsers.add_parser("escalate")
    run_escalate.add_argument("run_id")
    run_escalate.add_argument("--reason")
    run_promote = run_subparsers.add_parser("promote")
    run_promote.add_argument("run_id")
    run_promote.add_argument("--cleanup-worktree", action="store_true")
    run_reroute = run_subparsers.add_parser("reroute")
    run_reroute.add_argument("run_id")
    run_reroute.add_argument("--driver", required=True)
    run_reroute.add_argument("--model")
    run_reroute.add_argument("--reason")
    run_cleanup = run_subparsers.add_parser("cleanup")
    run_cleanup.add_argument("run_id", nargs="?")
    run_cleanup.add_argument("--terminal", action="store_true")

    steer_parser = subparsers.add_parser("steer")
    steer_subparsers = steer_parser.add_subparsers(dest="steer_command")
    steer_pause = steer_subparsers.add_parser("pause")
    steer_pause.add_argument("run_id")
    steer_pause.add_argument("--reason")
    steer_pause.add_argument("--owner")
    steer_resume = steer_subparsers.add_parser("resume")
    steer_resume.add_argument("run_id")
    steer_resume.add_argument("--reason")
    steer_resume.add_argument("--owner")
    steer_cancel = steer_subparsers.add_parser("cancel")
    steer_cancel.add_argument("run_id")
    steer_cancel.add_argument("--reason")
    steer_cancel.add_argument("--owner")
    steer_note = steer_subparsers.add_parser("note")
    steer_note.add_argument("run_id")
    steer_note.add_argument("--message", required=True)
    steer_note.add_argument("--owner")
    steer_approve = steer_subparsers.add_parser("approve")
    steer_approve.add_argument("run_id")
    steer_approve.add_argument("--owner")
    steer_reject = steer_subparsers.add_parser("reject")
    steer_reject.add_argument("run_id")
    steer_reject.add_argument("--reason")
    steer_reject.add_argument("--owner")
    steer_reroute = steer_subparsers.add_parser("reroute")
    steer_reroute.add_argument("run_id")
    steer_reroute.add_argument("--driver", required=True)
    steer_reroute.add_argument("--model")
    steer_reroute.add_argument("--reason")
    steer_reroute.add_argument("--owner")

    program_parser = subparsers.add_parser("program")
    program_subparsers = program_parser.add_subparsers(dest="program_command")
    program_doctor = program_subparsers.add_parser("doctor")
    program_doctor.add_argument("project_ref")
    program_add_evaluator = program_subparsers.add_parser("add-evaluator")
    program_add_evaluator.add_argument("project_ref")
    program_add_evaluator.add_argument("template_id")

    campaign_parser = subparsers.add_parser("campaign")
    campaign_subparsers = campaign_parser.add_subparsers(dest="campaign_command")
    campaign_list = campaign_subparsers.add_parser("list")
    campaign_list.add_argument("--project-id")
    campaign_create = campaign_subparsers.add_parser("create")
    campaign_create.add_argument("--title", required=True)
    campaign_create.add_argument("--goal", required=True)
    campaign_create.add_argument("--project-id", action="append", required=True)
    campaign_create.add_argument("--driver", default="local")
    campaign_create.add_argument("--model")
    campaign_create.add_argument("--cadence", default="daily")
    campaign_create.add_argument("--brief-cadence", default="daily")
    campaign_create.add_argument("--max-active-runs", type=int, default=1)
    campaign_create.add_argument("--notes")
    campaign_show = campaign_subparsers.add_parser("status")
    campaign_show.add_argument("campaign_id")
    campaign_tick = campaign_subparsers.add_parser("tick")
    campaign_tick.add_argument("campaign_id")
    campaign_tick.add_argument("--owner")

    brief_parser = subparsers.add_parser("brief")
    brief_subparsers = brief_parser.add_subparsers(dest="brief_command")
    brief_subparsers.add_parser("daily")
    brief_subparsers.add_parser("weekly")

    memory_parser = subparsers.add_parser("memory")
    memory_subparsers = memory_parser.add_subparsers(dest="memory_command")
    memory_observe = memory_subparsers.add_parser("observe")
    memory_observe.add_argument("--transcript-path")
    memory_observe.add_argument("--note")
    memory_observe.add_argument("--scope", choices=["project", "global"], default="project")
    memory_observe.add_argument("--project")
    memory_observe.add_argument("--harness")
    memory_reflect = memory_subparsers.add_parser("reflect")
    memory_reflect.add_argument("--scope", choices=["project", "global"], default="project")
    memory_reflect.add_argument("--project")
    memory_reflect.add_argument("--propose", action="store_true")
    memory_accept = memory_subparsers.add_parser("accept")
    memory_accept.add_argument("--scope", choices=["project", "global"], default="project")
    memory_accept.add_argument("--project")
    memory_reject = memory_subparsers.add_parser("reject")
    memory_reject.add_argument("--scope", choices=["project", "global"], default="project")
    memory_reject.add_argument("--project")
    memory_search = memory_subparsers.add_parser("search")
    memory_search.add_argument("query")
    memory_search.add_argument("--scope", choices=["project", "global", "all"], default="all")
    memory_search.add_argument("--project")
    memory_search.add_argument("--task")
    memory_search.add_argument("--limit", type=int, default=8)

    context_parser = subparsers.add_parser("context")
    context_subparsers = context_parser.add_subparsers(dest="context_command")
    context_startup = context_subparsers.add_parser("startup")
    context_startup.add_argument("--project", required=True)
    context_startup.add_argument("--profile", default="default")
    context_startup.add_argument("--query")
    context_startup.add_argument("--task")
    context_startup.add_argument("--output")
    context_handoff = context_subparsers.add_parser("handoff")
    context_handoff.add_argument("--project", required=True)
    context_handoff.add_argument("--output")

    sync_parser = subparsers.add_parser("sync")
    sync_subparsers = sync_parser.add_subparsers(dest="sync_command")
    sync_subparsers.add_parser("projections")

    portfolio_parser = subparsers.add_parser("portfolio")
    portfolio_subparsers = portfolio_parser.add_subparsers(dest="portfolio_command")
    portfolio_subparsers.add_parser("status")
    portfolio_steer = portfolio_subparsers.add_parser("steer")
    portfolio_steer.add_argument("project_ref")
    portfolio_steer.add_argument("--pause", action="store_true")
    portfolio_steer.add_argument("--resume", action="store_true")
    portfolio_steer.add_argument("--focus-task")
    portfolio_steer.add_argument("--clear-focus", action="store_true")
    portfolio_steer.add_argument("--boost", type=int)
    portfolio_steer.add_argument("--force-review", action="store_true")
    portfolio_steer.add_argument("--clear-force-review", action="store_true")
    portfolio_steer.add_argument("--note")
    portfolio_steer.add_argument("--owner")
    portfolio_tick = portfolio_subparsers.add_parser("tick")
    portfolio_tick.add_argument(
        "--mode",
        choices=["recommend", "start", "review", "cleanup"],
        default="recommend",
    )
    portfolio_tick.add_argument("--project-id")
    portfolio_tick.add_argument("--owner")
    portfolio_tick.add_argument("--profile", default="default")
    portfolio_tick.add_argument("--output")
    portfolio_tick.add_argument("--run-id")

    migrate_parser = subparsers.add_parser("migrate")
    migrate_subparsers = migrate_parser.add_subparsers(dest="migrate_command")
    migrate_v1 = migrate_subparsers.add_parser("v1-to-v2")
    migrate_v1.add_argument("--dry-run", action="store_true")
    migrate_v1.add_argument("--project")
    migrate_v1.add_argument("--owner", default="codex")
    migrate_v1.add_argument("--rewrite", action="store_true")

    deps_parser = subparsers.add_parser("deps")
    deps_parser.add_argument("--legacy", action="store_true")

    return parser


def _project_payload(project) -> dict[str, object]:
    return {
        "id": project.id,
        "slug": project.slug,
        "title": project.title,
        "status": project.status,
        "priority": project.priority,
        "owner": project.owner,
        "path": str(project.agency_path),
        "program_path": str(project.program_path),
    }


def _launch_console_api(root: Path, host: str, port: int, as_json: bool) -> int:
    try:
        import fastapi  # noqa: F401  # pylint: disable=unused-import,import-outside-toplevel
        import uvicorn  # noqa: F401  # pylint: disable=unused-import,import-outside-toplevel
    except ImportError:
        _emit(
            {
                "ok": False,
                "error": (
                    "Console support is not installed. Install it with "
                    "`uv tool install 'agent-hive[console]'`, "
                    "`pipx install 'agent-hive[console]'`, or "
                    "`python -m pip install 'agent-hive[console]'`."
                ),
            },
            as_json,
        )
        return 1

    env = dict(os.environ)
    env["HIVE_BASE_PATH"] = str(root)
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "src.hive.console.api:app",
        "--host",
        host,
        "--port",
        str(port),
    ]
    return subprocess.call(command, env=env)


def _launch_dashboard(
    root: Path,
    host: str,
    port: int,
    as_json: bool,
) -> int:
    return _launch_console_api(root, host, port, as_json)


def _console_url(host: str, port: int) -> str:
    return f"http://{host}:{port}/console/"


def _open_console(root: Path, host: str, port: int, as_json: bool, *, no_browser: bool) -> int:
    url = _console_url(host, port)
    payload = {
        "ok": True,
        "message": f"Start the console server with `hive console serve --host {host} --port {port}`",
        "url": url,
        "workspace": str(root),
    }
    if no_browser:
        return _emit(payload, as_json)
    try:
        import webbrowser  # pylint: disable=import-outside-toplevel

        opened = webbrowser.open(url)
    except Exception:  # pragma: no cover - browser availability is environment-specific.
        opened = False
    payload["opened"] = opened
    if not opened:
        payload["message"] = (
            f"Console URL: {url}. Start the server with `hive console serve --host {host} --port {port}`."
        )
    return _emit(payload, as_json)


def main(argv: list[str] | None = None) -> int:
    """Run the Hive CLI."""
    if argv is None:
        argv = sys.argv[1:]
    argv = list(argv)
    forced_json = False
    while "--json" in argv:
        argv.remove("--json")
        forced_json = True
    parser = build_parser()
    args = parser.parse_args(argv)
    args.json = bool(getattr(args, "json", False) or forced_json)
    root = Path(args.path).resolve()

    if args.command == "quickstart":
        try:
            bootstrapped = bootstrap_workspace(root)
            project = create_project(
                root,
                args.slug,
                title=args.title,
                objective=args.objective,
            )
            starter_tasks = []
            for spec in starter_task_specs(project.title):
                starter_tasks.append(
                    create_task(
                        root,
                        project.id,
                        str(spec["title"]),
                        status=str(spec["status"]),
                        priority=int(spec["priority"]),
                        acceptance=list(spec["acceptance"]),
                        summary_md=str(spec["summary_md"]),
                    )
                )
            for current, nxt in zip(starter_tasks, starter_tasks[1:]):
                link_tasks(root, current.id, "blocks", nxt.id)
            sync_workspace(root)
            if not starter_tasks:
                raise ValueError("Quickstart could not create starter tasks")
            first_task = starter_tasks[0]
            return _emit(
                {
                    "ok": True,
                    "message": (
                        f"Quickstarted Hive workspace at {root} with project {project.id} "
                        f"and {len(starter_tasks)} starter tasks"
                    ),
                    "layout": {key: str(value) for key, value in bootstrapped["layout"].items()},
                    "created_files": bootstrapped["created_files"],
                    "updated_files": bootstrapped["updated_files"],
                    "project": _project_payload(project),
                    "tasks": [
                        {
                            "id": task.id,
                            "project_id": task.project_id,
                            "title": task.title,
                            "status": task.status,
                            "priority": task.priority,
                        }
                        for task in starter_tasks
                    ],
                    "next_steps": [
                        f"hive task ready --project-id {project.id}",
                        f"hive task claim {first_task.id} --owner <your-name> --ttl-minutes 60",
                        f"hive context startup --project {project.id} --task {first_task.id}",
                    ],
                },
                args.json,
            )
        except (
            CacheBusyError,
            WorkspaceBusyError,
            FileExistsError,
            FileNotFoundError,
            ValueError,
            sqlite3.Error,
        ) as exc:
            return _emit_error(exc, args.json)

    if args.command == "init":
        try:
            bootstrapped = bootstrap_workspace(root)
            sync_workspace(root)
            doctor = _doctor_payload(root)
            return _emit(
                {
                    "ok": True,
                    "message": f"Initialized Hive layout at {root}",
                    "layout": {key: str(value) for key, value in bootstrapped["layout"].items()},
                    "created_files": bootstrapped["created_files"],
                    "updated_files": bootstrapped["updated_files"],
                    "next_steps": doctor["next_steps"],
                },
                args.json,
            )
        except (
            CacheBusyError,
            WorkspaceBusyError,
            FileNotFoundError,
            ValueError,
            sqlite3.Error,
        ) as exc:
            return _emit_error(exc, args.json)

    if args.command == "onboard":
        try:
            payload = onboard_workspace(
                root,
                slug=args.slug,
                title=args.title,
                objective=args.objective,
            )
            return _emit(
                {
                    "ok": True,
                    "message": f"Onboarded Hive workspace at {root}",
                    "next_steps": [
                        f"hive next --project-id {payload['project']['id']}",
                        f"hive work --project-id {payload['project']['id']} --owner <your-name>",
                    ],
                    **payload,
                },
                args.json,
            )
        except (
            CacheBusyError,
            WorkspaceBusyError,
            FileExistsError,
            FileNotFoundError,
            ValueError,
            sqlite3.Error,
        ) as exc:
            return _emit_error(exc, args.json)

    if args.command == "adopt":
        try:
            payload = adopt_repository(
                root,
                slug=args.slug,
                title=args.title,
                objective=args.objective,
            )
            return _emit(
                {
                    "ok": True,
                    "message": f"Adopted repository at {root} into Hive",
                    "next_steps": [
                        f"hive next --project-id {payload['project']['id']}",
                        f"hive work --project-id {payload['project']['id']} --owner <your-name>",
                    ],
                    **payload,
                },
                args.json,
            )
        except (
            CacheBusyError,
            WorkspaceBusyError,
            FileExistsError,
            FileNotFoundError,
            ValueError,
            sqlite3.Error,
        ) as exc:
            return _emit_error(exc, args.json)

    if args.command == "doctor":
        try:
            if args.doctor_command in {None, "workspace"}:
                return _emit(_doctor_payload(root), args.json)
            if args.doctor_command == "program":
                diagnosis = doctor_program(root, args.project_ref)
                return _emit(
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
        except (FileNotFoundError, ValueError) as exc:
            return _emit_error(exc, args.json)

    if args.command == "next":
        try:
            recommendation = recommend_next_task(root, project_id=args.project_id)
            if recommendation is None:
                return _emit(
                    {
                        "ok": True,
                        "message": "No ready task is available right now.",
                        "recommendation": None,
                    },
                    args.json,
                )
            recommendation_payload = cast(dict[str, Any], recommendation)
            recommendation_task = cast(dict[str, Any], recommendation_payload["task"])
            return _emit(
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
        except (
            CacheBusyError,
            WorkspaceBusyError,
            FileNotFoundError,
            ValueError,
            sqlite3.Error,
        ) as exc:
            return _emit_error(exc, args.json)

    if args.command == "work":
        try:
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
            }
            if payload["output_path"] is None:
                response["rendered_context"] = payload["rendered_context"]
            return _emit(response, args.json)
        except (
            CacheBusyError,
            WorkspaceBusyError,
            FileNotFoundError,
            ValueError,
            sqlite3.Error,
        ) as exc:
            return _emit_error(exc, args.json)

    if args.command == "finish":
        try:
            payload = finish_run_flow(
                root,
                args.run_id,
                promote=not args.no_promote,
                cleanup_worktree=not args.keep_worktree,
                actor=args.owner,
            )
            return _emit(
                {
                    "ok": True,
                    "message": (
                        f"Finished run {args.run_id} with action {payload['action']!r}"
                    ),
                    "run": payload["run"],
                    "evaluation": payload["evaluation"],
                    "promotion_decision": payload["promotion_decision"],
                    "promotion": payload["promotion"],
                    "action": payload["action"],
                },
                args.json,
            )
        except (
            CacheBusyError,
            WorkspaceBusyError,
            FileNotFoundError,
            ValueError,
            sqlite3.Error,
        ) as exc:
            return _emit_error(exc, args.json)

    if args.command == "dashboard":
        return _launch_dashboard(
            root,
            args.host,
            args.port,
            args.json,
        )

    if args.command == "console":
        try:
            if args.console_command in {"api", "serve"}:
                return _launch_console_api(root, args.host, args.port, args.json)
            if args.console_command == "open":
                return _open_console(
                    root,
                    args.host,
                    args.port,
                    args.json,
                    no_browser=args.no_browser,
                )
            if args.console_command == "home":
                sync_workspace(root)
                return _emit({"ok": True, "home": build_home_view(root)}, args.json)
            if args.console_command == "inbox":
                sync_workspace(root)
                return _emit({"ok": True, "items": build_inbox(root)}, args.json)
            if args.console_command == "runs":
                sync_workspace(root)
                return _emit(
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
                return _emit({"ok": True, "detail": load_run_detail(root, args.run_id)}, args.json)
        except (
            CacheBusyError,
            WorkspaceBusyError,
            FileNotFoundError,
            ValueError,
            sqlite3.Error,
        ) as exc:
            return _emit_error(exc, args.json)

    if args.command == "search":
        try:
            return _emit(
                {
                    "ok": True,
                    "message": f"Found search results for {args.query!r}",
                    "results": search_workspace(
                        root, args.query, scopes=args.scope, limit=args.limit
                    ),
                },
                args.json,
            )
        except (CacheBusyError, FileNotFoundError, ValueError, sqlite3.Error) as exc:
            return _emit_error(exc, args.json)

    if args.command == "execute":
        try:
            code = _load_execute_code(args)
        except ValueError as exc:
            return _emit({"ok": False, "error": str(exc)}, args.json)
        payload = execute_code(
            root,
            language=args.language,
            code=code,
            profile=args.profile,
            timeout_seconds=args.timeout_seconds,
        )
        return _emit(payload, args.json)

    if args.command == "cache" and args.cache_command == "rebuild":
        try:
            db_path = rebuild_cache(root)
            return _emit(
                {
                    "ok": True,
                    "message": f"Rebuilt cache at {db_path}",
                    "path": str(db_path),
                },
                args.json,
            )
        except (CacheBusyError, FileNotFoundError, ValueError, sqlite3.Error) as exc:
            return _emit_error(exc, args.json)

    if args.command == "drivers":
        try:
            if args.drivers_command == "list":
                return _emit(
                    {"ok": True, "drivers": [driver.probe().to_dict() for driver in list_drivers()]},
                    args.json,
                )
            if args.drivers_command == "probe":
                if args.driver:
                    drivers = [get_driver(args.driver).probe().to_dict()]
                else:
                    drivers = [driver.probe().to_dict() for driver in list_drivers()]
                return _emit({"ok": True, "drivers": drivers}, args.json)
        except ValueError as exc:
            return _emit_error(exc, args.json)

    if args.command == "project":
        try:
            if args.project_command == "list":
                return _emit({"ok": True, "projects": project_summary(root)}, args.json)
            if args.project_command == "create":
                project = create_project(
                    root,
                    args.slug,
                    title=args.title,
                    project_id=args.project_id,
                    status=args.status,
                    priority=args.priority,
                    objective=args.objective,
                    tags=args.tag,
                )
                sync_workspace(root)
                return _emit(
                    {
                        "ok": True,
                        "project": _project_payload(project),
                        "next_steps": [
                            "Run "
                            f"`hive task create --project-id {project.id} "
                            f'--title "Define the first slice"` '
                            "to add canonical work.",
                            f"Run `hive context startup --project {project.id}` "
                            "to build startup context.",
                        ],
                    },
                    args.json,
                )
            if args.project_command == "show":
                project = get_project(root, args.project_id)
                return _emit({"ok": True, "project": _project_payload(project)}, args.json)
            if args.project_command == "sync":
                sync_workspace(root)
                return _emit({"ok": True, "message": "Synced projections"}, args.json)
        except (
            CacheBusyError,
            WorkspaceBusyError,
            FileExistsError,
            FileNotFoundError,
            ValueError,
            sqlite3.Error,
        ) as exc:
            return _emit_error(exc, args.json)

    if args.command == "workspace":
        try:
            if args.workspace_command == "checkpoint":
                payload = create_checkpoint_commit(root, message=args.message)
                return _emit({"ok": True} | payload, args.json)
        except FileNotFoundError as exc:
            return _emit_error(exc, args.json)
        except ValueError as exc:
            return _emit_error(exc, args.json)

    if args.command == "task":
        try:
            if args.task_command == "list":
                tasks = list_tasks(root)
                if args.project_id:
                    tasks = [task for task in tasks if task.project_id == args.project_id]
                if args.status:
                    statuses = set(args.status)
                    tasks = [task for task in tasks if task.status in statuses]
                return _emit(
                    {
                        "ok": True,
                        "tasks": [
                            task.to_frontmatter() | {"path": str(task.path)} for task in tasks
                        ],
                    },
                    args.json,
                )
            if args.task_command == "show":
                task = get_task(root, args.task_id)
                return _emit(
                    {
                        "ok": True,
                        "task": task.to_frontmatter() | {"path": str(task.path)},
                    },
                    args.json,
                )
            if args.task_command == "create":
                task = create_task(
                    root,
                    args.project_id,
                    args.title,
                    kind=args.kind,
                    status=args.status,
                    priority=args.priority,
                    parent_id=args.parent_id,
                    labels=_clean_string_list(args.label),
                    relevant_files=_clean_string_list(args.relevant_file),
                    acceptance=_clean_string_list(args.acceptance),
                    summary_md=(args.summary or "").strip(),
                    notes_md=(args.notes or "").strip(),
                    history_md=(args.history or "").strip(),
                )
                sync_workspace(root)
                return _emit(
                    {
                        "ok": True,
                        "task": task.to_frontmatter() | {"path": str(task.path)},
                        "next_steps": [
                            f"hive task ready --project-id {task.project_id}",
                            f"hive context startup --project {task.project_id} --task {task.id}",
                        ],
                    },
                    args.json,
                )
            if args.task_command == "update":
                patch = {}
                for field in ["title", "status", "priority"]:
                    value = getattr(args, field)
                    if value is not None:
                        patch[field] = value
                if args.clear_parent:
                    patch["parent_id"] = None
                elif args.parent_id is not None:
                    patch["parent_id"] = args.parent_id
                if args.clear_labels:
                    patch["labels"] = []
                elif args.label is not None:
                    patch["labels"] = _clean_string_list(args.label)
                if args.clear_relevant_files:
                    patch["relevant_files"] = []
                elif args.relevant_file is not None:
                    patch["relevant_files"] = _clean_string_list(args.relevant_file)
                if args.clear_acceptance:
                    patch["acceptance"] = []
                elif args.acceptance is not None:
                    patch["acceptance"] = _clean_string_list(args.acceptance)
                if args.summary is not None:
                    patch["summary_md"] = args.summary.strip()
                if args.notes is not None:
                    patch["notes_md"] = args.notes.strip()
                if args.history is not None:
                    patch["history_md"] = args.history.strip()
                task = update_task(root, args.task_id, patch)
                sync_workspace(root)
                return _emit(
                    {
                        "ok": True,
                        "task": task.to_frontmatter() | {"path": str(task.path)},
                    },
                    args.json,
                )
            if args.task_command == "claim":
                task = claim_task(root, args.task_id, args.owner, args.ttl_minutes)
                sync_workspace(root)
                return _emit(
                    {
                        "ok": True,
                        "task": task.to_frontmatter() | {"path": str(task.path)},
                        "next_steps": [
                            f"hive context startup --project {task.project_id} --task {task.id}",
                        ],
                    },
                    args.json,
                )
            if args.task_command == "release":
                task = release_task(root, args.task_id)
                sync_workspace(root)
                return _emit(
                    {
                        "ok": True,
                        "task": task.to_frontmatter() | {"path": str(task.path)},
                    },
                    args.json,
                )
            if args.task_command == "link":
                task = link_tasks(root, args.src_id, args.edge_type, args.dst_id)
                sync_workspace(root)
                return _emit(
                    {
                        "ok": True,
                        "task": task.to_frontmatter() | {"path": str(task.path)},
                    },
                    args.json,
                )
            if args.task_command == "ready":
                return _emit(
                    {
                        "ok": True,
                        "tasks": ready_tasks(root, project_id=args.project_id, limit=args.limit),
                    },
                    args.json,
                )
        except (
            CacheBusyError,
            WorkspaceBusyError,
            FileExistsError,
            FileNotFoundError,
            ValueError,
            sqlite3.Error,
        ) as exc:
            return _emit_error(exc, args.json)

    if args.command == "run":
        try:
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
                return _emit({"ok": True, "run": run.to_dict()}, args.json)
            if args.run_command == "show":
                return _emit({"ok": True, "run": load_run(root, args.run_id)}, args.json)
            if args.run_command == "status":
                run = load_run(root, args.run_id)
                driver_status = run.get("metadata_json", {}).get("driver_status", {})
                return _emit(
                    {
                        "ok": True,
                        "run": run,
                        "status": {
                            "run_id": run["id"],
                            "state": run["status"],
                            "health": run.get("health", "healthy"),
                            "driver": run.get("driver", "local"),
                            "progress": driver_status.get(
                                "progress",
                                {
                                    "phase": "unknown",
                                    "message": "No driver status recorded",
                                    "percent": None,
                                },
                            ),
                            "waiting_on": driver_status.get("waiting_on"),
                            "last_event_at": run.get("finished_at") or run.get("started_at"),
                            "budget": driver_status.get(
                                "budget",
                                {"spent_tokens": 0, "spent_cost_usd": 0.0, "wall_minutes": 0},
                            ),
                            "links": driver_status.get("links", {"driver_ui": None}),
                        },
                    },
                    args.json,
                )
            if args.run_command == "artifacts":
                return _emit({"ok": True} | run_artifacts(root, args.run_id), args.json)
            if args.run_command == "eval":
                payload = eval_run(root, args.run_id)
                sync_workspace(root)
                return _emit({"ok": True} | payload, args.json)
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
                return _emit(response, args.json)
            if args.run_command == "reject":
                payload = reject_run(root, args.run_id, args.reason)
                sync_workspace(root)
                return _emit({"ok": True, "run": payload}, args.json)
            if args.run_command == "escalate":
                payload = escalate_run(root, args.run_id, args.reason)
                sync_workspace(root)
                return _emit({"ok": True, "run": payload}, args.json)
            if args.run_command == "promote":
                payload = promote_run(
                    root,
                    args.run_id,
                    cleanup_worktree=args.cleanup_worktree,
                )
                return _emit({"ok": True} | payload, args.json)
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
                return _emit({"ok": True} | payload, args.json)
            if args.run_command == "cleanup":
                if not args.run_id and not args.terminal:
                    raise ValueError("Specify a run ID or use `hive run cleanup --terminal`.")
                if args.run_id and args.terminal:
                    raise ValueError("Use either a run ID or `--terminal`, not both.")
                if args.terminal:
                    payload = {"cleanups": cleanup_terminal_runs(root)}
                else:
                    payload = {"cleanup": cleanup_run(root, args.run_id)}
                return _emit({"ok": True} | payload, args.json)
        except (
            CacheBusyError,
            WorkspaceBusyError,
            FileNotFoundError,
            ValueError,
            sqlite3.Error,
        ) as exc:
            return _emit_error(exc, args.json)

    if args.command == "steer":
        try:
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
            return _emit(
                {
                    "ok": True,
                    "message": f"Applied steering action {request.action!r} to {args.run_id}",
                }
                | payload,
                args.json,
            )
        except (
            CacheBusyError,
            WorkspaceBusyError,
            FileNotFoundError,
            ValueError,
            sqlite3.Error,
        ) as exc:
            return _emit_error(exc, args.json)

    if args.command == "program":
        try:
            if args.program_command == "doctor":
                diagnosis = doctor_program(root, args.project_ref)
                return _emit(
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
                return _emit(
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
        except (
            CacheBusyError,
            WorkspaceBusyError,
            FileNotFoundError,
            ValueError,
            sqlite3.Error,
        ) as exc:
            return _emit_error(exc, args.json)

    if args.command == "memory":
        try:
            if args.memory_command == "observe":
                output_path = observe(
                    root,
                    transcript_path=args.transcript_path,
                    note=args.note,
                    scope=args.scope,
                    harness=args.harness,
                    project_id=args.project,
                )
                rebuild_cache(root)
                return _emit(
                    {
                        "ok": True,
                        "message": f"Recorded observation at {output_path}",
                        "path": str(output_path),
                    },
                    args.json,
                )
            if args.memory_command == "reflect":
                output_paths = {
                    key: str(value)
                    for key, value in reflect(
                        root,
                        scope=args.scope,
                        project_id=args.project,
                        propose=args.propose,
                    ).items()
                }
                rebuild_cache(root)
                event_type = "memory.proposed" if args.propose else "memory.accepted"
                emit_event(
                    root,
                    actor={"kind": "system", "id": "hive"},
                    entity_type="memory",
                    entity_id=args.project or args.scope,
                    event_type=event_type,
                    source="memory.reflect",
                    payload={"paths": output_paths, "scope": args.scope, "project_id": args.project},
                    project_id=args.project,
                )
                return _emit(
                    {
                        "ok": True,
                        "message": (
                            "Wrote proposed memory review documents"
                            if args.propose
                            else "Wrote reflection documents"
                        ),
                        "paths": output_paths,
                    },
                    args.json,
                )
            if args.memory_command == "accept":
                promoted = accept_memory_review(root, scope=args.scope, project_id=args.project)
                rebuild_cache(root)
                emit_event(
                    root,
                    actor={"kind": "human", "id": "operator"},
                    entity_type="memory",
                    entity_id=args.project or args.scope,
                    event_type="memory.accepted",
                    source="memory.review",
                    payload={"paths": promoted, "scope": args.scope, "project_id": args.project},
                    project_id=args.project,
                )
                return _emit(
                    {
                        "ok": True,
                        "message": "Accepted proposed memory changes",
                        "paths": promoted,
                    },
                    args.json,
                )
            if args.memory_command == "reject":
                removed = reject_memory_review(root, scope=args.scope, project_id=args.project)
                rebuild_cache(root)
                emit_event(
                    root,
                    actor={"kind": "human", "id": "operator"},
                    entity_type="memory",
                    entity_id=args.project or args.scope,
                    event_type="memory.rejected",
                    source="memory.review",
                    payload={"paths": removed, "scope": args.scope, "project_id": args.project},
                    project_id=args.project,
                )
                return _emit(
                    {
                        "ok": True,
                        "message": "Rejected proposed memory changes",
                        "paths": removed,
                    },
                    args.json,
                )
            if args.memory_command == "search":
                return _emit(
                    {
                        "ok": True,
                        "message": f"Found memory results for {args.query!r}",
                        "results": search(
                            root,
                            args.query,
                            scope=args.scope,
                            project_id=args.project,
                            task_id=args.task,
                            limit=args.limit,
                        ),
                    },
                    args.json,
                )
        except (CacheBusyError, FileNotFoundError, ValueError, sqlite3.Error) as exc:
            return _emit_error(exc, args.json)

    if args.command == "context":
        try:
            if args.context_command == "startup":
                bundle = build_context_bundle(
                    root,
                    project_ref=args.project,
                    mode="startup",
                    profile=args.profile,
                    query=args.query,
                    task_id=args.task,
                    refresh=True,
                )
                if args.output:
                    output_path = resolve_workspace_path(root, args.output)
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_text(str(bundle["rendered"]), encoding="utf-8")
                    return _emit(
                        {
                            "ok": True,
                            "message": f"Wrote startup context to {output_path}",
                            "output_path": str(output_path),
                            "project": bundle["project_payload"],
                            "next_steps": [
                                f"Open {output_path}",
                                "Copy the bundle into your agent, or reuse it as a "
                                "handoff artifact.",
                            ],
                        },
                        args.json,
                    )
                if args.json:
                    return _emit({"ok": True, "context": bundle["context"]}, args.json)
                return _emit({"ok": True, "rendered_context": bundle["rendered"]}, args.json)
            if args.context_command == "handoff":
                bundle = build_context_bundle(
                    root,
                    project_ref=args.project,
                    mode="handoff",
                    refresh=True,
                )
                if args.output:
                    output_path = resolve_workspace_path(root, args.output)
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_text(str(bundle["rendered"]), encoding="utf-8")
                    return _emit(
                        {
                            "ok": True,
                            "message": f"Wrote handoff context to {output_path}",
                            "output_path": str(output_path),
                            "project": bundle["project_payload"],
                        },
                        args.json,
                    )
                if args.json:
                    return _emit({"ok": True, "context": bundle["context"]}, args.json)
                return _emit({"ok": True, "rendered_context": bundle["rendered"]}, args.json)
        except (
            CacheBusyError,
            WorkspaceBusyError,
            FileNotFoundError,
            ValueError,
            sqlite3.Error,
        ) as exc:
            return _emit_error(exc, args.json)

    if args.command == "sync" and args.sync_command == "projections":
        try:
            sync_workspace(root)
            return _emit({"ok": True, "message": "Synced projections"}, args.json)
        except (
            CacheBusyError,
            WorkspaceBusyError,
            FileNotFoundError,
            ValueError,
            sqlite3.Error,
        ) as exc:
            return _emit_error(exc, args.json)

    if args.command == "migrate" and args.migrate_command == "v1-to-v2":
        try:
            report = migrate_v1_to_v2(
                root,
                dry_run=args.dry_run,
                project_filter=args.project,
                owner=args.owner,
                rewrite=args.rewrite,
            )
            payload = report.to_dict()
            payload["ok"] = report.ok
            return _emit(payload, args.json)
        except (
            CacheBusyError,
            WorkspaceBusyError,
            FileNotFoundError,
            ValueError,
            sqlite3.Error,
        ) as exc:
            return _emit_error(exc, args.json)

    if args.command == "deps":
        return _emit({"ok": True, "summary": dependency_summary(root)}, args.json)

    if args.command == "portfolio":
        try:
            if args.portfolio_command == "status":
                payload = portfolio_status(root)
                return _emit(
                    {
                        "ok": True,
                        "message": "Loaded portfolio status",
                        "projects": payload["projects"],
                        "tasks": payload["ready_tasks"],
                        "active_runs": payload["active_runs"],
                        "evaluating_runs": payload["evaluating_runs"],
                        "recommendation": payload["recommended_next"],
                        "recent_events": payload["recent_events"],
                    },
                    args.json,
                )
            if args.portfolio_command == "steer":
                if args.pause and args.resume:
                    raise ValueError("Use either --pause or --resume, not both.")
                if args.force_review and args.clear_force_review:
                    raise ValueError(
                        "Use either --force-review or --clear-force-review, not both."
                    )
                payload = steer_project(
                    root,
                    args.project_ref,
                    paused=True if args.pause else False if args.resume else None,
                    focus_task_id=args.focus_task,
                    clear_focus=args.clear_focus,
                    boost=args.boost,
                    force_review=(
                        True
                        if args.force_review
                        else False if args.clear_force_review else None
                    ),
                    note=args.note,
                    actor=args.owner,
                )
                return _emit(
                    {
                        "ok": True,
                        "message": f"Updated steering for {payload['project']['id']}",
                        "project": payload["project"],
                        "steering": payload["steering"],
                    },
                    args.json,
                )
            if args.portfolio_command == "tick":
                payload = tick_portfolio(
                    root,
                    mode=args.mode,
                    owner=args.owner,
                    project_id=args.project_id,
                    profile=args.profile,
                    output_path=args.output,
                    run_id=args.run_id,
                )
                response = {"ok": True, "message": f"Completed portfolio tick in {args.mode} mode"}
                response.update(payload)
                return _emit(response, args.json)
        except (
            CacheBusyError,
            WorkspaceBusyError,
            FileNotFoundError,
            ValueError,
            sqlite3.Error,
        ) as exc:
            return _emit_error(exc, args.json)

    if args.command == "campaign":
        try:
            if args.campaign_command == "list":
                campaigns = []
                from src.hive.store.campaigns import list_campaigns  # pylint: disable=import-outside-toplevel

                for campaign in list_campaigns(root):
                    if args.project_id and args.project_id not in campaign.project_ids:
                        continue
                    campaigns.append(campaign_status(root, campaign.id)["campaign"])
                return _emit({"ok": True, "campaigns": campaigns}, args.json)
            if args.campaign_command == "create":
                payload = create_campaign_flow(
                    root,
                    title=args.title,
                    goal=args.goal,
                    project_ids=_clean_string_list(args.project_id),
                    driver=args.driver,
                    model=args.model,
                    cadence=args.cadence,
                    brief_cadence=args.brief_cadence,
                    max_active_runs=args.max_active_runs,
                    notes_md=(args.notes or "").strip(),
                )
                sync_workspace(root)
                return _emit({"ok": True} | payload, args.json)
            if args.campaign_command == "status":
                return _emit({"ok": True} | campaign_status(root, args.campaign_id), args.json)
            if args.campaign_command == "tick":
                payload = tick_campaign(root, args.campaign_id, owner=args.owner)
                sync_workspace(root)
                return _emit({"ok": True} | payload, args.json)
        except (
            CacheBusyError,
            WorkspaceBusyError,
            FileExistsError,
            FileNotFoundError,
            ValueError,
            sqlite3.Error,
        ) as exc:
            return _emit_error(exc, args.json)

    if args.command == "brief":
        try:
            cadence = "daily" if args.brief_command == "daily" else "weekly"
            payload = generate_brief(root, cadence=cadence)
            sync_workspace(root)
            return _emit({"ok": True} | payload, args.json)
        except (
            CacheBusyError,
            WorkspaceBusyError,
            FileNotFoundError,
            ValueError,
            sqlite3.Error,
        ) as exc:
            return _emit_error(exc, args.json)

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

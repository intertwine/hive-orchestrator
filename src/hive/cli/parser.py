"""Argument parser construction for the Hive CLI."""

# pylint: disable=line-too-long,too-many-lines,too-many-locals,too-many-statements
# pylint: disable=too-many-branches

from __future__ import annotations

import argparse
from pathlib import Path

from src.hive import __version__


def _add_bootstrap_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    quickstart_parser = subparsers.add_parser(
        "quickstart",
        help="Legacy compatibility alias for `hive onboard`.",
        description="Legacy compatibility alias for `hive onboard`. Prefer `hive onboard`.",
    )
    quickstart_parser.add_argument("slug", nargs="?", default="demo")
    quickstart_parser.add_argument("--title")
    quickstart_parser.add_argument(
        "--objective",
        "--prompt",
        dest="objective",
        help="Plain-English project goal used to seed the starter project and task chain.",
    )

    onboard_parser = subparsers.add_parser(
        "onboard",
        help="Recommended fresh-workspace bootstrap with a starter project and task chain.",
    )
    onboard_parser.add_argument("slug", nargs="?", default="demo")
    onboard_parser.add_argument("--title")
    onboard_parser.add_argument(
        "--objective",
        "--prompt",
        dest="objective",
        help="Plain-English project goal used to seed the starter project and task chain.",
    )

    adopt_parser = subparsers.add_parser("adopt")
    adopt_parser.add_argument("slug", nargs="?")
    adopt_parser.add_argument("--title")
    adopt_parser.add_argument(
        "--objective",
        "--prompt",
        dest="objective",
        help="Plain-English project goal used to seed the starter project and task chain.",
    )

    subparsers.add_parser(
        "init",
        help="Bootstrap only the base Hive layout without creating a starter project.",
    )

    doctor_parser = subparsers.add_parser("doctor")
    doctor_subparsers = doctor_parser.add_subparsers(dest="doctor_command")
    doctor_subparsers.add_parser("workspace")
    doctor_program = doctor_subparsers.add_parser("program")
    doctor_program.add_argument("project_ref")


def _add_control_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
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
        "--print-context",
        action="store_true",
        help="Print the startup context bundle to stdout instead of the summary view.",
    )
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

    driver_parser = subparsers.add_parser("driver")
    driver_subparsers = driver_parser.add_subparsers(dest="driver_command")
    driver_doctor = driver_subparsers.add_parser("doctor")
    driver_doctor.add_argument("driver", nargs="?")

    sandbox_parser = subparsers.add_parser("sandbox")
    sandbox_subparsers = sandbox_parser.add_subparsers(dest="sandbox_command")
    sandbox_doctor = sandbox_subparsers.add_parser("doctor")
    sandbox_doctor.add_argument("backend", nargs="?")

    integrate_parser = subparsers.add_parser(
        "integrate",
        help="Inspect v2.4 adapter integrations alongside legacy drivers.",
    )
    integrate_subparsers = integrate_parser.add_subparsers(dest="integrate_command")
    integrate_subparsers.add_parser(
        "list", help="List all backends (legacy drivers + v2.4 adapters)."
    )
    integrate_doctor = integrate_subparsers.add_parser(
        "doctor", help="Probe one or all integrations."
    )
    integrate_doctor.add_argument("name", nargs="?", help="Integration name to probe.")
    integrate_subparsers.add_parser(
        "pi", help="Prepare or verify Pi companion integration."
    )
    integrate_subparsers.add_parser(
        "openclaw", help="Prepare or verify OpenClaw Gateway bridge integration."
    )

    integrate_attach = integrate_subparsers.add_parser(
        "attach", help="Attach a native harness session to Hive as a delegate."
    )
    integrate_attach.add_argument("harness", help="Integration name (e.g. openclaw).")
    integrate_attach.add_argument(
        "native_session_ref", help="Native session key or ID."
    )
    integrate_attach.add_argument("--project-id", dest="project_id")
    integrate_attach.add_argument("--task-id", dest="task_id")

    integrate_detach = integrate_subparsers.add_parser(
        "detach", help="Detach a delegate session."
    )
    integrate_detach.add_argument("session_id", help="Delegate session ID to detach.")


def _add_project_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    project_parser = subparsers.add_parser("project")
    project_subparsers = project_parser.add_subparsers(dest="project_command")
    project_subparsers.add_parser("list")
    project_create = project_subparsers.add_parser("create")
    project_create.add_argument("slug")
    project_create.add_argument("--title")
    project_create.add_argument("--project-id")
    project_create.add_argument("--status", default="active")
    project_create.add_argument("--priority", type=int, default=2)
    project_create.add_argument(
        "--objective",
        "--prompt",
        dest="objective",
        help="Plain-English project goal used to seed the project mission.",
    )
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
    task_release = task_subparsers.add_parser(
        "release",
        help="Release a claim or governed run back to the ready queue.",
        description=(
            "Release a task back to the ready queue. If the task still has an active governed "
            "run, Hive will cancel that run before releasing the task."
        ),
    )
    task_release.add_argument("task_id")
    task_link = task_subparsers.add_parser("link")
    task_link.add_argument("src_id")
    task_link.add_argument("edge_type")
    task_link.add_argument("dst_id")
    task_ready = task_subparsers.add_parser(
        "ready",
        help="List ready tasks, or mark one task ready when you pass a task id.",
        description=(
            "Without arguments, list the ranked ready queue. With `<task-id>`, mark that one "
            "task ready as a shortcut for `hive task update <task-id> --status ready`."
        ),
    )
    task_ready.add_argument("task_id", nargs="?")
    task_ready.add_argument("--project-id")
    task_ready.add_argument("--limit", type=int)


def _add_run_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    run_parser = subparsers.add_parser("run")
    run_subparsers = run_parser.add_subparsers(dest="run_command")
    run_start = run_subparsers.add_parser("start")
    run_start.add_argument("task_id")
    run_start.add_argument("--driver", default="local")
    run_start.add_argument("--model")
    run_start.add_argument("--campaign-id")
    run_start.add_argument("--profile", default="default")
    run_start.add_argument("--attach-native-session")
    run_launch = run_subparsers.add_parser("launch")
    run_launch.add_argument("task_id")
    run_launch.add_argument("--driver", default="local")
    run_launch.add_argument("--model")
    run_launch.add_argument("--campaign-id")
    run_launch.add_argument("--profile", default="default")
    run_launch.add_argument("--attach-native-session")
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
    steer_approve.add_argument("--approval-id")
    steer_approve.add_argument("--owner")
    steer_reject = steer_subparsers.add_parser("reject")
    steer_reject.add_argument("run_id")
    steer_reject.add_argument("--approval-id")
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


def _add_knowledge_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    memory_parser = subparsers.add_parser("memory")
    memory_subparsers = memory_parser.add_subparsers(dest="memory_command")
    memory_observe = memory_subparsers.add_parser("observe")
    memory_observe.add_argument("--transcript-path")
    memory_observe.add_argument("--note")
    memory_observe.add_argument(
        "--scope", choices=["project", "global"], default="project"
    )
    memory_observe.add_argument("--project")
    memory_observe.add_argument("--harness")
    memory_reflect = memory_subparsers.add_parser("reflect")
    memory_reflect.add_argument(
        "--scope", choices=["project", "global"], default="project"
    )
    memory_reflect.add_argument("--project")
    memory_reflect.add_argument("--propose", action="store_true")
    memory_accept = memory_subparsers.add_parser("accept")
    memory_accept.add_argument(
        "--scope", choices=["project", "global"], default="project"
    )
    memory_accept.add_argument("--project")
    memory_reject = memory_subparsers.add_parser("reject")
    memory_reject.add_argument(
        "--scope", choices=["project", "global"], default="project"
    )
    memory_reject.add_argument("--project")
    memory_search = memory_subparsers.add_parser("search")
    memory_search.add_argument("query")
    memory_search.add_argument(
        "--scope", choices=["project", "global", "all"], default="all"
    )
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

    campaign_parser = subparsers.add_parser("campaign")
    campaign_subparsers = campaign_parser.add_subparsers(dest="campaign_command")
    campaign_list = campaign_subparsers.add_parser("list")
    campaign_list.add_argument("--project-id")
    campaign_create = campaign_subparsers.add_parser("create")
    campaign_create.add_argument("--title", required=True)
    campaign_create.add_argument("--goal", required=True)
    campaign_create.add_argument("--project-id", action="append", required=True)
    campaign_create.add_argument(
        "--type",
        choices=["delivery", "research", "maintenance", "review"],
        default="delivery",
    )
    campaign_create.add_argument("--driver", default="local")
    campaign_create.add_argument("--model")
    campaign_create.add_argument("--sandbox-profile")
    campaign_create.add_argument("--cadence", default="daily")
    campaign_create.add_argument("--brief-cadence", default="daily")
    campaign_create.add_argument("--max-active-runs", type=int, default=1)
    campaign_create.add_argument("--lane-quota", action="append")
    campaign_create.add_argument("--budget-cap-usd", type=float)
    campaign_create.add_argument("--budget-cap-tokens", type=int)
    campaign_create.add_argument("--escalation-mode")
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


def build_parser() -> argparse.ArgumentParser:
    """Build the Hive CLI parser."""
    parser = argparse.ArgumentParser(
        prog="hive", description="Hive v2.3 control-plane CLI"
    )
    parser.add_argument("--path", default=str(Path.cwd()), help="Workspace base path")
    parser.add_argument(
        "--json", action="store_true", help="Emit machine-readable JSON"
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command")
    _add_bootstrap_parsers(subparsers)
    _add_control_parsers(subparsers)
    _add_project_parsers(subparsers)
    _add_run_parsers(subparsers)
    _add_knowledge_parsers(subparsers)
    visible_commands = [name for name in subparsers.choices if name != "quickstart"]
    subparsers.metavar = "{" + ",".join(visible_commands) + "}"
    return parser

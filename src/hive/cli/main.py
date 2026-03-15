"""Hive 2.0 CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.hive import __version__
from src.hive.codemode.execute import MAX_EXECUTE_BYTES, execute_code
from src.hive.memory.context import handoff_context, startup_context
from src.hive.memory.observe import observe
from src.hive.memory.reflect import reflect
from src.hive.memory.search import search
from src.hive.migrate.v1_to_v2 import migrate_v1_to_v2
from src.hive.scaffold import starter_task_specs
from src.hive.search import search_workspace
from src.hive.projections.agency_md import sync_agency_md
from src.hive.projections.agents_md import sync_agents_md
from src.hive.projections.global_md import sync_global_md
from src.hive.runs.engine import accept_run, escalate_run, eval_run, load_run, reject_run, start_run
from src.hive.scheduler.query import dependency_summary, project_summary, ready_tasks
from src.hive.store.cache import rebuild_cache
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


def _emit(payload: dict, as_json: bool) -> int:
    payload.setdefault("version", __version__)
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(payload.get("message") or json.dumps(payload, indent=2, sort_keys=True))
    return 0


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
            'Run `hive quickstart demo --title "Demo project" --json` '
            "to bootstrap a workspace with a starter project and ready task."
        )
        next_steps.append("Run `hive init --json` to bootstrap the workspace.")
    if checks["layout"] and not checks["global_md"]:
        next_steps.append("Run `hive sync projections --json` to create `GLOBAL.md`.")
    if checks["layout"] and not checks["agents_md"]:
        next_steps.append("Run `hive sync projections --json` to create `AGENTS.md`.")
    if checks["layout"] and not projects:
        next_steps.append(
            'Run `hive quickstart demo --title "Demo project" --json` '
            "to scaffold a working project with starter tasks."
        )
        next_steps.append(
            'Run `hive project create demo --title "Demo project" --json` '
            "to scaffold your first project."
        )
    elif projects and not tasks:
        first_project = projects[0]
        next_steps.append(
            "Run "
            f"`hive task create --project-id {first_project.id} "
            f'--title "Define the first slice" --json` '
            "to create canonical work."
        )
        next_steps.append(
            "If you still have legacy checkbox tasks, run "
            "`hive migrate v1-to-v2 --json` to import them."
        )
    elif ready:
        top_task = ready[0]
        next_steps.append(
            "Run "
            f"`hive context startup --project {top_task['project_id']} "
            f"--task {top_task['id']} --json` "
            "to start work on the top ready task."
        )
    elif tasks:
        next_steps.append(
            "Run `hive task list --json` to inspect blocked, claimed, or completed work."
        )
    if checks["layout"] and not checks["cache"]:
        next_steps.append(
            "Run `hive sync projections --json` to rebuild the cache and refresh rollups."
        )

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
    parser = argparse.ArgumentParser(prog="hive", description="Hive 2.0 CLI")
    parser.add_argument("--path", default=str(Path.cwd()), help="Workspace base path")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    subparsers = parser.add_subparsers(dest="command")

    quickstart_parser = subparsers.add_parser("quickstart")
    quickstart_parser.add_argument("slug", nargs="?", default="demo")
    quickstart_parser.add_argument("--title")
    quickstart_parser.add_argument("--objective")

    subparsers.add_parser("init")
    subparsers.add_parser("doctor")
    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("query")
    search_parser.add_argument("--scope", action="append")
    search_parser.add_argument("--limit", type=int, default=8)
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
    task_update = task_subparsers.add_parser("update")
    task_update.add_argument("task_id")
    task_update.add_argument("--title")
    task_update.add_argument("--status")
    task_update.add_argument("--priority", type=int)
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
    run_show = run_subparsers.add_parser("show")
    run_show.add_argument("run_id")
    run_eval = run_subparsers.add_parser("eval")
    run_eval.add_argument("run_id")
    run_accept = run_subparsers.add_parser("accept")
    run_accept.add_argument("run_id")
    run_reject = run_subparsers.add_parser("reject")
    run_reject.add_argument("run_id")
    run_reject.add_argument("--reason")
    run_escalate = run_subparsers.add_parser("escalate")
    run_escalate.add_argument("run_id")
    run_escalate.add_argument("--reason")

    memory_parser = subparsers.add_parser("memory")
    memory_subparsers = memory_parser.add_subparsers(dest="memory_command")
    memory_observe = memory_subparsers.add_parser("observe")
    memory_observe.add_argument("--transcript-path")
    memory_observe.add_argument("--note")
    memory_observe.add_argument("--scope", choices=["project", "global"], default="project")
    memory_observe.add_argument("--harness")
    memory_reflect = memory_subparsers.add_parser("reflect")
    memory_reflect.add_argument("--scope", choices=["project", "global"], default="project")
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
    context_handoff = context_subparsers.add_parser("handoff")
    context_handoff.add_argument("--project", required=True)

    sync_parser = subparsers.add_parser("sync")
    sync_subparsers = sync_parser.add_subparsers(dest="sync_command")
    sync_subparsers.add_parser("projections")

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
            sync_global_md(root)
            sync_agency_md(root)
            sync_agents_md(root)
            rebuild_cache(root)
        except (FileExistsError, ValueError) as exc:
            _emit({"ok": False, "error": str(exc), "message": str(exc)}, args.json)
            return 1

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
                    f"hive task ready --project-id {project.id} --json",
                    f"hive task claim {first_task.id} --owner <your-name> --ttl-minutes 60 --json",
                    f"hive context startup --project {project.id} --task {first_task.id} --json",
                ],
            },
            args.json,
        )

    if args.command == "init":
        bootstrapped = bootstrap_workspace(root)
        sync_global_md(root)
        sync_agency_md(root)
        sync_agents_md(root)
        rebuild_cache(root)
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

    if args.command == "doctor":
        return _emit(_doctor_payload(root), args.json)

    if args.command == "search":
        return _emit(
            {
                "ok": True,
                "results": search_workspace(root, args.query, scopes=args.scope, limit=args.limit),
            },
            args.json,
        )

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
        db_path = rebuild_cache(root)
        return _emit(
            {"ok": True, "message": f"Rebuilt cache at {db_path}", "path": str(db_path)}, args.json
        )

    if args.command == "project":
        if args.project_command == "list":
            return _emit({"ok": True, "projects": project_summary(root)}, args.json)
        if args.project_command == "create":
            try:
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
            except (FileExistsError, ValueError) as exc:
                _emit({"ok": False, "error": str(exc), "message": str(exc)}, args.json)
                return 1
            sync_global_md(root)
            sync_agency_md(root)
            sync_agents_md(root)
            rebuild_cache(root)
            return _emit(
                {
                    "ok": True,
                    "project": _project_payload(project),
                    "next_steps": [
                        "Run "
                        f"`hive task create --project-id {project.id} "
                        f'--title "Define the first slice" --json` '
                        "to add canonical work.",
                        f"Run `hive context startup --project {project.id} --json` "
                        "to build startup context.",
                    ],
                },
                args.json,
            )
        if args.project_command == "show":
            project = get_project(root, args.project_id)
            return _emit({"ok": True, "project": _project_payload(project)}, args.json)
        if args.project_command == "sync":
            sync_global_md(root)
            sync_agency_md(root)
            sync_agents_md(root)
            rebuild_cache(root)
            return _emit({"ok": True, "message": "Synced projections"}, args.json)

    if args.command == "task":
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
                    "tasks": [task.to_frontmatter() | {"path": str(task.path)} for task in tasks],
                },
                args.json,
            )
        if args.task_command == "show":
            task = get_task(root, args.task_id)
            return _emit(
                {"ok": True, "task": task.to_frontmatter() | {"path": str(task.path)}}, args.json
            )
        if args.task_command == "create":
            task = create_task(
                root,
                args.project_id,
                args.title,
                kind=args.kind,
                status=args.status,
                priority=args.priority,
            )
            return _emit(
                {"ok": True, "task": task.to_frontmatter() | {"path": str(task.path)}}, args.json
            )
        if args.task_command == "update":
            patch = {}
            for field in ["title", "status", "priority"]:
                value = getattr(args, field)
                if value is not None:
                    patch[field] = value
            task = update_task(root, args.task_id, patch)
            return _emit(
                {"ok": True, "task": task.to_frontmatter() | {"path": str(task.path)}}, args.json
            )
        if args.task_command == "claim":
            task = claim_task(root, args.task_id, args.owner, args.ttl_minutes)
            rebuild_cache(root)
            return _emit(
                {"ok": True, "task": task.to_frontmatter() | {"path": str(task.path)}}, args.json
            )
        if args.task_command == "release":
            task = release_task(root, args.task_id)
            rebuild_cache(root)
            return _emit(
                {"ok": True, "task": task.to_frontmatter() | {"path": str(task.path)}}, args.json
            )
        if args.task_command == "link":
            task = link_tasks(root, args.src_id, args.edge_type, args.dst_id)
            rebuild_cache(root)
            return _emit(
                {"ok": True, "task": task.to_frontmatter() | {"path": str(task.path)}}, args.json
            )
        if args.task_command == "ready":
            return _emit(
                {
                    "ok": True,
                    "tasks": ready_tasks(root, project_id=args.project_id, limit=args.limit),
                },
                args.json,
            )

    if args.command == "run":
        if args.run_command == "start":
            run = start_run(root, args.task_id)
            rebuild_cache(root)
            return _emit({"ok": True, "run": run.to_dict()}, args.json)
        if args.run_command == "show":
            return _emit({"ok": True, "run": load_run(root, args.run_id)}, args.json)
        if args.run_command == "eval":
            payload = eval_run(root, args.run_id)
            rebuild_cache(root)
            return _emit({"ok": True} | payload, args.json)
        if args.run_command == "accept":
            payload = accept_run(root, args.run_id)
            rebuild_cache(root)
            return _emit({"ok": True, "run": payload}, args.json)
        if args.run_command == "reject":
            payload = reject_run(root, args.run_id, args.reason)
            rebuild_cache(root)
            return _emit({"ok": True, "run": payload}, args.json)
        if args.run_command == "escalate":
            payload = escalate_run(root, args.run_id, args.reason)
            rebuild_cache(root)
            return _emit({"ok": True, "run": payload}, args.json)

    if args.command == "memory":
        if args.memory_command == "observe":
            output_path = observe(
                root,
                transcript_path=args.transcript_path,
                note=args.note,
                scope=args.scope,
                harness=args.harness,
            )
            rebuild_cache(root)
            return _emit({"ok": True, "path": str(output_path)}, args.json)
        if args.memory_command == "reflect":
            output_paths = {
                key: str(value) for key, value in reflect(root, scope=args.scope).items()
            }
            rebuild_cache(root)
            return _emit({"ok": True, "paths": output_paths}, args.json)
        if args.memory_command == "search":
            return _emit(
                {
                    "ok": True,
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

    if args.command == "context":
        if args.context_command == "startup":
            payload = startup_context(
                root,
                project_id=args.project,
                profile=args.profile,
                query=args.query,
                task_id=args.task,
            )
            return _emit({"ok": True, "context": payload}, args.json)
        if args.context_command == "handoff":
            return _emit(
                {"ok": True, "context": handoff_context(root, project_id=args.project)}, args.json
            )

    if args.command == "sync" and args.sync_command == "projections":
        sync_global_md(root)
        sync_agency_md(root)
        sync_agents_md(root)
        rebuild_cache(root)
        return _emit({"ok": True, "message": "Synced projections"}, args.json)

    if args.command == "migrate" and args.migrate_command == "v1-to-v2":
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

    if args.command == "deps":
        return _emit({"ok": True, "summary": dependency_summary(root)}, args.json)

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

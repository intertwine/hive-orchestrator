"""Project and task Hive CLI commands."""

# pylint: disable=line-too-long,too-many-lines,too-many-locals,too-many-statements
# pylint: disable=too-many-branches,too-many-return-statements,import-outside-toplevel

from __future__ import annotations

import sqlite3
from pathlib import Path

from src.hive.cli.common import clean_string_list, emit, emit_error, project_payload
from src.hive.control import release_task_flow
from src.hive.scheduler.query import project_summary, ready_tasks
from src.hive.store.cache import CacheBusyError
from src.hive.store.projects import create_project, get_project
from src.hive.store.task_files import claim_task, create_task, get_task, link_tasks, list_tasks, update_task
from src.hive.workspace import WorkspaceBusyError, sync_workspace
from src.hive.runs.worktree import create_checkpoint_commit


def dispatch(args, root: Path) -> int:
    """Dispatch project, workspace, and task commands."""
    try:
        if args.command == "project":
            if args.project_command == "list":
                return emit({"ok": True, "projects": project_summary(root)}, args.json)
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
                return emit(
                    {
                        "ok": True,
                        "project": project_payload(project),
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
                return emit({"ok": True, "project": project_payload(project)}, args.json)
            if args.project_command == "sync":
                sync_workspace(root)
                return emit({"ok": True, "message": "Synced projections"}, args.json)
        if args.command == "workspace" and args.workspace_command == "checkpoint":
            payload = create_checkpoint_commit(root, message=args.message)
            return emit({"ok": True} | payload, args.json)
        if args.command == "task":
            if args.task_command == "list":
                tasks = list_tasks(root)
                if args.project_id:
                    tasks = [task for task in tasks if task.project_id == args.project_id]
                if args.status:
                    statuses = set(args.status)
                    tasks = [task for task in tasks if task.status in statuses]
                return emit(
                    {"ok": True, "tasks": [task.to_frontmatter() | {"path": str(task.path)} for task in tasks]},
                    args.json,
                )
            if args.task_command == "show":
                task = get_task(root, args.task_id)
                return emit({"ok": True, "task": task.to_frontmatter() | {"path": str(task.path)}}, args.json)
            if args.task_command == "create":
                task = create_task(
                    root,
                    args.project_id,
                    args.title,
                    kind=args.kind,
                    status=args.status,
                    priority=args.priority,
                    parent_id=args.parent_id,
                    labels=clean_string_list(args.label),
                    relevant_files=clean_string_list(args.relevant_file),
                    acceptance=clean_string_list(args.acceptance),
                    summary_md=(args.summary or "").strip(),
                    notes_md=(args.notes or "").strip(),
                    history_md=(args.history or "").strip(),
                )
                sync_workspace(root)
                return emit(
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
                    patch["labels"] = clean_string_list(args.label)
                if args.clear_relevant_files:
                    patch["relevant_files"] = []
                elif args.relevant_file is not None:
                    patch["relevant_files"] = clean_string_list(args.relevant_file)
                if args.clear_acceptance:
                    patch["acceptance"] = []
                elif args.acceptance is not None:
                    patch["acceptance"] = clean_string_list(args.acceptance)
                if args.summary is not None:
                    patch["summary_md"] = args.summary.strip()
                if args.notes is not None:
                    patch["notes_md"] = args.notes.strip()
                if args.history is not None:
                    patch["history_md"] = args.history.strip()
                task = update_task(root, args.task_id, patch)
                sync_workspace(root)
                return emit({"ok": True, "task": task.to_frontmatter() | {"path": str(task.path)}}, args.json)
            if args.task_command == "claim":
                task = claim_task(root, args.task_id, args.owner, args.ttl_minutes)
                sync_workspace(root)
                return emit(
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
                payload = release_task_flow(root, args.task_id)
                payload.update(
                    {
                        "ok": True,
                        "message": (
                            f"Released task {args.task_id} back to the ready queue."
                            if not payload["cancelled_runs"]
                            else f"Released task {args.task_id} and cancelled its active runs."
                        ),
                    }
                )
                if payload["cancelled_runs"]:
                    payload["next_steps"] = [
                        f"hive next --project-id {payload['task']['project_id']}",
                    ]
                return emit(payload, args.json)
            if args.task_command == "link":
                task = link_tasks(root, args.src_id, args.edge_type, args.dst_id)
                sync_workspace(root)
                return emit({"ok": True, "task": task.to_frontmatter() | {"path": str(task.path)}}, args.json)
            if args.task_command == "ready":
                if args.task_id:
                    if args.project_id or args.limit is not None:
                        raise ValueError(
                            "`hive task ready <task-id>` marks one task ready; do not combine it "
                            "with `--project-id` or `--limit`."
                        )
                    task = update_task(root, args.task_id, {"status": "ready"})
                    sync_workspace(root)
                    return emit(
                        {
                            "ok": True,
                            "message": f"Marked task {args.task_id} as ready.",
                            "task": task.to_frontmatter() | {"path": str(task.path)},
                        },
                        args.json,
                    )
                return emit(
                    {"ok": True, "tasks": ready_tasks(root, project_id=args.project_id, limit=args.limit)},
                    args.json,
                )
    except (CacheBusyError, WorkspaceBusyError, FileExistsError, FileNotFoundError, ValueError, sqlite3.Error) as exc:
        return emit_error(exc, args.json)
    return 0

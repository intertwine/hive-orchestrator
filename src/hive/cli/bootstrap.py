"""Bootstrap-oriented Hive CLI commands."""

# pylint: disable=line-too-long,too-many-lines,too-many-locals,too-many-statements
# pylint: disable=too-many-branches,too-many-return-statements

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from src.hive.cli.common import _doctor_payload, emit, emit_error, project_payload
from src.hive.scaffold import starter_task_specs as _starter_task_specs
from src.hive.store.cache import CacheBusyError
from src.hive.store.layout import bootstrap_workspace
from src.hive.store.projects import create_project
from src.hive.store.task_files import create_task, link_tasks
from src.hive.workspace import WorkspaceBusyError, sync_workspace
from src.hive.onboarding import adopt_repository, onboard_workspace
from src.hive.program import doctor_program


def _starter_specs():
    """Resolve the starter task factory through the public CLI module for test compatibility."""
    public_main = sys.modules.get("hive.cli.main")
    override = getattr(public_main, "starter_task_specs", None)
    if callable(override):
        return override
    return _starter_task_specs


def _guided_next_steps(payload: dict[str, object]) -> list[str]:
    """Return onboarding/adoption next steps that match the project policy state."""
    project = dict(payload.get("project", {}))
    project_id = str(project.get("id", "")).strip()
    diagnosis = dict(payload.get("program", {}))
    next_steps: list[str] = []
    if project_id:
        next_steps.append(f"hive next --project-id {project_id}")
    if diagnosis.get("blocked_autonomous_promotion"):
        if project_id:
            next_steps.append(f"hive program doctor {project_id}")
    elif project_id:
        next_steps.append(f"hive work --project-id {project_id} --owner <your-name>")
    applied_template = dict(diagnosis.get("applied_template", {}))
    if applied_template.get("id") == "local-smoke" and project_id:
        next_steps.append(
            "Later, replace the starter `local-smoke` evaluator by editing "
            f"`projects/{project_id}/PROGRAM.md` and running "
            f"`hive program add-evaluator {project_id} <real-evaluator-id>`."
        )
    return next_steps


def dispatch(args, root: Path) -> int:
    """Dispatch bootstrap-style commands."""
    try:
        if args.command == "quickstart":
            bootstrapped = bootstrap_workspace(root)
            project = create_project(
                root,
                args.slug,
                title=args.title,
                objective=args.objective,
            )
            starter_tasks = []
            for spec in _starter_specs()(project.title):
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
            return emit(
                {
                    "ok": True,
                    "message": (
                        f"Quickstarted Hive workspace at {root} with project {project.id} "
                        f"and {len(starter_tasks)} starter tasks"
                    ),
                    "layout": {key: str(value) for key, value in bootstrapped["layout"].items()},
                    "created_files": bootstrapped["created_files"],
                    "updated_files": bootstrapped["updated_files"],
                    "project": project_payload(project),
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
        if args.command == "init":
            bootstrapped = bootstrap_workspace(root)
            sync_workspace(root)
            doctor = _doctor_payload(root)
            return emit(
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
        if args.command == "onboard":
            payload = onboard_workspace(
                root,
                slug=args.slug,
                title=args.title,
                objective=args.objective,
            )
            return emit(
                {
                    "ok": True,
                    "message": f"Onboarded Hive workspace at {root}",
                    "next_steps": _guided_next_steps(payload),
                    **payload,
                },
                args.json,
            )
        if args.command == "adopt":
            payload = adopt_repository(
                root,
                slug=args.slug,
                title=args.title,
                objective=args.objective,
            )
            return emit(
                {
                    "ok": True,
                    "message": f"Adopted repository at {root} into Hive",
                    "next_steps": _guided_next_steps(payload),
                    **payload,
                },
                args.json,
            )
        if args.command == "doctor":
            if args.doctor_command in {None, "workspace"}:
                return emit(_doctor_payload(root), args.json)
            if args.doctor_command == "program":
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
    except (CacheBusyError, WorkspaceBusyError, FileExistsError, FileNotFoundError, ValueError, sqlite3.Error) as exc:
        return emit_error(exc, args.json)
    return 0

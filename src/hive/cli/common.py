"""Shared helpers for Hive CLI commands."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from src.hive import __version__
from src.hive.codemode.execute import MAX_EXECUTE_BYTES
from src.hive.payloads import project_payload
from src.hive.store.projects import discover_projects
from src.hive.store.task_files import list_tasks
from src.hive.scheduler.query import ready_tasks
from src.hive.store.cache import CacheBusyError
from src.hive.workspace import WorkspaceBusyError
from src.hive.cli.render import render_payload

__all__ = [
    "clean_string_list",
    "emit",
    "emit_error",
    "load_execute_code",
    "project_payload",
]


def emit(payload: dict, as_json: bool) -> int:
    """Render a CLI payload and return an exit status."""
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


def emit_error(exc: Exception, as_json: bool) -> int:
    """Render a CLI error payload."""
    message = _error_message(exc)
    emit({"ok": False, "error": message, "message": message}, as_json)
    return 1


def load_execute_code(args) -> str:
    """Load bounded execute code from an inline string or file."""
    max_bytes = MAX_EXECUTE_BYTES
    if args.file:
        file_path = Path(args.file)
        if file_path.stat().st_size > max_bytes:
            raise ValueError(f"Execute input exceeds {max_bytes} bytes: {file_path}")
        return file_path.read_text(encoding="utf-8")

    code = args.code or ""
    if len(code.encode("utf-8")) > max_bytes:
        raise ValueError(f"Execute input exceeds {max_bytes} bytes")
    return code


def clean_string_list(values: list[str] | None) -> list[str]:
    """Strip blanks from a string list."""
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
            'Run `hive onboard demo --title "Demo project"` '
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
            'Run `hive onboard demo --title "Demo project"` '
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
        next_steps.append(
            "Run `hive sync projections` to rebuild the cache and refresh rollups."
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


def launch_console_api(root: Path, host: str, port: int, as_json: bool) -> int:
    """Launch the console API process."""
    try:
        import fastapi  # noqa: F401  # pylint: disable=unused-import,import-outside-toplevel
        import uvicorn  # noqa: F401  # pylint: disable=unused-import,import-outside-toplevel
    except ImportError:
        emit(
            {
                "ok": False,
                "error": (
                    "Console support is not installed. Install it with "
                    "`uv tool install 'mellona-hive[console]'`, "
                    "`pipx install 'mellona-hive[console]'`, or "
                    "`python -m pip install 'mellona-hive[console]'`."
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


def launch_dashboard(root: Path, host: str, port: int, as_json: bool) -> int:
    """Launch the dashboard compatibility wrapper."""
    return launch_console_api(root, host, port, as_json)


def console_url(host: str, port: int) -> str:
    """Return the web URL for the console."""
    return f"http://{host}:{port}/console/"


def open_console(root: Path, host: str, port: int, as_json: bool, *, no_browser: bool) -> int:
    """Open the console in a browser or emit the URL."""
    url = console_url(host, port)
    payload = {
        "ok": True,
        "message": (
            f"Start the console server with `hive console serve --host {host} "
            f"--port {port}`"
        ),
        "url": url,
        "workspace": str(root),
    }
    if no_browser:
        return emit(payload, as_json)
    try:
        import webbrowser  # pylint: disable=import-outside-toplevel

        opened = webbrowser.open(url)
    except Exception:  # pylint: disable=broad-exception-caught
        # Browser availability is environment-specific.
        opened = False
    payload["opened"] = opened
    if not opened:
        payload["message"] = (
            f"Console URL: {url}. Start the server with "
            f"`hive console serve --host {host} --port {port}`."
        )
    return emit(payload, as_json)

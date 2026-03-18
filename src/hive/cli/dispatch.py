"""Top-level dispatch for Hive CLI commands."""

# pylint: disable=line-too-long,too-many-lines,too-many-locals,too-many-statements
# pylint: disable=too-many-branches,too-many-return-statements

from __future__ import annotations

from pathlib import Path

from src.hive.cli import bootstrap, control, knowledge, project, run


def dispatch(args, root: Path) -> int:
    """Route the parsed CLI args to the appropriate command family."""
    if args.command in {"quickstart", "init", "onboard", "adopt", "doctor"}:
        return bootstrap.dispatch(args, root)
    if args.command in {"next", "work", "finish", "dashboard", "console", "search", "execute", "cache", "drivers"}:
        return control.dispatch(args, root)
    if args.command in {"project", "workspace", "task"}:
        return project.dispatch(args, root)
    if args.command in {"run", "steer", "program"}:
        return run.dispatch(args, root)
    if args.command in {"memory", "context", "sync", "migrate", "deps", "portfolio", "campaign", "brief"}:
        return knowledge.dispatch(args, root)
    return 0

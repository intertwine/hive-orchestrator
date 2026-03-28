"""CLI handler for `hive integrate` commands."""

from __future__ import annotations

from pathlib import Path

from src.hive.cli.common import emit, emit_error
from src.hive.integrations.registry import (
    get_integration,
    list_all_backends,
    list_integrations,
)


def dispatch(args, root: Path) -> int:
    """Dispatch integrate subcommands."""
    try:
        if args.integrate_command == "list":
            backends = list_all_backends()
            return emit({"ok": True, "backends": backends}, args.json)

        if args.integrate_command == "doctor":
            if args.name:
                adapter = get_integration(args.name)
                info = adapter.probe()
                entries = [info.to_dict()]
            else:
                entries = [a.probe().to_dict() for a in list_integrations()]
                if not entries:
                    entries = []
            return emit(
                {
                    "ok": True,
                    "message": "Integration doctor inspected the v2.4 adapter surface.",
                    "integrations": entries,
                },
                args.json,
            )
    except (FileNotFoundError, ValueError) as exc:
        return emit_error(exc, args.json)
    return 0

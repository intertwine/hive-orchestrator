"""Hive 2.0 CLI."""

from __future__ import annotations

import sys
from pathlib import Path

from src.hive.cli.dispatch import dispatch
from src.hive.cli.parser import build_parser
from src.hive.scaffold import starter_task_specs  # pylint: disable=unused-import


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
    return dispatch(args, root)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Retired v1 entrypoint kept only to redirect callers to the Hive CLI."""

from __future__ import annotations

import argparse
import sys


RETIREMENT_MESSAGE = """`python -m src.cortex` has been retired.

Use the Hive CLI directly instead:

  hive sync projections
  hive task ready
  hive deps

If you are updating automation, switch it to `hive` commands now.
"""


def build_parser() -> argparse.ArgumentParser:
    """Build the retirement-only parser."""
    parser = argparse.ArgumentParser(
        prog="python -m src.cortex",
        description="Retired Hive v1 entrypoint",
    )
    parser.add_argument(
        "--ready",
        "-r",
        action="store_true",
        help="Ignored; use `hive task ready`.",
    )
    parser.add_argument(
        "--deps",
        "-d",
        action="store_true",
        help="Ignored; use `hive deps`.",
    )
    parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Ignored; use the matching `hive` command.",
    )
    parser.add_argument(
        "--path",
        "-p",
        help="Ignored; run the `hive` command in the target workspace.",
    )
    return parser


def main() -> None:
    """Exit with migration guidance instead of running retired v1 logic."""
    build_parser().parse_args()
    print(RETIREMENT_MESSAGE, file=sys.stderr)
    raise SystemExit(2)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Public entry point for `python -m hive`."""

from __future__ import annotations

from hive.cli.main import main


if __name__ == "__main__":
    raise SystemExit(main())

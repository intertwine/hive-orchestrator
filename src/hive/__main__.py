#!/usr/bin/env python3
"""Entry point for `python -m hive`."""

from __future__ import annotations

from .cli.main import main


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Entry point for `python -m hive_mcp`."""

from __future__ import annotations

import asyncio
import sys


def run() -> int:
    """Run the thin Hive MCP server or explain how to install it."""
    try:
        from .server import main  # pylint: disable=import-outside-toplevel
    except ImportError as exc:
        if exc.name and exc.name.startswith("mcp"):
            print(
                "Hive MCP support is not installed. Install it with "
                "`uv tool install 'agent-hive[mcp]'`, "
                "`pipx install 'agent-hive[mcp]'`, or "
                "`python -m pip install 'agent-hive[mcp]'`.",
                file=sys.stderr,
            )
            return 1
        raise

    asyncio.run(main())
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

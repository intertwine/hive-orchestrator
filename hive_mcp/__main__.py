#!/usr/bin/env python3
"""Entry point for the public Hive MCP package."""

import asyncio

from hive_mcp.server import main


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""Entry point for Hive MCP Server."""

import asyncio
from .server import main

if __name__ == "__main__":
    asyncio.run(main())

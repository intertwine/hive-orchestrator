#!/usr/bin/env python3
"""Thin Hive MCP wrapper exposing the v2 search/execute tool surface."""

from __future__ import annotations

import json
import os
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from src.hive.codemode.execute import execute_code
from src.hive.search import search_workspace


def get_base_path() -> str:
    """Get the base path for the Hive from environment or current directory."""
    return os.getenv("HIVE_BASE_PATH", os.getcwd())


def format_response(success: bool, data: Any = None, error: str | None = None) -> dict[str, Any]:
    """Format a standardized response."""
    return {"success": success, "data": data, "error": error}


# Create the MCP server
app = Server("hive-mcp")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List the thin v2 MCP tool surface."""
    return [
        Tool(
            name="search",
            description=(
                "Search workspace state, API docs, schemas, examples, and project summaries"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"},
                    "scopes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Optional search scopes such as api, examples, project, workspace"
                        ),
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 8,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="execute",
            description="Execute bounded Python against a typed local Hive client",
            inputSchema={
                "type": "object",
                "properties": {
                    "language": {
                        "type": "string",
                        "description": "Execution language. MVP currently supports python.",
                        "default": "python",
                    },
                    "profile": {
                        "type": "string",
                        "description": "Execution profile label",
                        "default": "default",
                    },
                    "code": {
                        "type": "string",
                        "description": (
                            "Python source code that defines `result = ...` or `main(hive)`"
                        ),
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "description": "Maximum wall clock time for the subprocess",
                        "default": 20,
                    },
                },
                "required": ["code"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle the thin v2 MCP tool calls."""
    base_path = get_base_path()

    try:
        if name == "search":
            query = arguments.get("query")
            if not query:
                result = format_response(success=False, error="query is required")
            else:
                results = search_workspace(
                    base_path,
                    query,
                    scopes=arguments.get("scopes"),
                    limit=int(arguments.get("limit", 8)),
                )
                result = format_response(
                    success=True,
                    data={"count": len(results), "results": results},
                )

        elif name == "execute":
            code = arguments.get("code")
            if not code:
                result = format_response(success=False, error="code is required")
            else:
                payload = execute_code(
                    base_path,
                    language=str(arguments.get("language", "python")),
                    code=code,
                    profile=str(arguments.get("profile", "default")),
                    timeout_seconds=int(arguments.get("timeout_seconds", 20)),
                )
                result = format_response(
                    success=bool(payload.get("ok")),
                    data={
                        "value": payload.get("value"),
                        "stdout": payload.get("stdout", ""),
                        "stderr": payload.get("stderr", ""),
                        "language": payload.get("language"),
                        "profile": payload.get("profile"),
                        "timed_out": payload.get("timed_out", False),
                    },
                    error=payload.get("error"),
                )

        else:
            result = format_response(
                success=False,
                error=f"Unknown tool: {name}",
            )

    except Exception as e:  # pylint: disable=broad-except
        result = format_response(success=False, error=str(e))

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def main():
    """Main entry point for the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

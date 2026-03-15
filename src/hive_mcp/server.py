#!/usr/bin/env python3
"""Thin Hive MCP wrapper exposing the v2 search/execute tool surface."""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Add the parent directory to the path so we can import from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.hive.codemode.execute import execute_code  # pylint: disable=wrong-import-position
from src.hive.search import search_workspace  # pylint: disable=wrong-import-position
from security import (  # pylint: disable=wrong-import-position
    safe_load_agency_md,
    safe_dump_agency_md,
    validate_path_within_base,
)


def get_base_path() -> str:
    """Get the base path for the Hive from environment or current directory."""
    return os.getenv("HIVE_BASE_PATH", os.getcwd())


def format_response(success: bool, data: Any = None, error: str = None) -> Dict[str, Any]:
    """Format a standardized response."""
    return {"success": success, "data": data, "error": error}


def format_project(project: Dict[str, Any]) -> Dict[str, Any]:
    """Format a project for JSON output."""
    return {
        "project_id": project["project_id"],
        "path": project["path"],
        "status": project["metadata"].get("status"),
        "owner": project["metadata"].get("owner"),
        "blocked": project["metadata"].get("blocked", False),
        "blocking_reason": project["metadata"].get("blocking_reason"),
        "priority": project["metadata"].get("priority", "medium"),
        "tags": project["metadata"].get("tags", []),
        "last_updated": project["metadata"].get("last_updated"),
        "dependencies": project["metadata"].get("dependencies", {}),
    }


def update_project_field(project_path: str, field: str, value: Any, base_path: str = None) -> bool:
    """
    Update a frontmatter field in a project's AGENCY.md file.

    Uses safe YAML loading to prevent deserialization attacks.

    Args:
        project_path: Path to the AGENCY.md file
        field: The frontmatter field to update
        value: The new value for the field
        base_path: Optional base path for validation

    Returns:
        True if successful, False otherwise
    """
    try:
        file_path = Path(project_path)

        # Validate path is within base_path if provided (prevent path traversal)
        if base_path:
            if not validate_path_within_base(file_path, Path(base_path)):
                return False

        if not file_path.exists():
            return False

        # Read the file using safe loading
        parsed = safe_load_agency_md(file_path)

        # Update the field
        parsed.metadata[field] = value

        # Update last_updated timestamp
        parsed.metadata["last_updated"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        # Write back using safe dump
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(safe_dump_agency_md(parsed.metadata, parsed.content))

        return True

    except Exception:  # pylint: disable=broad-except
        return False


def add_agent_note(project_path: str, agent: str, note: str, base_path: str = None) -> bool:
    """
    Add a timestamped note to the Agent Notes section of AGENCY.md.

    Uses safe YAML loading to prevent deserialization attacks.

    Args:
        project_path: Path to the AGENCY.md file
        agent: The agent name (e.g., "claude-3.5-sonnet")
        note: The note content
        base_path: Optional base path for validation

    Returns:
        True if successful, False otherwise
    """
    try:
        file_path = Path(project_path)

        # Validate path is within base_path if provided (prevent path traversal)
        if base_path:
            if not validate_path_within_base(file_path, Path(base_path)):
                return False

        if not file_path.exists():
            return False

        # Read the file using safe loading
        parsed = safe_load_agency_md(file_path)

        # Get current timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

        # Format the note (truncate to prevent abuse)
        truncated_note = note[:2000] if len(note) > 2000 else note
        new_note = f"- **{timestamp} - {agent}**: {truncated_note}"

        # Add to content
        content = parsed.content.strip()

        # Look for Agent Notes section
        if "## Agent Notes" in content:
            # Insert after the Agent Notes header
            parts = content.split("## Agent Notes")
            if len(parts) >= 2:
                # Split the second part to get existing notes
                after_header = parts[1].strip()
                # Add the new note
                updated_notes = f"{new_note}\n{after_header}" if after_header else new_note
                content = f"{parts[0].strip()}\n\n## Agent Notes\n{updated_notes}"
        else:
            # Add Agent Notes section at the end
            content = f"{content}\n\n## Agent Notes\n{new_note}"

        # Update last_updated
        parsed.metadata["last_updated"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        # Write back using safe dump
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(safe_dump_agency_md(parsed.metadata, content))

        return True

    except Exception:  # pylint: disable=broad-except
        return False


# Create the MCP server
app = Server("hive-mcp")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List the thin v2 MCP tool surface."""
    return [
        Tool(
            name="search",
            description="Search workspace state, API docs, schemas, examples, and project summaries",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"},
                    "scopes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional search scopes such as api, examples, project, workspace",
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
                        "description": "Python source code that defines `result = ...` or `main(hive)`",
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "description": "Maximum wall clock time for the subprocess",
                        "default": 20,
                    }
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

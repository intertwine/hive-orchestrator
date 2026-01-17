#!/usr/bin/env python3
"""
Hive MCP Server - Model Context Protocol integration for Agent Hive.

This server exposes Hive Orchestrator functionality as MCP tools
that can be used by AI agents like Claude.

Security Note: This server uses safe YAML loading to prevent deserialization
attacks from malicious AGENCY.md content.
"""

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

from cortex import Cortex  # pylint: disable=wrong-import-position
from coordinator_client import (  # pylint: disable=wrong-import-position
    CoordinatorUnavailable,
    get_coordinator_client,
)
from security import (  # pylint: disable=wrong-import-position
    safe_load_agency_md,
    safe_dump_agency_md,
    validate_path_within_base,
)
from yolo_loop import (  # pylint: disable=wrong-import-position
    YoloLoop,
    LoopConfig,
    ExecutionBackend,
    LoomWeaver,
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
    """List all available MCP tools."""
    return [
        Tool(
            name="list_projects",
            description="List all projects in the hive with their metadata",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_ready_work",
            description="Get projects that are ready for an agent to claim "
            "(active, not blocked, no owner, dependencies met)",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_project",
            description="Get full details of a specific project by project_id",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "The project ID to retrieve"}
                },
                "required": ["project_id"],
            },
        ),
        Tool(
            name="claim_project",
            description="Claim a project by setting the owner field to the agent name",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "The project ID to claim"},
                    "agent_name": {
                        "type": "string",
                        "description": "The agent name (e.g., 'claude-3.5-sonnet')",
                    },
                },
                "required": ["project_id", "agent_name"],
            },
        ),
        Tool(
            name="release_project",
            description="Release a project by setting the owner field to null",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "The project ID to release"}
                },
                "required": ["project_id"],
            },
        ),
        Tool(
            name="update_status",
            description="Update the status of a project " "(active, pending, blocked, completed)",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "The project ID to update"},
                    "status": {
                        "type": "string",
                        "description": "New status (active, pending, blocked, completed)",
                        "enum": ["active", "pending", "blocked", "completed"],
                    },
                },
                "required": ["project_id", "status"],
            },
        ),
        Tool(
            name="add_note",
            description="Add a timestamped note to a project's Agent Notes section",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "The project ID to add a note to",
                    },
                    "agent": {
                        "type": "string",
                        "description": "The agent name (e.g., 'claude-3.5-sonnet')",
                    },
                    "note": {"type": "string", "description": "The note content"},
                },
                "required": ["project_id", "agent", "note"],
            },
        ),
        Tool(
            name="get_dependencies",
            description="Get dependency information for a specific project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "The project ID to get dependencies for",
                    }
                },
                "required": ["project_id"],
            },
        ),
        Tool(
            name="get_dependency_graph",
            description="Get the full dependency graph for all projects",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="coordinator_status",
            description="Check if the coordination server is available and get its status",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="coordinator_claim",
            description="Claim a project via the coordination server for conflict prevention",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "The project ID to claim"},
                    "agent_name": {
                        "type": "string",
                        "description": "The agent name claiming the project",
                    },
                    "ttl_seconds": {
                        "type": "integer",
                        "description": "Time-to-live for the claim in seconds (default: 3600)",
                        "default": 3600,
                    },
                },
                "required": ["project_id", "agent_name"],
            },
        ),
        Tool(
            name="coordinator_release",
            description="Release a project claim via the coordination server",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "The project ID to release"}
                },
                "required": ["project_id"],
            },
        ),
        Tool(
            name="coordinator_reservations",
            description="Get all active reservations from the coordination server",
            inputSchema={"type": "object", "properties": {}},
        ),
        # YOLO Loop tools
        Tool(
            name="yolo_start",
            description="Start a YOLO loop (Ralph Wiggum style autonomous agent loop) "
            "with a prompt. The loop runs iterations until completion or limits.",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The task prompt for the agent to work on",
                    },
                    "max_iterations": {
                        "type": "integer",
                        "description": "Maximum iterations (default: 50)",
                        "default": 50,
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "description": "Timeout in seconds (default: 3600)",
                        "default": 3600,
                    },
                    "backend": {
                        "type": "string",
                        "description": "Execution backend: subprocess or docker",
                        "enum": ["subprocess", "docker"],
                        "default": "subprocess",
                    },
                },
                "required": ["prompt"],
            },
        ),
        Tool(
            name="yolo_project",
            description="Start a YOLO loop on a specific project by project_id",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "The project ID to run the loop on",
                    },
                    "max_iterations": {
                        "type": "integer",
                        "description": "Maximum iterations (default: 50)",
                        "default": 50,
                    },
                },
                "required": ["project_id"],
            },
        ),
        Tool(
            name="yolo_hive",
            description="Start Loom-style parallel YOLO loops on all ready Hive projects",
            inputSchema={
                "type": "object",
                "properties": {
                    "max_parallel": {
                        "type": "integer",
                        "description": "Max parallel agents (default: 3)",
                        "default": 3,
                    },
                    "max_iterations_per_loop": {
                        "type": "integer",
                        "description": "Max iterations per loop (default: 50)",
                        "default": 50,
                    },
                },
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """
    Handle tool calls.

    This is a dispatcher function that routes to different tool handlers,
    so complexity is expected and acceptable.
    """
    # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    base_path = get_base_path()
    cortex = Cortex(base_path=base_path)

    try:
        if name == "list_projects":
            projects = cortex.discover_projects()
            result = format_response(
                success=True,
                data={"count": len(projects), "projects": [format_project(p) for p in projects]},
            )

        elif name == "get_ready_work":
            projects = cortex.discover_projects()
            ready = cortex.ready_work(projects)
            result = format_response(
                success=True,
                data={"count": len(ready), "projects": [format_project(p) for p in ready]},
            )

        elif name == "get_project":
            project_id = arguments.get("project_id")
            if not project_id:
                result = format_response(success=False, error="project_id is required")
            else:
                projects = cortex.discover_projects()
                project = next((p for p in projects if p["project_id"] == project_id), None)
                if project:
                    # Include full content in get_project
                    project_data = format_project(project)
                    project_data["content"] = project["content"]
                    result = format_response(success=True, data=project_data)
                else:
                    result = format_response(
                        success=False, error=f"Project '{project_id}' not found"
                    )

        elif name == "claim_project":
            project_id = arguments.get("project_id")
            agent_name = arguments.get("agent_name")

            if not project_id or not agent_name:
                result = format_response(
                    success=False, error="project_id and agent_name are required"
                )
            else:
                projects = cortex.discover_projects()
                project = next((p for p in projects if p["project_id"] == project_id), None)

                if not project:
                    result = format_response(
                        success=False, error=f"Project '{project_id}' not found"
                    )
                elif project["metadata"].get("owner") is not None:
                    result = format_response(
                        success=False,
                        error=f"Project already claimed by {project['metadata']['owner']}",
                    )
                else:
                    success = update_project_field(project["path"], "owner", agent_name, base_path)
                    if success:
                        result = format_response(
                            success=True, data={"project_id": project_id, "owner": agent_name}
                        )
                    else:
                        result = format_response(success=False, error="Failed to update project")

        elif name == "release_project":
            project_id = arguments.get("project_id")

            if not project_id:
                result = format_response(success=False, error="project_id is required")
            else:
                projects = cortex.discover_projects()
                project = next((p for p in projects if p["project_id"] == project_id), None)

                if not project:
                    result = format_response(
                        success=False, error=f"Project '{project_id}' not found"
                    )
                else:
                    success = update_project_field(project["path"], "owner", None, base_path)
                    if success:
                        result = format_response(
                            success=True, data={"project_id": project_id, "owner": None}
                        )
                    else:
                        result = format_response(success=False, error="Failed to update project")

        elif name == "update_status":
            project_id = arguments.get("project_id")
            status = arguments.get("status")

            if not project_id or not status:
                result = format_response(success=False, error="project_id and status are required")
            elif status not in ["active", "pending", "blocked", "completed"]:
                result = format_response(
                    success=False,
                    error="status must be one of: active, pending, blocked, completed",
                )
            else:
                projects = cortex.discover_projects()
                project = next((p for p in projects if p["project_id"] == project_id), None)

                if not project:
                    result = format_response(
                        success=False, error=f"Project '{project_id}' not found"
                    )
                else:
                    success = update_project_field(project["path"], "status", status, base_path)
                    if success:
                        result = format_response(
                            success=True, data={"project_id": project_id, "status": status}
                        )
                    else:
                        result = format_response(success=False, error="Failed to update project")

        elif name == "add_note":
            project_id = arguments.get("project_id")
            agent = arguments.get("agent")
            note = arguments.get("note")

            if not project_id or not agent or not note:
                result = format_response(
                    success=False, error="project_id, agent, and note are required"
                )
            else:
                projects = cortex.discover_projects()
                project = next((p for p in projects if p["project_id"] == project_id), None)

                if not project:
                    result = format_response(
                        success=False, error=f"Project '{project_id}' not found"
                    )
                else:
                    success = add_agent_note(project["path"], agent, note, base_path)
                    if success:
                        result = format_response(
                            success=True, data={"project_id": project_id, "note_added": True}
                        )
                    else:
                        result = format_response(success=False, error="Failed to add note")

        elif name == "get_dependencies":
            project_id = arguments.get("project_id")

            if not project_id:
                result = format_response(success=False, error="project_id is required")
            else:
                projects = cortex.discover_projects()
                project = next((p for p in projects if p["project_id"] == project_id), None)

                if not project:
                    result = format_response(
                        success=False, error=f"Project '{project_id}' not found"
                    )
                else:
                    blocking_info = cortex.is_blocked(project_id, projects)
                    result = format_response(success=True, data=blocking_info)

        elif name == "get_dependency_graph":
            projects = cortex.discover_projects()
            summary = cortex.get_dependency_summary(projects)
            result = format_response(success=True, data=summary)

        elif name == "coordinator_status":
            coordinator = get_coordinator_client()
            if not coordinator:
                result = format_response(
                    success=True,
                    data={"available": False, "reason": "COORDINATOR_URL not configured"},
                )
            else:
                try:
                    if coordinator.is_available():
                        reservations = coordinator.get_all_reservations()
                        result = format_response(
                            success=True,
                            data={
                                "available": True,
                                "url": coordinator.base_url,
                                "active_claims": reservations.get("count", 0),
                            },
                        )
                    else:
                        result = format_response(
                            success=True,
                            data={
                                "available": False,
                                "url": coordinator.base_url,
                                "reason": "Server not responding",
                            },
                        )
                except CoordinatorUnavailable as e:
                    result = format_response(
                        success=True,
                        data={"available": False, "url": coordinator.base_url, "reason": str(e)},
                    )

        elif name == "coordinator_claim":
            project_id = arguments.get("project_id")
            agent_name = arguments.get("agent_name")
            ttl_seconds = arguments.get("ttl_seconds", 3600)

            if not project_id or not agent_name:
                result = format_response(
                    success=False, error="project_id and agent_name are required"
                )
            else:
                coordinator = get_coordinator_client()
                if not coordinator:
                    result = format_response(
                        success=False, error="Coordinator not configured (COORDINATOR_URL not set)"
                    )
                else:
                    try:
                        claim_result = coordinator.try_claim(
                            project_id=project_id, agent_name=agent_name, ttl_seconds=ttl_seconds
                        )
                        if claim_result.success:
                            result = format_response(
                                success=True,
                                data={
                                    "claim_id": claim_result.claim_id,
                                    "project_id": claim_result.project_id,
                                    "agent_name": claim_result.agent_name,
                                    "expires_at": claim_result.expires_at,
                                },
                            )
                        else:
                            result = format_response(
                                success=False,
                                error=claim_result.error,
                                data={"current_owner": claim_result.current_owner},
                            )
                    except CoordinatorUnavailable as e:
                        result = format_response(
                            success=False, error=f"Coordinator unavailable: {e}"
                        )

        elif name == "coordinator_release":
            project_id = arguments.get("project_id")

            if not project_id:
                result = format_response(success=False, error="project_id is required")
            else:
                coordinator = get_coordinator_client()
                if not coordinator:
                    result = format_response(
                        success=False, error="Coordinator not configured (COORDINATOR_URL not set)"
                    )
                else:
                    try:
                        released = coordinator.release(project_id)
                        result = format_response(
                            success=True, data={"project_id": project_id, "released": released}
                        )
                    except CoordinatorUnavailable as e:
                        result = format_response(
                            success=False, error=f"Coordinator unavailable: {e}"
                        )

        elif name == "coordinator_reservations":
            coordinator = get_coordinator_client()
            if not coordinator:
                result = format_response(
                    success=False, error="Coordinator not configured (COORDINATOR_URL not set)"
                )
            else:
                try:
                    reservations = coordinator.get_all_reservations()
                    result = format_response(success=True, data=reservations)
                except CoordinatorUnavailable as e:
                    result = format_response(success=False, error=f"Coordinator unavailable: {e}")

        elif name == "yolo_start":
            prompt = arguments.get("prompt")
            max_iterations = arguments.get("max_iterations", 50)
            timeout_seconds = arguments.get("timeout_seconds", 3600)
            backend_str = arguments.get("backend", "subprocess")

            if not prompt:
                result = format_response(success=False, error="prompt is required")
            else:
                try:
                    backend = ExecutionBackend(backend_str)
                    config = LoopConfig(
                        prompt=prompt,
                        max_iterations=max_iterations,
                        timeout_seconds=timeout_seconds,
                        backend=backend,
                        working_dir=base_path,
                    )
                    loop = YoloLoop(config)
                    state = loop.run()
                    result = format_response(
                        success=True,
                        data={
                            "loop_id": state.loop_id,
                            "status": state.status.value,
                            "iterations": state.current_iteration,
                            "elapsed_seconds": (
                                (state.end_time or 0) - (state.start_time or 0)
                            ),
                        },
                    )
                except Exception as e:  # pylint: disable=broad-except
                    result = format_response(success=False, error=f"YOLO loop error: {e}")

        elif name == "yolo_project":
            project_id = arguments.get("project_id")
            max_iterations = arguments.get("max_iterations", 50)

            if not project_id:
                result = format_response(success=False, error="project_id is required")
            else:
                projects = cortex.discover_projects()
                project = next((p for p in projects if p["project_id"] == project_id), None)

                if not project:
                    result = format_response(
                        success=False, error=f"Project '{project_id}' not found"
                    )
                else:
                    try:
                        weaver = LoomWeaver(base_path=base_path, max_parallel_agents=1)
                        loop = weaver.create_loop_for_project(project, max_iterations)
                        weaver.claim_project(project, loop.loop_id)
                        state = loop.run()
                        weaver.release_project(project, loop.loop_id, state.status)
                        result = format_response(
                            success=True,
                            data={
                                "loop_id": state.loop_id,
                                "project_id": project_id,
                                "status": state.status.value,
                                "iterations": state.current_iteration,
                            },
                        )
                    except Exception as e:  # pylint: disable=broad-except
                        result = format_response(success=False, error=f"YOLO project error: {e}")

        elif name == "yolo_hive":
            max_parallel = arguments.get("max_parallel", 3)
            max_iterations_per_loop = arguments.get("max_iterations_per_loop", 50)

            try:
                weaver = LoomWeaver(base_path=base_path, max_parallel_agents=max_parallel)
                results = weaver.weave(max_iterations_per_loop=max_iterations_per_loop)
                loop_summaries = {
                    loop_id: {
                        "status": state.status.value,
                        "iterations": state.current_iteration,
                    }
                    for loop_id, state in results.items()
                }
                result = format_response(
                    success=True,
                    data={
                        "total_loops": len(results),
                        "loops": loop_summaries,
                    },
                )
            except Exception as e:  # pylint: disable=broad-except
                result = format_response(success=False, error=f"YOLO hive error: {e}")

        else:
            result = format_response(success=False, error=f"Unknown tool: {name}")

    except Exception as e:  # pylint: disable=broad-except
        result = format_response(success=False, error=str(e))

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def main():
    """Main entry point for the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

"""Tests for the thin Hive MCP server."""

import json
import os
from pathlib import Path

from src.hive_mcp.server import (
    call_tool,
    format_response,
    get_base_path,
    list_tools,
)


class TestFormatResponse:
    """Response formatting should stay stable."""

    def test_success_response(self):
        """Successful responses should keep the data payload."""
        result = format_response(success=True, data={"test": "value"})
        assert result["success"] is True
        assert result["data"] == {"test": "value"}
        assert result["error"] is None

    def test_error_response(self):
        """Error responses should keep the error message."""
        result = format_response(success=False, error="Test error")
        assert result["success"] is False
        assert result["data"] is None
        assert result["error"] == "Test error"


class TestGetBasePath:
    """Base path detection should honor the environment variable override."""

    def test_get_base_path_from_env(self, monkeypatch):
        """The env var should override the current directory."""
        monkeypatch.setenv("HIVE_BASE_PATH", "/test/path")
        assert get_base_path() == "/test/path"

    def test_get_base_path_default(self, monkeypatch):
        """Without an env override, use the current directory."""
        monkeypatch.delenv("HIVE_BASE_PATH", raising=False)
        assert get_base_path() == os.getcwd()


class TestHiveV2MCP:
    """The live MCP surface should stay limited to search and execute."""

    async def test_list_tools_exposes_only_search_and_execute(self):
        """Only the thin v2 tools should be exposed."""
        tools = await list_tools()
        assert [tool.name for tool in tools] == ["search", "execute"]

    async def test_search_tool_returns_workspace_results(
        self,
        temp_hive_dir,
        temp_project,
        monkeypatch,
    ):
        """Search should return project/workspace results through the MCP wrapper."""
        assert temp_project
        monkeypatch.setenv("HIVE_BASE_PATH", temp_hive_dir)

        response = await call_tool("search", {"query": "Task 1", "scopes": ["project"]})
        payload = json.loads(response[0].text)

        assert payload["success"] is True
        assert payload["data"]["count"] >= 1
        assert payload["data"]["results"][0]["kind"] == "project"

    async def test_execute_tool_runs_python_client_code(
        self,
        temp_hive_dir,
        temp_project,
        monkeypatch,
    ):
        """Execute should expose the typed local Hive client."""
        assert temp_project
        monkeypatch.setenv("HIVE_BASE_PATH", temp_hive_dir)

        response = await call_tool(
            "execute",
            {
                "language": "python",
                "code": (
                    "result = {'workspace': str(hive.root), "
                    "'project_count': len(hive.project.list())}"
                ),
            },
        )
        payload = json.loads(response[0].text)

        assert payload["success"] is True
        assert payload["data"]["value"]["workspace"] == str(Path(temp_hive_dir).resolve())
        assert payload["data"]["value"]["project_count"] >= 1

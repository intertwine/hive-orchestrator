"""Tests for Hive MCP Server."""

import frontmatter
from pathlib import Path
from src.hive_mcp.server import (
    format_response,
    format_project,
    update_project_field,
    add_agent_note,
    get_base_path,
)
from src.cortex import Cortex


class TestFormatResponse:
    """Test response formatting."""

    def test_success_response(self):
        """Test formatting a successful response."""
        result = format_response(success=True, data={"test": "value"})
        assert result["success"] is True
        assert result["data"] == {"test": "value"}
        assert result["error"] is None

    def test_error_response(self):
        """Test formatting an error response."""
        result = format_response(success=False, error="Test error")
        assert result["success"] is False
        assert result["data"] is None
        assert result["error"] == "Test error"


class TestFormatProject:
    """Test project formatting."""

    def test_format_project(self, temp_hive_dir, temp_project):
        """Test formatting a project for output."""
        cortex = Cortex(temp_hive_dir)
        projects = cortex.discover_projects()
        assert len(projects) == 1

        formatted = format_project(projects[0])
        assert formatted["project_id"] == "test-project"
        assert formatted["status"] == "active"
        assert formatted["owner"] is None
        assert formatted["blocked"] is False
        assert formatted["priority"] == "high"
        assert "test" in formatted["tags"]
        assert "path" in formatted

    def test_format_project_with_dependencies(self, temp_hive_dir, temp_project_with_dependency):
        """Test formatting a project with dependencies."""
        cortex = Cortex(temp_hive_dir)
        projects = cortex.discover_projects()
        project = next(p for p in projects if p["project_id"] == "dependent-project")

        formatted = format_project(project)
        assert "dependencies" in formatted
        assert "blocked_by" in formatted["dependencies"]
        assert "prereq-project" in formatted["dependencies"]["blocked_by"]


class TestUpdateProjectField:
    """Test updating project fields."""

    def test_update_project_field(self, temp_hive_dir, temp_project):
        """Test updating a project field."""
        success = update_project_field(temp_project, "status", "completed", temp_hive_dir)
        assert success is True

        # Verify the update
        with open(temp_project, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)
        assert post.metadata["status"] == "completed"
        assert "last_updated" in post.metadata

    def test_update_owner_field(self, temp_hive_dir, temp_project):
        """Test updating the owner field."""
        success = update_project_field(temp_project, "owner", "claude-3.5-sonnet", temp_hive_dir)
        assert success is True

        # Verify the update
        with open(temp_project, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)
        assert post.metadata["owner"] == "claude-3.5-sonnet"

    def test_update_nonexistent_file(self, temp_hive_dir):
        """Test updating a file that doesn't exist."""
        success = update_project_field(
            str(Path(temp_hive_dir) / "nonexistent.md"), "status", "active", temp_hive_dir
        )
        assert success is False

    def test_update_outside_base_path(self, temp_hive_dir, temp_project):
        """Test that updates outside base path are rejected."""
        # Try to update with a different base path
        success = update_project_field(temp_project, "status", "completed", "/some/other/path")
        assert success is False


class TestAddAgentNote:
    """Test adding agent notes."""

    def test_add_note_to_existing_section(self, temp_hive_dir, temp_project):
        """Test adding a note when Agent Notes section exists."""
        success = add_agent_note(
            temp_project, "claude-3.5-sonnet", "Test note from Claude", temp_hive_dir
        )
        assert success is True

        # Verify the note was added
        with open(temp_project, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)

        assert "claude-3.5-sonnet" in post.content
        assert "Test note from Claude" in post.content
        assert "## Agent Notes" in post.content

    def test_add_note_creates_section(self, temp_hive_dir):
        """Test adding a note when Agent Notes section doesn't exist."""
        # Create a project without Agent Notes section
        project_dir = Path(temp_hive_dir) / "projects" / "no-notes-project"
        project_dir.mkdir(parents=True)

        agency_content = frontmatter.Post(
            """# Project Without Notes

## Objective
Testing note addition.
""",
            project_id="no-notes-project",
            status="active",
            owner=None,
            priority="medium",
            tags=[],
        )

        agency_file = project_dir / "AGENCY.md"
        with open(agency_file, "w", encoding="utf-8") as f:
            f.write(frontmatter.dumps(agency_content))

        # Add a note
        success = add_agent_note(str(agency_file), "grok", "Creating notes section", temp_hive_dir)
        assert success is True

        # Verify the section was created
        with open(agency_file, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)

        assert "## Agent Notes" in post.content
        assert "grok" in post.content
        assert "Creating notes section" in post.content

    def test_add_multiple_notes(self, temp_hive_dir, temp_project):
        """Test adding multiple notes."""
        add_agent_note(temp_project, "claude", "First note", temp_hive_dir)
        add_agent_note(temp_project, "grok", "Second note", temp_hive_dir)

        with open(temp_project, "r", encoding="utf-8") as f:
            content = f.read()

        assert "claude" in content
        assert "First note" in content
        assert "grok" in content
        assert "Second note" in content

    def test_add_note_to_nonexistent_file(self, temp_hive_dir):
        """Test adding a note to a file that doesn't exist."""
        success = add_agent_note(
            str(Path(temp_hive_dir) / "nonexistent.md"), "claude", "Test note", temp_hive_dir
        )
        assert success is False


class TestGetBasePath:
    """Test base path detection."""

    def test_get_base_path_from_env(self, monkeypatch):
        """Test getting base path from environment variable."""
        monkeypatch.setenv("HIVE_BASE_PATH", "/test/path")
        assert get_base_path() == "/test/path"

    def test_get_base_path_default(self, monkeypatch):
        """Test getting default base path."""
        monkeypatch.delenv("HIVE_BASE_PATH", raising=False)
        import os

        assert get_base_path() == os.getcwd()


class TestMCPToolIntegration:
    """Integration tests for MCP tool functionality."""

    def test_list_projects_workflow(self, temp_hive_dir, temp_project):
        """Test the list_projects workflow."""
        cortex = Cortex(temp_hive_dir)
        projects = cortex.discover_projects()

        result = format_response(
            success=True,
            data={"count": len(projects), "projects": [format_project(p) for p in projects]},
        )

        assert result["success"] is True
        assert result["data"]["count"] == 1
        assert result["data"]["projects"][0]["project_id"] == "test-project"

    def test_get_ready_work_workflow(self, temp_hive_dir, temp_project, temp_blocked_project):
        """Test the get_ready_work workflow."""
        cortex = Cortex(temp_hive_dir)
        projects = cortex.discover_projects()
        ready = cortex.ready_work(projects)

        # Only test-project should be ready (blocked-project is blocked)
        result = format_response(
            success=True, data={"count": len(ready), "projects": [format_project(p) for p in ready]}
        )

        assert result["success"] is True
        assert result["data"]["count"] == 1
        assert result["data"]["projects"][0]["project_id"] == "test-project"

    def test_claim_and_release_workflow(self, temp_hive_dir, temp_project):
        """Test claiming and releasing a project."""
        # Claim the project
        success = update_project_field(temp_project, "owner", "claude-3.5-sonnet", temp_hive_dir)
        assert success is True

        # Verify it's claimed
        with open(temp_project, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)
        assert post.metadata["owner"] == "claude-3.5-sonnet"

        # Release the project
        success = update_project_field(temp_project, "owner", None, temp_hive_dir)
        assert success is True

        # Verify it's released
        with open(temp_project, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)
        assert post.metadata["owner"] is None

    def test_update_status_workflow(self, temp_hive_dir, temp_project):
        """Test updating project status."""
        # Update to completed
        success = update_project_field(temp_project, "status", "completed", temp_hive_dir)
        assert success is True

        # Verify the status
        with open(temp_project, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)
        assert post.metadata["status"] == "completed"

    def test_get_dependencies_workflow(
        self, temp_hive_dir, temp_project_with_dependency, temp_prereq_project_incomplete
    ):
        """Test getting dependency information."""
        cortex = Cortex(temp_hive_dir)
        projects = cortex.discover_projects()

        blocking_info = cortex.is_blocked("dependent-project", projects)

        result = format_response(success=True, data=blocking_info)

        assert result["success"] is True
        assert result["data"]["is_blocked"] is True
        assert "prereq-project" in result["data"]["blocking_projects"]

    def test_get_dependencies_nonexistent_project(self, temp_hive_dir, temp_project):
        """Test get_dependencies with a nonexistent project returns error."""
        cortex = Cortex(temp_hive_dir)
        projects = cortex.discover_projects()

        # Check if the project exists (simulating the fixed MCP handler logic)
        project_id = "nonexistent-project"
        project = next((p for p in projects if p["project_id"] == project_id), None)

        if not project:
            result = format_response(success=False, error=f"Project '{project_id}' not found")
        else:
            blocking_info = cortex.is_blocked(project_id, projects)
            result = format_response(success=True, data=blocking_info)

        # Verify the result is an error response
        assert result["success"] is False
        assert result["error"] == "Project 'nonexistent-project' not found"
        assert result["data"] is None

    def test_get_dependency_graph_workflow(
        self, temp_hive_dir, temp_project, temp_project_with_dependency, temp_prereq_project
    ):
        """Test getting the full dependency graph."""
        cortex = Cortex(temp_hive_dir)
        projects = cortex.discover_projects()
        summary = cortex.get_dependency_summary(projects)

        result = format_response(success=True, data=summary)

        assert result["success"] is True
        assert result["data"]["total_projects"] == 3
        assert len(result["data"]["projects"]) == 3

        # Find the dependent project in the summary
        dep_project = next(
            p for p in result["data"]["projects"] if p["project_id"] == "dependent-project"
        )
        assert "prereq-project" in dep_project["blocked_by"]

    def test_full_agent_workflow(self, temp_hive_dir, temp_project):
        """Test a complete agent workflow: claim, work, note, release."""
        agent_name = "claude-3.5-sonnet"

        # 1. Claim the project
        update_project_field(temp_project, "owner", agent_name, temp_hive_dir)

        # 2. Add a progress note
        add_agent_note(temp_project, agent_name, "Started working on tasks", temp_hive_dir)

        # 3. Update status
        update_project_field(temp_project, "status", "completed", temp_hive_dir)

        # 4. Add completion note
        add_agent_note(temp_project, agent_name, "Completed all tasks", temp_hive_dir)

        # 5. Release the project
        update_project_field(temp_project, "owner", None, temp_hive_dir)

        # Verify final state
        with open(temp_project, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)

        assert post.metadata["status"] == "completed"
        assert post.metadata["owner"] is None
        assert "Started working on tasks" in post.content
        assert "Completed all tasks" in post.content
        assert agent_name in post.content

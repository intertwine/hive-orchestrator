"""Tests for the Cortex orchestration engine."""

# pylint: disable=unused-argument,import-error,wrong-import-position

import sys
import os
import json
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
import frontmatter

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cortex import Cortex


class TestCortexInitialization:
    """Test Cortex initialization."""

    def test_init_with_default_path(self):
        """Test initialization with default path."""
        cortex = Cortex()
        assert cortex.base_path == Path(os.getcwd())
        assert cortex.global_file == Path(os.getcwd()) / "GLOBAL.md"
        assert cortex.projects_dir == Path(os.getcwd()) / "projects"

    def test_init_with_custom_path(self, temp_hive_dir):
        """Test initialization with custom path."""
        cortex = Cortex(temp_hive_dir)
        assert cortex.base_path == Path(temp_hive_dir)
        assert cortex.global_file == Path(temp_hive_dir) / "GLOBAL.md"
        assert cortex.projects_dir == Path(temp_hive_dir) / "projects"

    def test_init_sets_api_configuration(self, mock_env_vars):
        """Test that API configuration is set from environment."""
        cortex = Cortex()
        assert cortex.api_key == "test-api-key-12345"
        assert cortex.model == "anthropic/claude-haiku-4.5"
        assert cortex.api_url == "https://openrouter.ai/api/v1/chat/completions"


class TestEnvironmentValidation:
    """Test environment validation."""

    def test_validate_environment_with_api_key(self, mock_env_vars, temp_hive_dir):
        """Test validation succeeds when API key is set."""
        cortex = Cortex(temp_hive_dir)
        assert cortex.validate_environment() is True

    def test_validate_environment_without_api_key(self, temp_hive_dir, monkeypatch):
        """Test validation fails when API key is missing."""
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        cortex = Cortex(temp_hive_dir)
        assert cortex.validate_environment() is False


class TestReadGlobalContext:
    """Test reading GLOBAL.md file."""

    def test_read_global_context_success(self, temp_hive_dir):
        """Test successfully reading GLOBAL.md."""
        cortex = Cortex(temp_hive_dir)
        global_ctx = cortex.read_global_context()

        assert global_ctx is not None
        assert "metadata" in global_ctx
        assert "content" in global_ctx
        assert "path" in global_ctx
        assert global_ctx["metadata"]["status"] == "active"
        assert global_ctx["metadata"]["version"] == "1.0.0"

    def test_read_global_context_missing_file(self, temp_hive_dir):
        """Test reading GLOBAL.md when file doesn't exist."""
        # Remove GLOBAL.md
        global_file = Path(temp_hive_dir) / "GLOBAL.md"
        global_file.unlink()

        cortex = Cortex(temp_hive_dir)
        global_ctx = cortex.read_global_context()

        assert global_ctx is None

    def test_read_global_context_malformed_file(self, temp_hive_dir):
        """Test reading malformed GLOBAL.md."""
        # Create a malformed file
        global_file = Path(temp_hive_dir) / "GLOBAL.md"
        global_file.write_text("---\ninvalid: yaml: content:\n---")

        cortex = Cortex(temp_hive_dir)
        global_ctx = cortex.read_global_context()

        assert global_ctx is None


class TestDiscoverProjects:
    """Test project discovery."""

    def test_discover_single_project(self, temp_hive_dir, temp_project):
        """Test discovering a single project."""
        cortex = Cortex(temp_hive_dir)
        projects = cortex.discover_projects()

        assert len(projects) == 1
        assert projects[0]["project_id"] == "test-project"
        assert projects[0]["metadata"]["status"] == "active"
        assert projects[0]["metadata"]["priority"] == "high"

    def test_discover_multiple_projects(self, temp_hive_dir, temp_project, temp_blocked_project):
        """Test discovering multiple projects."""
        cortex = Cortex(temp_hive_dir)
        projects = cortex.discover_projects()

        assert len(projects) == 2
        project_ids = [p["project_id"] for p in projects]
        assert "test-project" in project_ids
        assert "blocked-project" in project_ids

    def test_discover_no_projects_dir(self, temp_hive_dir):
        """Test discovering projects when directory doesn't exist."""
        # Remove projects directory
        projects_dir = Path(temp_hive_dir) / "projects"
        shutil.rmtree(projects_dir)

        cortex = Cortex(temp_hive_dir)
        projects = cortex.discover_projects()

        assert len(projects) == 0

    def test_discover_projects_with_malformed_agency(self, temp_hive_dir):
        """Test discovering projects with a malformed AGENCY.md file."""
        # Create a project with malformed AGENCY.md
        project_dir = Path(temp_hive_dir) / "projects" / "malformed-project"
        project_dir.mkdir(parents=True)
        agency_file = project_dir / "AGENCY.md"
        agency_file.write_text("---\ninvalid: yaml: content:\n---")

        cortex = Cortex(temp_hive_dir)
        projects = cortex.discover_projects()

        # Should skip malformed project
        assert len(projects) == 0

    def test_discover_nested_projects(self, temp_hive_dir):
        """Test discovering projects in nested directories (e.g., projects/external/foo)."""
        # Create a nested project at projects/external/nested-project/AGENCY.md
        nested_dir = Path(temp_hive_dir) / "projects" / "external" / "nested-project"
        nested_dir.mkdir(parents=True)
        nested_agency = nested_dir / "AGENCY.md"
        nested_agency.write_text("""---
project_id: nested-project
status: active
owner: null
priority: high
target_repo:
  url: https://github.com/example/repo
  branch: main
---

# Nested External Project

A project in a nested directory for cross-repo work.
""")

        # Also create a regular project
        regular_dir = Path(temp_hive_dir) / "projects" / "regular-project"
        regular_dir.mkdir(parents=True)
        regular_agency = regular_dir / "AGENCY.md"
        regular_agency.write_text("""---
project_id: regular-project
status: active
owner: null
priority: medium
---

# Regular Project
""")

        cortex = Cortex(temp_hive_dir)
        projects = cortex.discover_projects()

        # Should find both projects
        assert len(projects) == 2
        project_ids = [p["project_id"] for p in projects]
        assert "nested-project" in project_ids
        assert "regular-project" in project_ids


class TestBuildAnalysisPrompt:
    """Test building analysis prompts for LLM."""

    def test_build_analysis_prompt_structure(self, temp_hive_dir, temp_project):
        """Test that the analysis prompt has the correct secure structure."""
        cortex = Cortex(temp_hive_dir)
        global_ctx = cortex.read_global_context()
        projects = cortex.discover_projects()

        prompt = cortex.build_analysis_prompt(global_ctx, projects)

        # Check for secure prompt structure
        assert "<system_instructions>" in prompt
        assert "</system_instructions>" in prompt
        assert "<untrusted_content>" in prompt
        assert "</untrusted_content>" in prompt
        assert "SECURITY NOTICE" in prompt

        # Check for content
        assert "GLOBAL CONTEXT" in prompt
        assert "test-project" in prompt
        assert "blocked_tasks" in prompt
        assert "state_updates" in prompt
        assert "new_projects" in prompt

    def test_build_analysis_prompt_includes_project_metadata(self, temp_hive_dir, temp_project):
        """Test that prompt includes project metadata."""
        cortex = Cortex(temp_hive_dir)
        global_ctx = cortex.read_global_context()
        projects = cortex.discover_projects()

        prompt = cortex.build_analysis_prompt(global_ctx, projects)

        assert "active" in prompt
        assert "high" in prompt
        assert "test-project" in prompt

    def test_build_analysis_prompt_with_multiple_projects(
        self, temp_hive_dir, temp_project, temp_blocked_project
    ):
        """Test prompt building with multiple projects."""
        cortex = Cortex(temp_hive_dir)
        global_ctx = cortex.read_global_context()
        projects = cortex.discover_projects()

        prompt = cortex.build_analysis_prompt(global_ctx, projects)

        assert "Project 1:" in prompt
        assert "Project 2:" in prompt
        assert "test-project" in prompt
        assert "blocked-project" in prompt


class TestCallLLM:
    """Test LLM API calls."""

    def test_call_llm_success(self, temp_hive_dir, mock_env_vars, sample_api_response, monkeypatch):
        """Test successful LLM call."""
        # Disable weave tracing for tests
        monkeypatch.setenv("WEAVE_DISABLED", "true")
        cortex = Cortex(temp_hive_dir)

        with patch("tracing.requests.post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = sample_api_response
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            result = cortex.call_llm("Test prompt")

            assert result is not None
            assert "summary" in result
            assert "blocked_tasks" in result
            assert result["summary"] == "System is running well with 2 active projects"

    def test_call_llm_without_api_key(self, temp_hive_dir, monkeypatch):
        """Test LLM call without API key."""
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        cortex = Cortex(temp_hive_dir)

        result = cortex.call_llm("Test prompt")
        assert result is None

    def test_call_llm_with_markdown_wrapped_json(
        self, temp_hive_dir, mock_env_vars, sample_llm_response, monkeypatch
    ):
        """Test LLM call with JSON wrapped in markdown code blocks."""
        monkeypatch.setenv("WEAVE_DISABLED", "true")
        cortex = Cortex(temp_hive_dir)

        markdown_response = {
            "choices": [
                {"message": {"content": f"```json\n{json.dumps(sample_llm_response)}\n```"}}
            ]
        }

        with patch("tracing.requests.post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = markdown_response
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            result = cortex.call_llm("Test prompt")

            assert result is not None
            assert result["summary"] == "System is running well with 2 active projects"

    def test_call_llm_network_error(self, temp_hive_dir, mock_env_vars, monkeypatch):
        """Test LLM call with network error."""
        monkeypatch.setenv("WEAVE_DISABLED", "true")
        cortex = Cortex(temp_hive_dir)

        with patch("tracing.requests.post") as mock_post:
            mock_post.side_effect = Exception("Network error")

            result = cortex.call_llm("Test prompt")
            assert result is None

    def test_call_llm_invalid_json_response(self, temp_hive_dir, mock_env_vars, monkeypatch):
        """Test LLM call with invalid JSON response."""
        monkeypatch.setenv("WEAVE_DISABLED", "true")
        cortex = Cortex(temp_hive_dir)

        invalid_response = {"choices": [{"message": {"content": "This is not valid JSON"}}]}

        with patch("tracing.requests.post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = invalid_response
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            result = cortex.call_llm("Test prompt")
            assert result is None

    def test_call_llm_missing_choices(self, temp_hive_dir, mock_env_vars, monkeypatch):
        """Test LLM call with missing choices in response."""
        monkeypatch.setenv("WEAVE_DISABLED", "true")
        cortex = Cortex(temp_hive_dir)

        invalid_response = {"error": "No choices"}

        with patch("tracing.requests.post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = invalid_response
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            result = cortex.call_llm("Test prompt")
            assert result is None


class TestApplyStateUpdates:
    """Test applying state updates to AGENCY.md files."""

    def test_apply_no_updates(self, temp_hive_dir):
        """Test applying empty update list returns 0 changes."""
        cortex = Cortex(temp_hive_dir)
        result = cortex.apply_state_updates([])
        assert result == 0

    def test_apply_single_update(self, temp_hive_dir, temp_project):
        """Test applying a single state update returns 1 change."""
        cortex = Cortex(temp_hive_dir)

        updates = [
            {
                "file": "projects/test-project/AGENCY.md",
                "field": "status",
                "value": "completed",
                "reason": "All tasks finished",
            }
        ]

        result = cortex.apply_state_updates(updates)
        assert result == 1

        # Verify the update was applied
        with open(temp_project, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)
            assert post.metadata["status"] == "completed"
            assert "last_updated" in post.metadata

    def test_apply_multiple_updates(self, temp_hive_dir, temp_project, temp_blocked_project):
        """Test applying multiple state updates returns correct count."""
        cortex = Cortex(temp_hive_dir)

        updates = [
            {
                "file": "projects/test-project/AGENCY.md",
                "field": "priority",
                "value": "low",
                "reason": "Deprioritized",
            },
            {
                "file": "projects/blocked-project/AGENCY.md",
                "field": "blocked",
                "value": False,
                "reason": "Unblocked",
            },
        ]

        result = cortex.apply_state_updates(updates)
        assert result == 2

        # Verify both updates were applied
        with open(temp_project, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)
            assert post.metadata["priority"] == "low"

        with open(temp_blocked_project, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)
            assert post.metadata["blocked"] is False

    def test_apply_update_skips_unchanged_values(self, temp_hive_dir, temp_project):
        """Test that updates with unchanged values are skipped (no file modification)."""
        cortex = Cortex(temp_hive_dir)

        # The temp_project has status="active" by default
        updates = [
            {
                "file": "projects/test-project/AGENCY.md",
                "field": "status",
                "value": "active",  # Same as current value
                "reason": "No change needed",
            }
        ]

        # Get the file's mtime before
        import os
        mtime_before = os.path.getmtime(temp_project)

        result = cortex.apply_state_updates(updates)
        assert result == 0  # No actual changes

        # File should not have been modified
        mtime_after = os.path.getmtime(temp_project)
        assert mtime_before == mtime_after

    def test_apply_update_mixed_changed_unchanged(self, temp_hive_dir, temp_project):
        """Test mix of changed and unchanged values returns correct count."""
        cortex = Cortex(temp_hive_dir)

        updates = [
            {
                "file": "projects/test-project/AGENCY.md",
                "field": "status",
                "value": "active",  # Same as current - should be skipped
                "reason": "No change",
            },
            {
                "file": "projects/test-project/AGENCY.md",
                "field": "priority",
                "value": "critical",  # Different from current "high"
                "reason": "Upgraded priority",
            },
        ]

        result = cortex.apply_state_updates(updates)
        assert result == 1  # Only priority changed

        with open(temp_project, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)
            assert post.metadata["priority"] == "critical"

    def test_apply_update_nonexistent_file(self, temp_hive_dir):
        """Test applying update to non-existent file returns 0 changes."""
        cortex = Cortex(temp_hive_dir)

        updates = [
            {
                "file": "projects/nonexistent/AGENCY.md",
                "field": "status",
                "value": "active",
                "reason": "Test",
            }
        ]

        result = cortex.apply_state_updates(updates)
        # Should handle gracefully and return 0 (no changes made)
        assert result == 0

    def test_apply_update_with_absolute_path(self, temp_hive_dir, temp_project):
        """Test applying update with absolute path."""
        cortex = Cortex(temp_hive_dir)

        updates = [
            {"file": temp_project, "field": "status", "value": "completed", "reason": "Test"}
        ]

        result = cortex.apply_state_updates(updates)
        assert result == 1

    def test_apply_update_prevents_path_traversal(self, temp_hive_dir, temp_project, tmp_path):
        """Test that updates prevent path traversal attacks."""
        cortex = Cortex(temp_hive_dir)

        # Try to update a file outside the base path
        external_file = tmp_path / "external.md"
        external_file.write_text("---\ntest: value\n---\nContent")

        updates = [
            {"file": str(external_file), "field": "status", "value": "hacked", "reason": "Test"}
        ]

        result = cortex.apply_state_updates(updates)
        # Should complete but skip the external file (0 changes)
        assert result == 0

        # Verify external file wasn't modified
        content = external_file.read_text()
        assert "hacked" not in content


class TestCortexRun:
    """Test the main Cortex run method."""

    def test_run_without_api_key(self, temp_hive_dir, monkeypatch):
        """Test run fails without API key."""
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        cortex = Cortex(temp_hive_dir)

        result = cortex.run()
        assert result is False

    def test_run_without_global_file(self, temp_hive_dir, mock_env_vars):
        """Test run fails without GLOBAL.md."""
        # Remove GLOBAL.md
        global_file = Path(temp_hive_dir) / "GLOBAL.md"
        global_file.unlink()

        cortex = Cortex(temp_hive_dir)
        result = cortex.run()
        assert result is False

    def test_run_success(
        self, temp_hive_dir, temp_project, mock_env_vars, sample_api_response, monkeypatch
    ):
        """Test successful cortex run with no state changes."""
        monkeypatch.setenv("WEAVE_DISABLED", "true")
        cortex = Cortex(temp_hive_dir)

        # Get the initial GLOBAL.md content
        global_file = Path(temp_hive_dir) / "GLOBAL.md"
        with open(global_file, "r", encoding="utf-8") as f:
            initial_content = f.read()

        with patch("tracing.requests.post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = sample_api_response
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            result = cortex.run()
            assert result is True

            # Verify GLOBAL.md was NOT updated (no state changes occurred)
            with open(global_file, "r", encoding="utf-8") as f:
                final_content = f.read()
            assert initial_content == final_content

    def test_run_with_state_updates(
        self, temp_hive_dir, temp_project, mock_env_vars, sample_llm_response, monkeypatch
    ):
        """Test cortex run with state updates."""
        monkeypatch.setenv("WEAVE_DISABLED", "true")
        cortex = Cortex(temp_hive_dir)

        # Add state updates to the response
        response_with_updates = sample_llm_response.copy()
        response_with_updates["state_updates"] = [
            {
                "file": "projects/test-project/AGENCY.md",
                "field": "status",
                "value": "completed",
                "reason": "All tasks done",
            }
        ]

        api_response = {"choices": [{"message": {"content": json.dumps(response_with_updates)}}]}

        with patch("tracing.requests.post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = api_response
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            result = cortex.run()
            assert result is True

            # Verify state was updated
            with open(temp_project, "r", encoding="utf-8") as f:
                post = frontmatter.load(f)
                assert post.metadata["status"] == "completed"

            # Verify GLOBAL.md was updated with last_cortex_run (because changes occurred)
            global_file = Path(temp_hive_dir) / "GLOBAL.md"
            with open(global_file, "r", encoding="utf-8") as f:
                post = frontmatter.load(f)
                assert post.metadata["last_cortex_run"] is not None

    def test_run_handles_llm_failure(self, temp_hive_dir, temp_project, mock_env_vars, monkeypatch):
        """Test cortex run handles LLM call failures gracefully."""
        monkeypatch.setenv("WEAVE_DISABLED", "true")
        cortex = Cortex(temp_hive_dir)

        with patch("tracing.requests.post") as mock_post:
            mock_post.side_effect = Exception("API Error")

            result = cortex.run()
            assert result is False


class TestHasUnresolvedBlockers:
    """Test the has_unresolved_blockers method."""

    def test_no_dependencies_means_no_blockers(self, temp_hive_dir, temp_project):
        """Test project without dependencies has no blockers."""
        cortex = Cortex(temp_hive_dir)
        projects = cortex.discover_projects()

        assert len(projects) == 1
        result = cortex.has_unresolved_blockers(projects[0], projects)
        assert result is False

    def test_dependency_on_completed_project(
        self, temp_hive_dir, temp_project_with_dependency, temp_prereq_project
    ):
        """Test that dependency on completed project is resolved."""
        cortex = Cortex(temp_hive_dir)
        projects = cortex.discover_projects()

        # Find the dependent project
        dependent = next(p for p in projects if p["project_id"] == "dependent-project")

        result = cortex.has_unresolved_blockers(dependent, projects)
        assert result is False

    def test_dependency_on_incomplete_project(
        self, temp_hive_dir, temp_project_with_dependency, temp_prereq_project_incomplete
    ):
        """Test that dependency on incomplete project is unresolved."""
        cortex = Cortex(temp_hive_dir)
        projects = cortex.discover_projects()

        # Find the dependent project
        dependent = next(p for p in projects if p["project_id"] == "dependent-project")

        result = cortex.has_unresolved_blockers(dependent, projects)
        assert result is True

    def test_dependency_on_unknown_project(self, temp_hive_dir, temp_project_with_dependency):
        """Test that dependency on unknown project is unresolved (conservative)."""
        cortex = Cortex(temp_hive_dir)
        projects = cortex.discover_projects()

        # Only the dependent project exists, prereq doesn't
        assert len(projects) == 1
        dependent = projects[0]

        result = cortex.has_unresolved_blockers(dependent, projects)
        assert result is True


class TestReadyWork:
    """Test the ready_work method."""

    def test_ready_work_finds_active_unclaimed_unblocked(self, temp_hive_dir, temp_project):
        """Test that ready_work finds active, unclaimed, unblocked projects."""
        cortex = Cortex(temp_hive_dir)
        ready = cortex.ready_work()

        assert len(ready) == 1
        assert ready[0]["project_id"] == "test-project"

    def test_ready_work_excludes_blocked_projects(
        self, temp_hive_dir, temp_project, temp_blocked_project
    ):
        """Test that ready_work excludes blocked projects."""
        cortex = Cortex(temp_hive_dir)
        ready = cortex.ready_work()

        # Should only find test-project, not blocked-project
        assert len(ready) == 1
        assert ready[0]["project_id"] == "test-project"

    def test_ready_work_excludes_claimed_projects(
        self, temp_hive_dir, temp_project, temp_claimed_project
    ):
        """Test that ready_work excludes projects with an owner."""
        cortex = Cortex(temp_hive_dir)
        ready = cortex.ready_work()

        # Should only find test-project, not claimed-project
        assert len(ready) == 1
        assert ready[0]["project_id"] == "test-project"

    def test_ready_work_excludes_projects_with_unresolved_deps(
        self, temp_hive_dir, temp_project_with_dependency, temp_prereq_project_incomplete
    ):
        """Test that ready_work excludes projects with unresolved dependencies."""
        cortex = Cortex(temp_hive_dir)
        ready = cortex.ready_work()

        project_ids = [p["project_id"] for p in ready]
        # prereq-project is active but unclaimed, so it should be ready
        # dependent-project has unresolved dep, so should not be ready
        assert "prereq-project" in project_ids
        assert "dependent-project" not in project_ids

    def test_ready_work_includes_projects_with_resolved_deps(
        self, temp_hive_dir, temp_project_with_dependency, temp_prereq_project
    ):
        """Test that ready_work includes projects with resolved dependencies."""
        cortex = Cortex(temp_hive_dir)
        ready = cortex.ready_work()

        project_ids = [p["project_id"] for p in ready]
        # prereq-project is completed, so not ready (status != active)
        # dependent-project has resolved dep and is active, so should be ready
        assert "dependent-project" in project_ids
        assert "prereq-project" not in project_ids

    def test_ready_work_returns_empty_when_all_blocked(self, temp_hive_dir, temp_blocked_project):
        """Test ready_work returns empty list when all projects blocked."""
        cortex = Cortex(temp_hive_dir)
        ready = cortex.ready_work()

        assert len(ready) == 0

    def test_ready_work_with_provided_projects(self, temp_hive_dir, temp_project):
        """Test ready_work with pre-provided project list."""
        cortex = Cortex(temp_hive_dir)
        projects = cortex.discover_projects()

        ready = cortex.ready_work(projects)

        assert len(ready) == 1
        assert ready[0]["project_id"] == "test-project"


class TestReadyWorkFormatters:
    """Test the ready work output formatters."""

    def test_format_ready_work_json_structure(self, temp_hive_dir, temp_project):
        """Test JSON output has correct structure."""
        cortex = Cortex(temp_hive_dir)
        ready = cortex.ready_work()

        json_output = cortex.format_ready_work_json(ready)
        data = json.loads(json_output)

        assert "timestamp" in data
        assert "count" in data
        assert "projects" in data
        assert data["count"] == 1
        assert len(data["projects"]) == 1
        assert data["projects"][0]["project_id"] == "test-project"
        assert "priority" in data["projects"][0]
        assert "tags" in data["projects"][0]
        assert "path" in data["projects"][0]

    def test_format_ready_work_json_empty(self, temp_hive_dir):
        """Test JSON output with no ready projects."""
        cortex = Cortex(temp_hive_dir)

        json_output = cortex.format_ready_work_json([])
        data = json.loads(json_output)

        assert data["count"] == 0
        assert len(data["projects"]) == 0

    def test_format_ready_work_text_structure(self, temp_hive_dir, temp_project):
        """Test text output has correct structure."""
        cortex = Cortex(temp_hive_dir)
        ready = cortex.ready_work()

        text_output = cortex.format_ready_work_text(ready)

        assert "READY WORK" in text_output
        assert "test-project" in text_output
        assert "Priority: high" in text_output
        assert "Tags: test, backend" in text_output

    def test_format_ready_work_text_empty(self, temp_hive_dir):
        """Test text output with no ready projects."""
        cortex = Cortex(temp_hive_dir)

        text_output = cortex.format_ready_work_text([])

        assert "Found 0 project(s)" in text_output
        assert "No projects ready" in text_output

    def test_format_ready_work_text_sorts_by_priority(
        self, temp_hive_dir, temp_project, temp_blocked_project
    ):
        """Test that text output sorts projects by priority."""
        # Create a low-priority ready project
        from pathlib import Path as PathLib

        project_dir = PathLib(temp_hive_dir) / "projects" / "low-prio"
        project_dir.mkdir(parents=True)

        agency_content = frontmatter.Post(
            "# Low Priority",
            project_id="low-prio",
            status="active",
            owner=None,
            blocked=False,
            priority="low",
            tags=[],
        )

        agency_file = project_dir / "AGENCY.md"
        with open(agency_file, "w", encoding="utf-8") as f:
            f.write(frontmatter.dumps(agency_content))

        cortex = Cortex(temp_hive_dir)
        ready = cortex.ready_work()

        text_output = cortex.format_ready_work_text(ready)

        # High priority should appear before low priority
        high_pos = text_output.find("test-project")
        low_pos = text_output.find("low-prio")
        assert high_pos < low_pos


class TestRunReady:
    """Test the run_ready method."""

    def test_run_ready_text_output(self, temp_hive_dir, temp_project, capsys):
        """Test run_ready with text output."""
        cortex = Cortex(temp_hive_dir)

        result = cortex.run_ready(output_json=False)

        assert result is True
        captured = capsys.readouterr()
        assert "READY WORK" in captured.out
        assert "test-project" in captured.out

    def test_run_ready_json_output(self, temp_hive_dir, temp_project, capsys):
        """Test run_ready with JSON output."""
        cortex = Cortex(temp_hive_dir)

        result = cortex.run_ready(output_json=True)

        assert result is True
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["count"] == 1
        assert data["projects"][0]["project_id"] == "test-project"


class TestBuildDependencyGraph:
    """Test the build_dependency_graph method."""

    def test_build_graph_single_project(self, temp_hive_dir, temp_project):
        """Test building graph with single project."""
        cortex = Cortex(temp_hive_dir)
        projects = cortex.discover_projects()
        graph = cortex.build_dependency_graph(projects)

        assert "nodes" in graph
        assert "edges" in graph
        assert "reverse_edges" in graph
        assert "test-project" in graph["nodes"]
        assert graph["edges"]["test-project"] == []
        assert graph["reverse_edges"]["test-project"] == []

    def test_build_graph_with_dependencies(
        self, temp_hive_dir, temp_project_with_dependency, temp_prereq_project
    ):
        """Test building graph with dependencies."""
        cortex = Cortex(temp_hive_dir)
        projects = cortex.discover_projects()
        graph = cortex.build_dependency_graph(projects)

        # prereq-project blocks dependent-project
        assert "dependent-project" in graph["edges"]["prereq-project"]
        # dependent-project is blocked by prereq-project
        assert "prereq-project" in graph["reverse_edges"]["dependent-project"]


class TestDetectCycles:
    """Test the detect_cycles method."""

    def test_no_cycles_in_simple_graph(self, temp_hive_dir, temp_project):
        """Test no cycles detected in simple graph."""
        cortex = Cortex(temp_hive_dir)
        cycles = cortex.detect_cycles()
        assert len(cycles) == 0

    def test_no_cycles_with_linear_deps(
        self, temp_hive_dir, temp_project_with_dependency, temp_prereq_project
    ):
        """Test no cycles in linear dependency chain."""
        cortex = Cortex(temp_hive_dir)
        cycles = cortex.detect_cycles()
        assert len(cycles) == 0

    def test_detect_cycle(self, temp_hive_dir):
        """Test cycle detection with circular dependencies."""
        # Create two projects that depend on each other
        from pathlib import Path as PathLib

        project_a_dir = PathLib(temp_hive_dir) / "projects" / "project-a"
        project_a_dir.mkdir(parents=True)
        agency_a = frontmatter.Post(
            "# Project A",
            project_id="project-a",
            status="active",
            owner=None,
            blocked=False,
            priority="high",
            tags=[],
            dependencies={"blocked_by": ["project-b"], "blocks": []},
        )
        with open(project_a_dir / "AGENCY.md", "w", encoding="utf-8") as f:
            f.write(frontmatter.dumps(agency_a))

        project_b_dir = PathLib(temp_hive_dir) / "projects" / "project-b"
        project_b_dir.mkdir(parents=True)
        agency_b = frontmatter.Post(
            "# Project B",
            project_id="project-b",
            status="active",
            owner=None,
            blocked=False,
            priority="high",
            tags=[],
            dependencies={"blocked_by": ["project-a"], "blocks": []},
        )
        with open(project_b_dir / "AGENCY.md", "w", encoding="utf-8") as f:
            f.write(frontmatter.dumps(agency_b))

        cortex = Cortex(temp_hive_dir)
        cycles = cortex.detect_cycles()

        assert len(cycles) > 0
        # The cycle should contain both projects
        cycle_projects = set()
        for cycle in cycles:
            cycle_projects.update(cycle)
        assert "project-a" in cycle_projects or "project-b" in cycle_projects


class TestIsBlocked:
    """Test the is_blocked method."""

    def test_unblocked_project(self, temp_hive_dir, temp_project):
        """Test is_blocked for unblocked project."""
        cortex = Cortex(temp_hive_dir)
        result = cortex.is_blocked("test-project")

        assert result["is_blocked"] is False
        assert result["reasons"] == []
        assert result["blocking_projects"] == []
        assert result["in_cycle"] is False

    def test_blocked_by_flag(self, temp_hive_dir, temp_blocked_project):
        """Test is_blocked for explicitly blocked project."""
        cortex = Cortex(temp_hive_dir)
        result = cortex.is_blocked("blocked-project")

        assert result["is_blocked"] is True
        assert "Explicitly marked as blocked" in result["reasons"]

    def test_blocked_by_dependency(
        self, temp_hive_dir, temp_project_with_dependency, temp_prereq_project_incomplete
    ):
        """Test is_blocked for project with unresolved dependency."""
        cortex = Cortex(temp_hive_dir)
        result = cortex.is_blocked("dependent-project")

        assert result["is_blocked"] is True
        assert "prereq-project" in result["blocking_projects"]

    def test_not_blocked_with_resolved_dependency(
        self, temp_hive_dir, temp_project_with_dependency, temp_prereq_project
    ):
        """Test is_blocked for project with resolved dependency."""
        cortex = Cortex(temp_hive_dir)
        result = cortex.is_blocked("dependent-project")

        assert result["is_blocked"] is False

    def test_unknown_project(self, temp_hive_dir, temp_project):
        """Test is_blocked for unknown project."""
        cortex = Cortex(temp_hive_dir)
        result = cortex.is_blocked("nonexistent-project")

        assert result["is_blocked"] is True
        assert any("not found" in r for r in result["reasons"])


class TestGetDependencySummary:
    """Test the get_dependency_summary method."""

    def test_summary_structure(self, temp_hive_dir, temp_project):
        """Test summary has correct structure."""
        cortex = Cortex(temp_hive_dir)
        summary = cortex.get_dependency_summary()

        assert "total_projects" in summary
        assert "projects" in summary
        assert "has_cycles" in summary
        assert "cycles" in summary
        assert summary["total_projects"] == 1
        assert len(summary["projects"]) == 1

    def test_summary_project_details(self, temp_hive_dir, temp_project):
        """Test summary includes project details."""
        cortex = Cortex(temp_hive_dir)
        summary = cortex.get_dependency_summary()

        proj = summary["projects"][0]
        assert proj["project_id"] == "test-project"
        assert proj["status"] == "active"
        assert proj["priority"] == "high"
        assert "blocks" in proj
        assert "blocked_by" in proj
        assert "effectively_blocked" in proj
        assert "blocking_reasons" in proj
        assert "in_cycle" in proj


class TestDependencyFormatters:
    """Test dependency output formatters."""

    def test_format_deps_json(self, temp_hive_dir, temp_project):
        """Test JSON dependency output."""
        cortex = Cortex(temp_hive_dir)
        summary = cortex.get_dependency_summary()
        output = cortex.format_deps_json(summary)

        data = json.loads(output)
        assert "timestamp" in data
        assert "total_projects" in data
        assert "has_cycles" in data
        assert "projects" in data

    def test_format_deps_text(self, temp_hive_dir, temp_project):
        """Test text dependency output."""
        cortex = Cortex(temp_hive_dir)
        summary = cortex.get_dependency_summary()
        output = cortex.format_deps_text(summary)

        assert "DEPENDENCY GRAPH" in output
        assert "test-project" in output
        assert "Legend:" in output


class TestRunDeps:
    """Test the run_deps method."""

    def test_run_deps_text(self, temp_hive_dir, temp_project, capsys):
        """Test run_deps text output."""
        cortex = Cortex(temp_hive_dir)
        result = cortex.run_deps(output_json=False)

        assert result is True
        captured = capsys.readouterr()
        assert "DEPENDENCY GRAPH" in captured.out
        assert "test-project" in captured.out

    def test_run_deps_json(self, temp_hive_dir, temp_project, capsys):
        """Test run_deps JSON output."""
        cortex = Cortex(temp_hive_dir)
        result = cortex.run_deps(output_json=True)

        assert result is True
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["total_projects"] == 1
        assert len(data["projects"]) == 1

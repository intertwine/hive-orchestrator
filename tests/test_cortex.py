"""Tests for the Cortex orchestration engine."""
# pylint: disable=unused-argument,import-error,wrong-import-position

import sys
import os
import json
from pathlib import Path
from unittest.mock import Mock, patch
import frontmatter

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

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
        assert cortex.model == "anthropic/claude-3.5-haiku"
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
        assert 'metadata' in global_ctx
        assert 'content' in global_ctx
        assert 'path' in global_ctx
        assert global_ctx['metadata']['status'] == 'active'
        assert global_ctx['metadata']['version'] == '1.0.0'

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
        assert projects[0]['project_id'] == 'test-project'
        assert projects[0]['metadata']['status'] == 'active'
        assert projects[0]['metadata']['priority'] == 'high'

    def test_discover_multiple_projects(self, temp_hive_dir, temp_project, temp_blocked_project):
        """Test discovering multiple projects."""
        cortex = Cortex(temp_hive_dir)
        projects = cortex.discover_projects()

        assert len(projects) == 2
        project_ids = [p['project_id'] for p in projects]
        assert 'test-project' in project_ids
        assert 'blocked-project' in project_ids

    def test_discover_no_projects_dir(self, temp_hive_dir):
        """Test discovering projects when directory doesn't exist."""
        # Remove projects directory
        import shutil
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


class TestBuildAnalysisPrompt:
    """Test building analysis prompts for LLM."""

    def test_build_analysis_prompt_structure(self, temp_hive_dir, temp_project):
        """Test that the analysis prompt has the correct structure."""
        cortex = Cortex(temp_hive_dir)
        global_ctx = cortex.read_global_context()
        projects = cortex.discover_projects()

        prompt = cortex.build_analysis_prompt(global_ctx, projects)

        assert "GLOBAL CONTEXT" in prompt
        assert "PROJECTS" in prompt
        assert "YOUR TASK" in prompt
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

    def test_call_llm_success(self, temp_hive_dir, mock_env_vars, sample_api_response):
        """Test successful LLM call."""
        cortex = Cortex(temp_hive_dir)

        with patch('cortex.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = sample_api_response
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            result = cortex.call_llm("Test prompt")

            assert result is not None
            assert 'summary' in result
            assert 'blocked_tasks' in result
            assert result['summary'] == "System is running well with 2 active projects"

    def test_call_llm_without_api_key(self, temp_hive_dir, monkeypatch):
        """Test LLM call without API key."""
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        cortex = Cortex(temp_hive_dir)

        result = cortex.call_llm("Test prompt")
        assert result is None

    def test_call_llm_with_markdown_wrapped_json(
        self, temp_hive_dir, mock_env_vars, sample_llm_response
    ):
        """Test LLM call with JSON wrapped in markdown code blocks."""
        cortex = Cortex(temp_hive_dir)

        markdown_response = {
            "choices": [
                {
                    "message": {
                        "content": f"```json\n{json.dumps(sample_llm_response)}\n```"
                    }
                }
            ]
        }

        with patch('cortex.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = markdown_response
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            result = cortex.call_llm("Test prompt")

            assert result is not None
            assert result['summary'] == "System is running well with 2 active projects"

    def test_call_llm_network_error(self, temp_hive_dir, mock_env_vars):
        """Test LLM call with network error."""
        cortex = Cortex(temp_hive_dir)

        with patch('cortex.requests.post') as mock_post:
            mock_post.side_effect = Exception("Network error")

            result = cortex.call_llm("Test prompt")
            assert result is None

    def test_call_llm_invalid_json_response(self, temp_hive_dir, mock_env_vars):
        """Test LLM call with invalid JSON response."""
        cortex = Cortex(temp_hive_dir)

        invalid_response = {
            "choices": [
                {
                    "message": {
                        "content": "This is not valid JSON"
                    }
                }
            ]
        }

        with patch('cortex.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = invalid_response
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            result = cortex.call_llm("Test prompt")
            assert result is None

    def test_call_llm_missing_choices(self, temp_hive_dir, mock_env_vars):
        """Test LLM call with missing choices in response."""
        cortex = Cortex(temp_hive_dir)

        invalid_response = {"error": "No choices"}

        with patch('cortex.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = invalid_response
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            result = cortex.call_llm("Test prompt")
            assert result is None


class TestApplyStateUpdates:
    """Test applying state updates to AGENCY.md files."""

    def test_apply_no_updates(self, temp_hive_dir):
        """Test applying empty update list."""
        cortex = Cortex(temp_hive_dir)
        result = cortex.apply_state_updates([])
        assert result is True

    def test_apply_single_update(self, temp_hive_dir, temp_project):
        """Test applying a single state update."""
        cortex = Cortex(temp_hive_dir)

        updates = [
            {
                "file": "projects/test-project/AGENCY.md",
                "field": "status",
                "value": "completed",
                "reason": "All tasks finished"
            }
        ]

        result = cortex.apply_state_updates(updates)
        assert result is True

        # Verify the update was applied
        with open(temp_project, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)
            assert post.metadata['status'] == 'completed'
            assert 'last_updated' in post.metadata

    def test_apply_multiple_updates(self, temp_hive_dir, temp_project, temp_blocked_project):
        """Test applying multiple state updates."""
        cortex = Cortex(temp_hive_dir)

        updates = [
            {
                "file": "projects/test-project/AGENCY.md",
                "field": "priority",
                "value": "low",
                "reason": "Deprioritized"
            },
            {
                "file": "projects/blocked-project/AGENCY.md",
                "field": "blocked",
                "value": False,
                "reason": "Unblocked"
            }
        ]

        result = cortex.apply_state_updates(updates)
        assert result is True

        # Verify both updates were applied
        with open(temp_project, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)
            assert post.metadata['priority'] == 'low'

        with open(temp_blocked_project, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)
            assert post.metadata['blocked'] is False

    def test_apply_update_nonexistent_file(self, temp_hive_dir):
        """Test applying update to non-existent file."""
        cortex = Cortex(temp_hive_dir)

        updates = [
            {
                "file": "projects/nonexistent/AGENCY.md",
                "field": "status",
                "value": "active",
                "reason": "Test"
            }
        ]

        result = cortex.apply_state_updates(updates)
        # Should handle gracefully and continue
        assert result is True

    def test_apply_update_with_absolute_path(self, temp_hive_dir, temp_project):
        """Test applying update with absolute path."""
        cortex = Cortex(temp_hive_dir)

        updates = [
            {
                "file": temp_project,
                "field": "status",
                "value": "completed",
                "reason": "Test"
            }
        ]

        result = cortex.apply_state_updates(updates)
        assert result is True

    def test_apply_update_prevents_path_traversal(self, temp_hive_dir, temp_project, tmp_path):
        """Test that updates prevent path traversal attacks."""
        cortex = Cortex(temp_hive_dir)

        # Try to update a file outside the base path
        external_file = tmp_path / "external.md"
        external_file.write_text("---\ntest: value\n---\nContent")

        updates = [
            {
                "file": str(external_file),
                "field": "status",
                "value": "hacked",
                "reason": "Test"
            }
        ]

        result = cortex.apply_state_updates(updates)
        # Should complete but skip the external file
        assert result is True

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

    def test_run_success(self, temp_hive_dir, temp_project, mock_env_vars, sample_api_response):
        """Test successful cortex run."""
        cortex = Cortex(temp_hive_dir)

        with patch('cortex.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = sample_api_response
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            result = cortex.run()
            assert result is True

            # Verify GLOBAL.md was updated with last_cortex_run
            global_file = Path(temp_hive_dir) / "GLOBAL.md"
            with open(global_file, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
                assert post.metadata['last_cortex_run'] is not None

    def test_run_with_state_updates(
        self, temp_hive_dir, temp_project, mock_env_vars, sample_llm_response
    ):
        """Test cortex run with state updates."""
        cortex = Cortex(temp_hive_dir)

        # Add state updates to the response
        response_with_updates = sample_llm_response.copy()
        response_with_updates['state_updates'] = [
            {
                "file": "projects/test-project/AGENCY.md",
                "field": "status",
                "value": "completed",
                "reason": "All tasks done"
            }
        ]

        api_response = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(response_with_updates)
                    }
                }
            ]
        }

        with patch('cortex.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = api_response
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            result = cortex.run()
            assert result is True

            # Verify state was updated
            with open(temp_project, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
                assert post.metadata['status'] == 'completed'

    def test_run_handles_llm_failure(self, temp_hive_dir, temp_project, mock_env_vars):
        """Test cortex run handles LLM call failures gracefully."""
        cortex = Cortex(temp_hive_dir)

        with patch('cortex.requests.post') as mock_post:
            mock_post.side_effect = Exception("API Error")

            result = cortex.run()
            assert result is False

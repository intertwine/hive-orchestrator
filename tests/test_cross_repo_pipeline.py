#!/usr/bin/env python3
"""
Tests for the Cross-Repository Multi-Agent Pipeline.
"""

import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from src.cross_repo_pipeline import (
    CrossRepoPipeline,
    PhaseConfig,
    ExternalRepoInfo,
)


class TestPhaseConfig:
    """Test PhaseConfig dataclass."""

    def test_phase_config_creation(self):
        """Test creating a PhaseConfig."""
        config = PhaseConfig(
            name="test",
            model="test-model",
            system_prompt="Test prompt",
            output_section="## Test Section",
        )
        assert config.name == "test"
        assert config.model == "test-model"
        assert config.system_prompt == "Test prompt"
        assert config.output_section == "## Test Section"


class TestExternalRepoInfo:
    """Test ExternalRepoInfo dataclass."""

    def test_external_repo_info_defaults(self):
        """Test ExternalRepoInfo with default values."""
        info = ExternalRepoInfo(url="https://github.com/test/repo")
        assert info.url == "https://github.com/test/repo"
        assert info.branch == "main"
        assert info.local_path is None
        assert info.file_tree == ""
        assert info.key_files == {}

    def test_external_repo_info_custom_branch(self):
        """Test ExternalRepoInfo with custom branch."""
        info = ExternalRepoInfo(
            url="https://github.com/test/repo",
            branch="develop",
        )
        assert info.branch == "develop"


class TestCrossRepoPipelineInitialization:
    """Test CrossRepoPipeline initialization."""

    def test_pipeline_initialization(self, tmp_path):
        """Test basic pipeline initialization."""
        agency_md = tmp_path / "AGENCY.md"
        agency_md.write_text("""---
project_id: test
status: active
target_repo:
  url: https://github.com/test/repo
---
# Test
""")

        pipeline = CrossRepoPipeline(
            project_path=agency_md,
            base_path=tmp_path,
        )

        assert pipeline.project_path == agency_md
        assert pipeline.base_path == tmp_path
        assert pipeline.dry_run is False

    def test_pipeline_dry_run(self, tmp_path):
        """Test pipeline initialization with dry run."""
        agency_md = tmp_path / "AGENCY.md"
        agency_md.write_text("""---
project_id: test
status: active
target_repo:
  url: https://github.com/test/repo
---
# Test
""")

        pipeline = CrossRepoPipeline(
            project_path=agency_md,
            base_path=tmp_path,
            dry_run=True,
        )

        assert pipeline.dry_run is True


class TestCrossRepoPipelineValidation:
    """Test CrossRepoPipeline validation."""

    def test_validate_environment_no_api_key(self, tmp_path):
        """Test validation fails without API key."""
        agency_md = tmp_path / "AGENCY.md"
        agency_md.write_text("""---
project_id: test
target_repo:
  url: https://github.com/test/repo
---
# Test
""")

        with patch.dict(os.environ, {}, clear=True):
            pipeline = CrossRepoPipeline(project_path=agency_md)
            pipeline.api_key = None
            assert pipeline.validate_environment() is False

    @patch("subprocess.run")
    def test_validate_environment_no_git(self, mock_run, tmp_path):
        """Test validation fails without git."""
        agency_md = tmp_path / "AGENCY.md"
        agency_md.write_text("""---
project_id: test
target_repo:
  url: https://github.com/test/repo
---
# Test
""")

        mock_run.side_effect = FileNotFoundError()

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            pipeline = CrossRepoPipeline(project_path=agency_md)
            assert pipeline.validate_environment() is False


class TestCrossRepoPipelineProjectLoading:
    """Test project loading functionality."""

    def test_load_project_success(self, tmp_path):
        """Test successful project loading."""
        agency_md = tmp_path / "AGENCY.md"
        agency_md.write_text("""---
project_id: test-project
status: active
phase: analyze
target_repo:
  url: https://github.com/test/repo
  branch: develop
models:
  analyst: custom/model-1
  strategist: custom/model-2
  implementer: custom/model-3
---
# Test Project
""")

        pipeline = CrossRepoPipeline(project_path=agency_md)
        assert pipeline.load_project() is True

        assert pipeline.external_repo.url == "https://github.com/test/repo"
        assert pipeline.external_repo.branch == "develop"
        assert pipeline.models["analyst"] == "custom/model-1"
        assert pipeline.models["strategist"] == "custom/model-2"
        assert pipeline.models["implementer"] == "custom/model-3"

    def test_load_project_default_models(self, tmp_path):
        """Test project loading with default models."""
        agency_md = tmp_path / "AGENCY.md"
        agency_md.write_text("""---
project_id: test-project
target_repo:
  url: https://github.com/test/repo
---
# Test
""")

        pipeline = CrossRepoPipeline(project_path=agency_md)
        assert pipeline.load_project() is True

        # Should use defaults
        assert "haiku" in pipeline.models["analyst"]
        assert "gemini" in pipeline.models["strategist"]
        assert "gpt-4" in pipeline.models["implementer"]

    def test_load_project_missing_target_repo(self, tmp_path):
        """Test project loading fails without target_repo."""
        agency_md = tmp_path / "AGENCY.md"
        agency_md.write_text("""---
project_id: test-project
status: active
---
# Test
""")

        pipeline = CrossRepoPipeline(project_path=agency_md)
        assert pipeline.load_project() is False


class TestCrossRepoPipelineFileTree:
    """Test file tree generation."""

    def test_generate_file_tree(self, tmp_path):
        """Test file tree generation."""
        # Create a simple directory structure
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "index.ts").write_text("// main file")
        (tmp_path / "src" / "utils").mkdir()
        (tmp_path / "src" / "utils" / "helper.ts").write_text("// helper")
        (tmp_path / "package.json").write_text("{}")
        (tmp_path / ".git").mkdir()  # Should be excluded

        agency_md = tmp_path / "test" / "AGENCY.md"
        agency_md.parent.mkdir()
        agency_md.write_text("""---
project_id: test
target_repo:
  url: https://github.com/test/repo
---
# Test
""")

        pipeline = CrossRepoPipeline(project_path=agency_md)
        pipeline.external_repo = ExternalRepoInfo(
            url="https://github.com/test/repo",
            local_path=tmp_path,
        )

        tree = pipeline.generate_file_tree(max_depth=3)

        assert "src" in tree
        assert "index.ts" in tree
        assert "package.json" in tree
        assert ".git" not in tree  # Should be excluded


class TestCrossRepoPipelineKeyFiles:
    """Test key file reading."""

    def test_read_key_files(self, tmp_path):
        """Test reading key files from repo."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "index.ts").write_text("export const main = () => {};")
        (tmp_path / "package.json").write_text('{"name": "test"}')
        (tmp_path / "README.md").write_text("# Test Project")

        agency_md = tmp_path / "test" / "AGENCY.md"
        agency_md.parent.mkdir()
        agency_md.write_text("""---
project_id: test
target_repo:
  url: https://github.com/test/repo
---
# Test
""")

        pipeline = CrossRepoPipeline(project_path=agency_md)
        pipeline.external_repo = ExternalRepoInfo(
            url="https://github.com/test/repo",
            local_path=tmp_path,
        )

        key_files = pipeline.read_key_files()

        assert "package.json" in key_files
        assert "README.md" in key_files
        assert "src/index.ts" in key_files
        assert '{"name": "test"}' in key_files["package.json"]


class TestCrossRepoPipelineAgencyMdUpdates:
    """Test AGENCY.md update functionality."""

    def test_update_agency_md_existing_section(self, tmp_path):
        """Test updating an existing section in AGENCY.md."""
        agency_md = tmp_path / "AGENCY.md"
        agency_md.write_text("""---
project_id: test
target_repo:
  url: https://github.com/test/repo
---
# Test

## Phase 1: Analysis

*Placeholder*

## Phase 2: Strategy

*Placeholder*
""")

        pipeline = CrossRepoPipeline(project_path=agency_md)
        pipeline.load_project()

        result = pipeline.update_agency_md(
            "## Phase 1: Analysis",
            "This is the new analysis content."
        )

        assert result is True

        # Read back and verify
        content = agency_md.read_text()
        assert "This is the new analysis content." in content
        assert "*Placeholder*" not in content.split("## Phase 1:")[1].split("## Phase 2:")[0]

    def test_update_agency_md_dry_run(self, tmp_path):
        """Test that dry run doesn't modify files."""
        agency_md = tmp_path / "AGENCY.md"
        original_content = """---
project_id: test
target_repo:
  url: https://github.com/test/repo
---
# Test

## Phase 1: Analysis

*Placeholder*
"""
        agency_md.write_text(original_content)

        pipeline = CrossRepoPipeline(project_path=agency_md, dry_run=True)
        pipeline.load_project()

        result = pipeline.update_agency_md(
            "## Phase 1: Analysis",
            "New content"
        )

        assert result is True
        # File should be unchanged
        assert agency_md.read_text() == original_content


class TestCrossRepoPipelineAgentNotes:
    """Test agent note functionality."""

    def test_add_agent_note_existing_section(self, tmp_path):
        """Test adding note to existing Agent Notes section."""
        agency_md = tmp_path / "AGENCY.md"
        agency_md.write_text("""---
project_id: test
target_repo:
  url: https://github.com/test/repo
---
# Test

## Agent Notes

""")

        pipeline = CrossRepoPipeline(project_path=agency_md)
        pipeline.load_project()

        result = pipeline.add_agent_note("TestAgent", "Test note message")

        assert result is True

        content = agency_md.read_text()
        assert "TestAgent" in content
        assert "Test note message" in content

    def test_add_agent_note_creates_section(self, tmp_path):
        """Test that agent note creates section if missing."""
        agency_md = tmp_path / "AGENCY.md"
        agency_md.write_text("""---
project_id: test
target_repo:
  url: https://github.com/test/repo
---
# Test
""")

        pipeline = CrossRepoPipeline(project_path=agency_md)
        pipeline.load_project()

        result = pipeline.add_agent_note("TestAgent", "Test note")

        assert result is True

        content = agency_md.read_text()
        assert "## Agent Notes" in content
        assert "TestAgent" in content


class TestCrossRepoPipelinePhaseUpdate:
    """Test phase update functionality."""

    def test_update_phase(self, tmp_path):
        """Test updating the current phase."""
        agency_md = tmp_path / "AGENCY.md"
        agency_md.write_text("""---
project_id: test
phase: analyze
target_repo:
  url: https://github.com/test/repo
---
# Test
""")

        pipeline = CrossRepoPipeline(project_path=agency_md)
        pipeline.load_project()

        result = pipeline.update_phase("strategize")

        assert result is True

        # Reload and check
        pipeline2 = CrossRepoPipeline(project_path=agency_md)
        pipeline2.load_project()
        assert pipeline2.project_data["metadata"]["phase"] == "strategize"


class TestCrossRepoPipelineLLMCalls:
    """Test LLM call functionality."""

    @patch("src.cross_repo_pipeline.traced_llm_call")
    def test_call_llm_success(self, mock_traced_call, tmp_path):
        """Test successful LLM call."""
        agency_md = tmp_path / "AGENCY.md"
        agency_md.write_text("""---
project_id: test
target_repo:
  url: https://github.com/test/repo
---
# Test
""")

        mock_traced_call.return_value = {
            "metadata": MagicMock(
                success=True,
                latency_ms=100,
                total_tokens=500,
                error=None,
            ),
            "response": {
                "choices": [
                    {"message": {"content": "Test response"}}
                ]
            }
        }

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            pipeline = CrossRepoPipeline(project_path=agency_md)

            result = pipeline.call_llm(
                model="test-model",
                system_prompt="Test system",
                user_prompt="Test user",
            )

            assert result == "Test response"
            mock_traced_call.assert_called_once()

    @patch("src.cross_repo_pipeline.traced_llm_call")
    def test_call_llm_failure(self, mock_traced_call, tmp_path):
        """Test LLM call failure handling."""
        agency_md = tmp_path / "AGENCY.md"
        agency_md.write_text("""---
project_id: test
target_repo:
  url: https://github.com/test/repo
---
# Test
""")

        mock_traced_call.return_value = {
            "metadata": MagicMock(
                success=False,
                latency_ms=None,
                total_tokens=None,
                error="API Error",
            ),
            "response": None,
        }

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            pipeline = CrossRepoPipeline(project_path=agency_md)

            result = pipeline.call_llm(
                model="test-model",
                system_prompt="Test",
                user_prompt="Test",
            )

            assert result is None


class TestCrossRepoPipelineClone:
    """Test repository cloning."""

    @patch("subprocess.run")
    def test_clone_external_repo_success(self, mock_run, tmp_path):
        """Test successful repository clone."""
        agency_md = tmp_path / "AGENCY.md"
        agency_md.write_text("""---
project_id: test
target_repo:
  url: https://github.com/test/repo
  branch: main
---
# Test
""")

        mock_run.return_value = MagicMock(returncode=0, stderr="")

        pipeline = CrossRepoPipeline(project_path=agency_md)
        pipeline.load_project()

        result = pipeline.clone_external_repo()

        assert result is True
        assert pipeline.external_repo.local_path is not None

        # Cleanup
        if pipeline.external_repo.local_path:
            shutil.rmtree(pipeline.external_repo.local_path, ignore_errors=True)

    @patch("subprocess.run")
    def test_clone_external_repo_failure(self, mock_run, tmp_path):
        """Test repository clone failure."""
        agency_md = tmp_path / "AGENCY.md"
        agency_md.write_text("""---
project_id: test
target_repo:
  url: https://github.com/test/repo
---
# Test
""")

        mock_run.return_value = MagicMock(returncode=1, stderr="Clone failed")

        pipeline = CrossRepoPipeline(project_path=agency_md)
        pipeline.load_project()

        result = pipeline.clone_external_repo()

        assert result is False


class TestCrossRepoPipelinePhases:
    """Test individual pipeline phases."""

    @patch.object(CrossRepoPipeline, "call_llm")
    @patch.object(CrossRepoPipeline, "generate_file_tree")
    @patch.object(CrossRepoPipeline, "read_key_files")
    def test_run_analyst_phase(
        self, mock_read_files, mock_tree, mock_llm, tmp_path
    ):
        """Test analyst phase execution."""
        agency_md = tmp_path / "AGENCY.md"
        agency_md.write_text("""---
project_id: test
phase: analyze
target_repo:
  url: https://github.com/test/repo
models:
  analyst: test/model
---
# Test

## Phase 1: Analysis

*Placeholder*
""")

        mock_tree.return_value = "test/\n|-- file.ts"
        mock_read_files.return_value = {"file.ts": "code"}
        mock_llm.return_value = "This is the analysis result."

        pipeline = CrossRepoPipeline(project_path=agency_md)
        pipeline.load_project()
        pipeline.external_repo.local_path = tmp_path

        result = pipeline.run_analyst_phase()

        assert result is True
        mock_llm.assert_called_once()

        # Check AGENCY.md was updated
        content = agency_md.read_text()
        assert "This is the analysis result." in content

    @patch.object(CrossRepoPipeline, "call_llm")
    def test_run_strategist_phase(self, mock_llm, tmp_path):
        """Test strategist phase execution."""
        agency_md = tmp_path / "AGENCY.md"
        agency_md.write_text("""---
project_id: test
phase: strategize
target_repo:
  url: https://github.com/test/repo
models:
  strategist: test/model
---
# Test

## Phase 1: Analysis

Previous analysis content here.

## Phase 2: Strategy

*Placeholder*
""")

        mock_llm.return_value = "Recommended improvement: Add error handling."

        pipeline = CrossRepoPipeline(project_path=agency_md)
        pipeline.load_project()
        pipeline.external_repo = ExternalRepoInfo(
            url="https://github.com/test/repo",
            local_path=tmp_path,
        )

        result = pipeline.run_strategist_phase()

        assert result is True
        mock_llm.assert_called_once()

        # Check AGENCY.md was updated
        content = agency_md.read_text()
        assert "Recommended improvement" in content


class TestCrossRepoPipelineDefaultModels:
    """Test default model configuration."""

    def test_default_models_exist(self):
        """Verify all phases have default models."""
        assert "analyst" in CrossRepoPipeline.DEFAULT_MODELS
        assert "strategist" in CrossRepoPipeline.DEFAULT_MODELS
        assert "implementer" in CrossRepoPipeline.DEFAULT_MODELS

    def test_phases_configuration(self):
        """Verify all phases are properly configured."""
        assert "analyze" in CrossRepoPipeline.PHASES
        assert "strategize" in CrossRepoPipeline.PHASES
        assert "implement" in CrossRepoPipeline.PHASES

        for phase in CrossRepoPipeline.PHASES.values():
            assert phase.name
            assert phase.model
            assert phase.system_prompt
            assert phase.output_section

"""Shared pytest fixtures for Agent Hive tests."""

import json
import tempfile
import shutil
from pathlib import Path
import pytest
import frontmatter


@pytest.fixture
def temp_hive_dir():
    """Create a temporary Agent Hive directory structure for testing."""
    temp_dir = tempfile.mkdtemp()

    # Create directory structure
    projects_dir = Path(temp_dir) / "projects"
    projects_dir.mkdir()

    # Create GLOBAL.md
    global_content = frontmatter.Post(
        """# Agent Hive - Global Context

## Overview
Test global context.
""",
        status="active",
        last_cortex_run=None,
        version="1.0.0",
        orchestrator="agent-hive"
    )

    global_file = Path(temp_dir) / "GLOBAL.md"
    with open(global_file, 'w', encoding='utf-8') as f:
        f.write(frontmatter.dumps(global_content))

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def temp_project(temp_hive_dir):  # pylint: disable=redefined-outer-name
    """Create a temporary test project in the hive directory."""
    project_dir = Path(temp_hive_dir) / "projects" / "test-project"
    project_dir.mkdir(parents=True)

    # Create AGENCY.md
    agency_content = frontmatter.Post(
        """# Test Project

## Objective
This is a test project.

## Tasks
- [ ] Task 1
- [ ] Task 2
- [x] Completed task

## Agent Notes
- Test note
""",
        project_id="test-project",
        status="active",
        owner=None,
        last_updated="2025-01-15T10:30:00Z",
        blocked=False,
        blocking_reason=None,
        priority="high",
        tags=["test", "backend"]
    )

    agency_file = project_dir / "AGENCY.md"
    with open(agency_file, 'w', encoding='utf-8') as f:
        f.write(frontmatter.dumps(agency_content))

    # Create a sample file in the project
    sample_file = project_dir / "sample.py"
    sample_file.write_text("# Sample Python file\nprint('Hello')")

    return str(agency_file)


@pytest.fixture
def temp_blocked_project(temp_hive_dir):  # pylint: disable=redefined-outer-name
    """Create a blocked project for testing."""
    project_dir = Path(temp_hive_dir) / "projects" / "blocked-project"
    project_dir.mkdir(parents=True)

    agency_content = frontmatter.Post(
        """# Blocked Project

## Objective
This project is blocked.

## Tasks
- [ ] Blocked task

## Agent Notes
- Waiting for external dependency
""",
        project_id="blocked-project",
        status="blocked",
        owner="test-agent",
        last_updated="2025-01-15T10:30:00Z",
        blocked=True,
        blocking_reason="Waiting for API key",
        priority="medium",
        tags=["test"]
    )

    agency_file = project_dir / "AGENCY.md"
    with open(agency_file, 'w', encoding='utf-8') as f:
        f.write(frontmatter.dumps(agency_content))

    return str(agency_file)


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-api-key-12345")
    monkeypatch.setenv("OPENROUTER_MODEL", "anthropic/claude-3.5-haiku")


@pytest.fixture
def sample_llm_response():
    """Sample LLM response for testing."""
    return {
        "summary": "System is running well with 2 active projects",
        "blocked_tasks": [
            {
                "project_id": "blocked-project",
                "task": "Blocked task",
                "reason": "Waiting for API key",
                "recommendation": "Provide the required API key"
            }
        ],
        "state_updates": [],
        "new_projects": [],
        "notes": "All systems operational"
    }


@pytest.fixture
def sample_api_response(sample_llm_response):  # pylint: disable=redefined-outer-name
    """Sample OpenRouter API response structure."""
    return {
        "choices": [
            {
                "message": {
                    "content": json.dumps(sample_llm_response)
                }
            }
        ]
    }

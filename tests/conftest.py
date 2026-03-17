"""Shared pytest fixtures for Agent Hive tests."""

import json
from pathlib import Path
import shutil
import subprocess
import tempfile

import pytest
import frontmatter

from src.hive.store.projects import discover_projects


def init_git_repo(path: str | Path) -> None:
    """Initialize a test Git repository with a stable identity."""
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "tests@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Hive Tests"], cwd=path, check=True)


def safe_program(command: str = "python -c \"print('ok')\"") -> str:
    """Return a safe PROGRAM.md contract for driver and console tests."""
    return f"""---
program_version: 1
mode: workflow
default_executor: local
budgets:
  max_wall_clock_minutes: 30
  max_steps: 25
  max_tokens: 20000
  max_cost_usd: 2.0
paths:
  allow:
    - src/**
    - tests/**
    - docs/**
  deny: []
commands:
  allow:
    - {json.dumps(command)}
  deny: []
evaluators:
  - id: unit
    command: {json.dumps(command)}
    required: true
promotion:
  allow_unsafe_without_evaluators: false
  allow_accept_without_changes: true
  requires_all:
    - unit
  review_required_when_paths_match: []
  auto_close_task: false
escalation:
  when_paths_match: []
  when_commands_match: []
---

# Goal

Run a governed task safely.
"""


def write_safe_program(
    root: str | Path,
    project_id: str,
    command: str = "python -c \"print('ok')\"",
):
    """Write the shared safe PROGRAM.md test contract into a project."""
    project = next(project for project in discover_projects(root) if project.id == project_id)
    project.program_path.write_text(safe_program(command), encoding="utf-8")
    return project


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
        last_sync=None,
        version="1.0.0",
        # Internal metadata keeps the product identifier even though the
        # published distribution is now mellona-hive.
        orchestrator="agent-hive",
    )

    global_file = Path(temp_dir) / "GLOBAL.md"
    with open(global_file, "w", encoding="utf-8") as f:
        f.write(frontmatter.dumps(global_content))

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def commit_workspace():
    """Commit all current workspace files into a temporary Git repo."""

    def _commit(path: str | Path, message: str = "test snapshot") -> str:
        root = Path(path)
        if not (root / ".git").exists():
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(
                ["git", "config", "user.email", "tests@example.com"], cwd=root, check=True
            )
            subprocess.run(["git", "config", "user.name", "Agent Hive Tests"], cwd=root, check=True)
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        status = subprocess.run(
            ["git", "status", "--short"],
            cwd=root,
            text=True,
            capture_output=True,
            check=True,
        )
        if status.stdout.strip():
            subprocess.run(["git", "commit", "-q", "-m", message], cwd=root, check=True)
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            text=True,
            capture_output=True,
            check=True,
        )
        return head.stdout.strip()

    return _commit


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
        tags=["test", "backend"],
    )

    agency_file = project_dir / "AGENCY.md"
    with open(agency_file, "w", encoding="utf-8") as f:
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
        tags=["test"],
    )

    agency_file = project_dir / "AGENCY.md"
    with open(agency_file, "w", encoding="utf-8") as f:
        f.write(frontmatter.dumps(agency_content))

    return str(agency_file)


@pytest.fixture
def temp_project_with_dependency(temp_hive_dir):  # pylint: disable=redefined-outer-name
    """Create a project that depends on another project."""
    project_dir = Path(temp_hive_dir) / "projects" / "dependent-project"
    project_dir.mkdir(parents=True)

    agency_content = frontmatter.Post(
        """# Dependent Project

## Objective
This project depends on another.

## Tasks
- [ ] Task that needs prereq
""",
        project_id="dependent-project",
        status="active",
        owner=None,
        last_updated="2025-01-15T10:30:00Z",
        blocked=False,
        blocking_reason=None,
        priority="medium",
        tags=["test"],
        dependencies={
            "blocked_by": ["prereq-project"],
            "blocks": [],
            "parent": None,
            "related": [],
        },
    )

    agency_file = project_dir / "AGENCY.md"
    with open(agency_file, "w", encoding="utf-8") as f:
        f.write(frontmatter.dumps(agency_content))

    return str(agency_file)


@pytest.fixture
def temp_prereq_project(temp_hive_dir):  # pylint: disable=redefined-outer-name
    """Create a prerequisite project (completed)."""
    project_dir = Path(temp_hive_dir) / "projects" / "prereq-project"
    project_dir.mkdir(parents=True)

    agency_content = frontmatter.Post(
        """# Prerequisite Project

## Objective
This is a prerequisite project.

## Tasks
- [x] Done
""",
        project_id="prereq-project",
        status="completed",
        owner=None,
        last_updated="2025-01-15T10:30:00Z",
        blocked=False,
        blocking_reason=None,
        priority="high",
        tags=["test"],
    )

    agency_file = project_dir / "AGENCY.md"
    with open(agency_file, "w", encoding="utf-8") as f:
        f.write(frontmatter.dumps(agency_content))

    return str(agency_file)


@pytest.fixture
def temp_prereq_project_incomplete(temp_hive_dir):  # pylint: disable=redefined-outer-name
    """Create an incomplete prerequisite project."""
    project_dir = Path(temp_hive_dir) / "projects" / "prereq-project"
    project_dir.mkdir(parents=True)

    agency_content = frontmatter.Post(
        """# Prerequisite Project

## Objective
This is a prerequisite project that is not done.

## Tasks
- [ ] Not done yet
""",
        project_id="prereq-project",
        status="active",
        owner=None,
        last_updated="2025-01-15T10:30:00Z",
        blocked=False,
        blocking_reason=None,
        priority="high",
        tags=["test"],
    )

    agency_file = project_dir / "AGENCY.md"
    with open(agency_file, "w", encoding="utf-8") as f:
        f.write(frontmatter.dumps(agency_content))

    return str(agency_file)


@pytest.fixture
def temp_claimed_project(temp_hive_dir):  # pylint: disable=redefined-outer-name
    """Create a project that is already claimed by an agent."""
    project_dir = Path(temp_hive_dir) / "projects" / "claimed-project"
    project_dir.mkdir(parents=True)

    agency_content = frontmatter.Post(
        """# Claimed Project

## Objective
This project is being worked on.

## Tasks
- [ ] In progress task
""",
        project_id="claimed-project",
        status="active",
        owner="claude-3.5-sonnet",
        last_updated="2025-01-15T10:30:00Z",
        blocked=False,
        blocking_reason=None,
        priority="high",
        tags=["test"],
    )

    agency_file = project_dir / "AGENCY.md"
    with open(agency_file, "w", encoding="utf-8") as f:
        f.write(frontmatter.dumps(agency_content))

    return str(agency_file)

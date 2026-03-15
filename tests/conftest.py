"""Shared pytest fixtures for Agent Hive tests."""

from pathlib import Path
import shutil
import subprocess
import tempfile

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

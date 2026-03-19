"""Regression checks for maintainer docs, helpers, and workflow guardrails."""

from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_yaml(relative_path: str) -> dict:
    return yaml.safe_load((REPO_ROOT / relative_path).read_text(encoding="utf-8"))


def test_v23_status_doc_tracks_release_gates_and_next_blocker():
    """The maintainer status ledger should stay compact and release-gate oriented."""
    status_doc = (REPO_ROOT / "docs" / "V2_3_STATUS.md").read_text(encoding="utf-8")

    assert "# Hive v2.3 Status" in status_doc
    assert "## Release Gate Ledger" in status_doc
    assert "## Next Blocker" in status_doc
    assert "Deep Claude live driver with SDK adapter and approval bridging" in status_doc
    assert "One real hosted sandbox path" in status_doc


def test_pull_request_template_enforces_slice_and_review_discipline():
    """The PR template should ask for blocker, validation, and review closure."""
    template = (REPO_ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md").read_text(encoding="utf-8")

    assert "## Blocker Removed" in template
    assert "## Why This Slice Is Mergeable" in template
    assert "## Validation" in template
    assert "## Review Discipline" in template
    assert "@Claude review" in template


def test_makefile_exposes_workspace_status_helper():
    """Maintainers should have one checkout-only status command."""
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

    assert "workspace-status" in makefile
    assert 'pgrep -fl "codex_app_server_worker.py|claude_sdk_worker.py|agent_dispatcher|hive "' in makefile
    assert "git ls-files --others --exclude-standard -- .hive/events" in makefile


def test_ci_workflow_cancels_superseded_runs():
    """Rapid PR pushes should cancel older CI runs instead of piling up."""
    workflow = _load_yaml(".github/workflows/ci.yml")

    assert workflow["concurrency"]["cancel-in-progress"] is True
    assert "github.event.pull_request.number || github.ref" in workflow["concurrency"]["group"]


def test_claude_review_workflow_cancels_superseded_pr_reviews():
    """Claude PR review should track the latest push, not every outdated head."""
    workflow = _load_yaml(".github/workflows/claude.yml")
    review = workflow["jobs"]["claude-review"]

    assert review["concurrency"]["cancel-in-progress"] is True
    assert "github.event.pull_request.number || github.ref" in review["concurrency"]["group"]


def test_scheduled_uv_installers_use_setup_action():
    """Scheduled maintainer workflows should use the standard uv setup action."""
    ready_work = _load_yaml(".github/workflows/agent-assignment.yml")
    projection_sync = _load_yaml(".github/workflows/projection-sync.yml")

    ready_steps = ready_work["jobs"]["ready-work"]["steps"]
    projection_steps = projection_sync["jobs"]["projection-sync"]["steps"]

    assert any(step.get("uses") == "astral-sh/setup-uv@v7" for step in ready_steps)
    assert any(step.get("uses") == "astral-sh/setup-uv@v7" for step in projection_steps)

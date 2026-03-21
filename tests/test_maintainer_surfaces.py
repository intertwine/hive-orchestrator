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
    assert "## Scope Lock" in status_doc
    assert "## Release Gate Ledger" in status_doc
    assert "## Next Blocker" in status_doc
    assert "Deep Claude live driver with SDK adapter and approval bridging" in status_doc
    assert "One real hosted sandbox path" in status_doc
    assert "One real hosted sandbox path | Complete" in status_doc
    assert "One real self-hosted sandbox path | Complete" in status_doc
    assert "Pi driver at acceptance bar | Deferred" in status_doc
    assert "full hybrid retrieval stack" in status_doc
    assert "the Daytona self-hosted proof now passed in a credentialed environment" in status_doc
    assert "Explainable retrieval, packaged corpus, and traces | Complete" in status_doc
    assert "Release docs, demo, and acceptance alignment | Complete" in status_doc
    assert "built-artifact release smoke path now proves installed-package `hive search`" in status_doc
    assert "Status: v2.3.1 released" in status_doc
    assert "## Release History" in status_doc
    assert "`v2.3.0`" in status_doc
    assert "`v2.3.1`" in status_doc


def test_v23_acceptance_doc_tracks_scope_locked_remote_sandbox_truth():
    """The v2.3 acceptance doc should narrow remote sandbox expectations to shipped truth."""
    acceptance_doc = (
        REPO_ROOT / "docs" / "hive-v2.3-rfc" / "HIVE_V2_3_ACCEPTANCE_TESTS.md"
    ).read_text(encoding="utf-8")

    assert "Scope-locked v2.3 note:" in acceptance_doc
    assert "E2B is release-accepted as an ephemeral upload-only hosted path." in acceptance_doc
    assert "E2B pause/resume and downloaded artifact sync are deferred" in acceptance_doc
    assert "Daytona truthfully documents upload-only sync and the current mount/network limits" in acceptance_doc
    assert "Pi remains available as an honest staged driver" in acceptance_doc
    assert "Pi (deferred from the v2.3 release bar)" in acceptance_doc


def test_release_docs_require_scope_locked_v23_story_and_installed_search_proof():
    """Release docs should require docs/demo alignment and installed retrieval proof for v2.3."""
    release_doc = (REPO_ROOT / "docs" / "RELEASING.md").read_text(encoding="utf-8")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    operator_doc = (REPO_ROOT / "docs" / "OPERATOR_FLOWS.md").read_text(encoding="utf-8")
    start_here = (REPO_ROOT / "docs" / "START_HERE.md").read_text(encoding="utf-8")

    assert "README, demo walkthrough, compare-harness, and operator docs" in release_doc
    assert "Installed-package `hive search` is proven useful" in release_doc
    assert "make bump-version BUMP=minor" in release_doc
    assert "Update [docs/V2_3_STATUS.md](/docs/V2_3_STATUS.md)" in release_doc
    assert 'hive search "runtime contract" --scope api --limit 5 --json' in release_doc
    assert 'hive search "sandbox doctor" --scope examples --limit 5 --json' in release_doc
    assert 'hive onboard demo --prompt "Create a small React website about bees."' in release_doc
    assert "built-artifact smoke script now proves installed-package" in release_doc
    assert "truthful v2.3 operator surface" in readme
    assert "Hive v2.3 assumes the operator mostly supervises" in operator_doc
    assert "If you want the latest unreleased checkout" in start_here


def test_archive_and_rfc_docs_frame_historical_material_clearly():
    """Historical notes and broader RFC bundles should point readers back to the live v2.3 ledger."""
    archive_readme = (REPO_ROOT / "docs" / "archive" / "README.md").read_text(encoding="utf-8")
    onboarding_note = (
        REPO_ROOT / "docs" / "archive" / "V2_2_4_ONBOARDING_POLISH.md"
    ).read_text(encoding="utf-8")
    ux_sweep = (REPO_ROOT / "docs" / "archive" / "UX_SWEEP.md").read_text(encoding="utf-8")
    rfc_readme = (REPO_ROOT / "docs" / "hive-v2.3-rfc" / "README.md").read_text(encoding="utf-8")
    implementation_plan = (
        REPO_ROOT / "docs" / "hive-v2.3-rfc" / "HIVE_V2_3_IMPLEMENTATION_PLAN.md"
    ).read_text(encoding="utf-8")
    acceptance_doc = (
        REPO_ROOT / "docs" / "hive-v2.3-rfc" / "HIVE_V2_3_ACCEPTANCE_TESTS.md"
    ).read_text(encoding="utf-8")
    security_doc = (REPO_ROOT / "SECURITY.md").read_text(encoding="utf-8")

    assert "# Archived Docs" in archive_readme
    assert "no longer part of the primary user or maintainer path" in archive_readme
    assert "Archived note" in onboarding_note
    assert "Archived note" in ux_sweep
    assert "historical planning and design reference" in rfc_readme
    assert "Current scoped release truth lives in" in rfc_readme
    assert "Status: Historical planning reference" in implementation_plan
    assert "Status: Active scope-locked release-gate reference" in acceptance_doc
    assert "| 2.2.x   | yes       |" in security_doc
    assert "| 2.3.x   | yes       |" in security_doc
    assert "Hive is built around a local, file-backed substrate" in security_doc


def test_pull_request_template_enforces_slice_and_review_discipline():
    """The PR template should ask for blocker, validation, and review closure."""
    template = (REPO_ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md").read_text(encoding="utf-8")

    assert "## Blocker Removed" in template
    assert "## Why This Slice Is Mergeable" in template
    assert "## Validation" in template
    assert "## Review Discipline" in template
    assert "@claude review" in template
    assert "reactions alone did not count as completion" in template
    assert "post-merge `main` CI run" in template


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


def test_ci_workflow_proves_local_safe_podman_path():
    """CI should carry one real Podman-backed proof for the local-safe sandbox gate."""
    workflow = _load_yaml(".github/workflows/ci.yml")
    job = workflow["jobs"]["sandbox-local-safe-proof"]
    steps = job["steps"]

    assert job["runs-on"] == "ubuntu-latest"
    assert any(step.get("name") == "Verify rootless Podman availability" for step in steps)
    assert any(step.get("name") == "Verify Hive sees Podman as local-safe" for step in steps)
    assert any(
        "tests/test_local_safe_acceptance.py" in step.get("run", "")
        for step in steps
        if isinstance(step.get("run"), str)
    )


def test_repo_relies_on_managed_claude_review_instead_of_repo_local_workflow():
    """Claude review should come from Anthropic's managed app, not a repo-local workflow."""
    install_doc = (REPO_ROOT / "docs" / "INSTALL_CLAUDE_APP.md").read_text(encoding="utf-8")
    maintaining_doc = (REPO_ROOT / "docs" / "MAINTAINING.md").read_text(encoding="utf-8")
    agents_doc = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    claude_doc = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    skill_doc = (
        REPO_ROOT / ".agents" / "skills" / "hive-v23-execution-discipline" / "SKILL.md"
    ).read_text(encoding="utf-8")

    assert not (REPO_ROOT / ".github" / "workflows" / "claude.yml").exists()
    assert "managed Code Review" in install_doc
    assert "@claude review" in install_doc
    assert 'claude -p "/review <pr-number>"' in install_doc
    assert "does not ship a custom Claude GitHub Actions review workflow" in maintaining_doc
    assert "An `eyes` reaction alone is not completion." in install_doc
    assert "local Claude review is an acceptable primary or fallback path" in maintaining_doc
    assert 'claude -p "/review <pr-number>"' in maintaining_doc
    assert "Use the explicit scope-lock notes there as the current release truth" in maintaining_doc
    assert "/Users/bryanyoung/experiments/hive-orchestrator/.github/workflows/branch-hygiene.yml" not in maintaining_doc
    assert "An `eyes` reaction alone does not count as completion." in agents_doc
    assert "An `eyes` reaction alone does not count as completion." in claude_doc
    assert 'claude -p "/review <pr-number>"' in skill_doc
    assert "an `eyes` reaction or acknowledgement on the request comment is not completion" in skill_doc


def test_scheduled_uv_installers_use_setup_action():
    """Scheduled maintainer workflows should use the standard uv setup action."""
    ready_work = _load_yaml(".github/workflows/agent-assignment.yml")
    projection_sync = _load_yaml(".github/workflows/projection-sync.yml")

    ready_steps = ready_work["jobs"]["ready-work"]["steps"]
    projection_steps = projection_sync["jobs"]["projection-sync"]["steps"]

    assert any(step.get("uses") == "astral-sh/setup-uv@v7" for step in ready_steps)
    assert any(step.get("uses") == "astral-sh/setup-uv@v7" for step in projection_steps)

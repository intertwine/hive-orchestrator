"""Workflow guardrails for Claude GitHub automation."""

from __future__ import annotations

from pathlib import Path

import yaml


def _load_claude_workflow() -> dict:
    workflow_path = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "claude.yml"
    return yaml.safe_load(workflow_path.read_text(encoding="utf-8"))


def _workflow_triggers(workflow: dict) -> dict:
    return workflow.get("on", workflow.get(True, {}))


def _step_with(job: dict, name: str) -> dict:
    for step in job["steps"]:
        if step.get("name") == name:
            return step["with"]
    raise AssertionError(f"Missing workflow step: {name}")


def test_claude_workflows_discourage_raw_log_dump_comments():
    """Both Claude workflows should summarize logs instead of pasting them into comments."""
    workflow = _load_claude_workflow()
    response_prompt = _step_with(workflow["jobs"]["claude-response"], "Run Claude Code Action")["prompt"]
    review_prompt = _step_with(workflow["jobs"]["claude-review"], "Run Claude PR review")["prompt"]

    for prompt in (response_prompt, review_prompt):
        assert "Keep GitHub comments concise and actionable." in prompt
        assert "Never paste raw shell output, test logs, or long diffs" in prompt
        assert "Summarize command results in prose" in prompt
        assert "workflow or job URL for full logs" in prompt
    assert "Only publish the final GitHub comment or PR update" in response_prompt


def test_claude_workflow_reviews_draft_prs_and_uses_sticky_comments():
    """Draft PR review should stay enabled and mention replies should stay contained."""
    workflow = _load_claude_workflow()

    response_with = _step_with(workflow["jobs"]["claude-response"], "Run Claude Code Action")
    review_if = workflow["jobs"]["claude-review"]["if"]
    review_types = _workflow_triggers(workflow)["pull_request"]["types"]
    review_permissions = workflow["jobs"]["claude-review"]["permissions"]

    assert response_with["use_sticky_comment"] is True
    assert "!github.event.pull_request.draft" not in review_if
    assert "github.event_name == 'pull_request'" in review_if
    assert "ready_for_review" not in review_types
    assert review_permissions["id-token"] == "write"


def test_claude_review_workflow_only_advertises_supported_comment_tools():
    """The review job should not instruct Claude to use unavailable inline-comment tooling."""
    workflow = _load_claude_workflow()
    review_with = _step_with(workflow["jobs"]["claude-review"], "Run Claude PR review")
    review_prompt = review_with["prompt"]
    allowed_tools = review_with["claude_args"]

    assert "mcp__github_inline_comment__create_inline_comment" not in review_prompt
    assert "mcp__github_inline_comment__create_inline_comment" not in allowed_tools
    assert "gh pr comment" in review_prompt

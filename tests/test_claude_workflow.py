"""Workflow guardrails for Claude GitHub automation."""

from __future__ import annotations

from pathlib import Path

import yaml


def test_claude_workflows_discourage_raw_log_dump_comments():
    """Both Claude workflows should summarize logs instead of pasting them into comments."""
    workflow_path = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "claude.yml"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    response_prompt = workflow["jobs"]["claude-response"]["steps"][-1]["with"]["prompt"]
    review_prompt = workflow["jobs"]["claude-review"]["steps"][-1]["with"]["prompt"]

    for prompt in (response_prompt, review_prompt):
        assert "Keep GitHub comments concise and actionable." in prompt
        assert "Never paste raw shell output, test logs, or long diffs" in prompt
        assert "Summarize command results in prose" in prompt
        assert "workflow or job URL for full logs" in prompt
    assert "Only publish the final GitHub comment or PR update" in response_prompt

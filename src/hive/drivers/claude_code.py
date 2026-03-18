"""Claude Code harness driver."""

from __future__ import annotations

from src.hive.drivers.base import HarnessDriver


class ClaudeCodeDriver(HarnessDriver):
    """Driver that stages runs for Claude Code."""

    name = "claude-code"
    binary_names = ("claude", "claude-code")
    display_name = "Claude Code"
    cli_label = "Claude Code CLI"
    declared_launch_mode = "sdk"
    declared_session_persistence = "session"
    declared_event_stream = "structured_deltas"
    declared_approvals = ("command", "file", "network")
    declared_skills = "list"
    declared_subagents = "native"
    declared_native_sandbox = "policy"
    declared_artifacts = ("diff", "transcript", "plan", "review")
    declared_reroute_export = "transcript_plus_context"

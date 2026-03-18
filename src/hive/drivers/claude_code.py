"""Claude Code harness driver."""

from __future__ import annotations

from typing import Any

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

    def _probe_details(
        self,
        *,
        binary_name: str | None,
        binary_path: str | None,
    ) -> tuple[dict[str, Any], list[str], dict[str, str]]:
        if not binary_path:
            return {}, [], {}

        help_text = self._command_output("--help") or ""
        probed = {
            "binary_name": binary_name,
            "print_mode": "--print" in help_text or "-p," in help_text,
            "output_format_json": "--output-format" in help_text and "json" in help_text,
            "input_format_stream_json": "--input-format" in help_text
            and "stream-json" in help_text,
            "resume": "--resume" in help_text,
            "continue": "--continue" in help_text,
            "session_id": "--session-id" in help_text,
            "permission_mode": "--permission-mode" in help_text,
            "tools": "--tools" in help_text,
            "mcp_config": "--mcp-config" in help_text,
            "session_persistence_toggle": "--no-session-persistence" in help_text,
        }
        notes = []
        if binary_name == "claude":
            notes.append("Claude Code is currently detected through the `claude` executable.")
        if probed["resume"] and probed["session_id"]:
            notes.append(
                "Claude CLI exposes resume/session flags, which supports truthful session "
                "continuity claims while the Hive adapter remains staged."
            )
        evidence = {
            "claude_cli_surface": (
                "Claude CLI help exposes print/stream/resume/session/permission controls."
                if help_text
                else "Claude CLI help could not be read on this machine."
            ),
            "claude_binary": (
                "Hive normalizes the `claude` executable to the `claude-code` driver alias."
                if binary_name == "claude"
                else "Hive detected a `claude-code` executable directly."
            ),
        }
        return probed, notes, evidence

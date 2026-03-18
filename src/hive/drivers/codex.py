"""Codex harness driver."""

from __future__ import annotations

from src.hive.drivers.base import HarnessDriver


class CodexDriver(HarnessDriver):
    """Driver that stages runs for Codex."""

    name = "codex"
    binary_names = ("codex",)
    display_name = "Codex"
    cli_label = "Codex CLI"
    declared_launch_mode = "app_server"
    declared_session_persistence = "thread"
    declared_event_stream = "structured_deltas"
    declared_approvals = ("command", "file")
    declared_skills = "explicit_invoke"
    declared_subagents = "native"
    declared_native_sandbox = "policy"
    declared_artifacts = ("diff", "transcript", "plan")
    declared_reroute_export = "transcript_plus_context"

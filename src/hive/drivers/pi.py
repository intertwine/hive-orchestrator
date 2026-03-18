"""Pi harness driver."""

from __future__ import annotations

from src.hive.drivers.base import HarnessDriver


class PiDriver(HarnessDriver):
    """Driver that stages runs for Pi RPC integration."""

    name = "pi"
    binary_names = ("pi",)
    display_name = "Pi"
    cli_label = "Pi CLI"
    declared_launch_mode = "rpc"
    declared_session_persistence = "session"
    declared_event_stream = "structured_deltas"
    declared_approvals = ("command",)
    declared_skills = "list"
    declared_subagents = "none"
    declared_native_sandbox = "none"
    declared_artifacts = ("transcript", "plan")
    declared_reroute_export = "transcript_plus_context"

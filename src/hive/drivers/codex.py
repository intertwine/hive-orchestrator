"""Codex harness driver."""

from __future__ import annotations

from typing import Any

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

    def _probe_details(
        self,
        *,
        binary_name: str | None,
        binary_path: str | None,
    ) -> tuple[dict[str, Any], list[str], dict[str, str]]:
        if not binary_path:
            return {}, [], {}

        help_text = self._command_output("--help") or ""
        exec_help = self._command_output("exec", "--help") or ""
        app_server_help = self._command_output("app-server", "--help") or ""
        probed = {
            "binary_name": binary_name,
            "exec_available": "exec" in help_text,
            "app_server_available": "app-server" in help_text,
            "sandbox_cli_available": "sandbox" in help_text,
            "features_cli_available": "features" in help_text,
            "exec_json_output": "--json" in exec_help,
            "exec_output_schema": "--output-schema" in exec_help,
            "app_server_listen": "--listen" in app_server_help,
        }
        notes = []
        if probed["exec_available"]:
            notes.append("Codex CLI exposes `exec`, so batch fallback can be probed truthfully.")
        if probed["app_server_available"]:
            notes.append(
                "Codex CLI exposes `app-server`, but Hive still stages runs until the protocol "
                "adapter is implemented."
            )
        evidence = {
            "codex_exec": (
                "Codex CLI help exposes `exec` with structured output flags."
                if probed["exec_available"]
                else "Codex CLI help did not expose `exec` on this machine."
            ),
            "codex_app_server": (
                "Codex CLI help exposes `app-server`; the effective mode stays staged until Hive "
                "speaks that protocol."
                if probed["app_server_available"]
                else "Codex CLI help did not expose `app-server` on this machine."
            ),
        }
        return probed, notes, evidence

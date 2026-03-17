"""Claude Code harness driver."""

from __future__ import annotations

from src.hive.drivers.base import HarnessDriver


class ClaudeCodeDriver(HarnessDriver):
    """Driver that stages runs for Claude Code."""

    name = "claude-code"
    binary_names = ("claude", "claude-code")
    display_name = "Claude Code"
    cli_label = "Claude Code CLI"

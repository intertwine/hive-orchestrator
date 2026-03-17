"""Codex harness driver."""

from __future__ import annotations

from src.hive.drivers.base import HarnessDriver


class CodexDriver(HarnessDriver):
    """Driver that stages runs for Codex."""

    name = "codex"
    binary_names = ("codex",)
    display_name = "Codex"
    cli_label = "Codex CLI"

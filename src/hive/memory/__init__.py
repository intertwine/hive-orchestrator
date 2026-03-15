"""Observational memory helpers."""

from src.hive.memory.adapters import (
    claude_session_end,
    claude_session_start,
    codex_observe,
    codex_poll_latest,
)
from src.hive.memory.context import handoff_context, startup_context
from src.hive.memory.observe import observe
from src.hive.memory.reflect import reflect
from src.hive.memory.search import search

observe_project = observe
reflect_project = reflect
search_memory = search

__all__ = [
    "observe",
    "observe_project",
    "reflect",
    "reflect_project",
    "search",
    "search_memory",
    "startup_context",
    "handoff_context",
    "claude_session_start",
    "claude_session_end",
    "codex_observe",
    "codex_poll_latest",
]

"""Thin harness adapters for observational memory workflows."""

from __future__ import annotations

from pathlib import Path

from src.hive.memory.context import startup_context
from src.hive.memory.observe import observe
from src.hive.memory.reflect import reflect


def _reflect_payload(path: str | Path | None, *, scope: str) -> dict[str, str]:
    return {key: str(value) for key, value in reflect(path, scope=scope).items()}


def claude_session_start(
    path: str | Path | None,
    *,
    project_id: str,
    profile: str = "default",
    query: str | None = None,
    task_id: str | None = None,
) -> dict[str, object]:
    """Return startup context for a Claude Code session-start hook."""
    return startup_context(
        path,
        project_id=project_id,
        profile=profile,
        query=query,
        task_id=task_id,
    )


def claude_session_end(
    path: str | Path | None,
    *,
    transcript_path: str | Path,
    scope: str = "project",
) -> dict[str, object]:
    """Observe and reflect a Claude Code transcript at session end."""
    observation_path = observe(
        path,
        transcript_path=transcript_path,
        scope=scope,
        harness="claude",
    )
    return {
        "harness": "claude",
        "observation_path": str(observation_path),
        "paths": _reflect_payload(path, scope=scope),
    }


def codex_observe(
    path: str | Path | None,
    *,
    transcript_path: str | Path | None = None,
    note: str | None = None,
    scope: str = "project",
) -> dict[str, object]:
    """Observe and reflect explicit Codex memory input."""
    observation_path = observe(
        path,
        transcript_path=transcript_path,
        note=note,
        scope=scope,
        harness="codex",
    )
    return {
        "harness": "codex",
        "observation_path": str(observation_path),
        "paths": _reflect_payload(path, scope=scope),
    }


def codex_poll_latest(
    path: str | Path | None,
    *,
    transcripts_dir: str | Path,
    glob: str = "*.md",
    scope: str = "project",
) -> dict[str, object] | None:
    """Observe the latest matching Codex transcript from a poll/cron path."""
    directory = Path(transcripts_dir)
    if not directory.exists():
        return None
    candidates = sorted(file_path for file_path in directory.rglob(glob) if file_path.is_file())
    if not candidates:
        return None
    return codex_observe(path, transcript_path=candidates[-1], scope=scope)


__all__ = [
    "claude_session_end",
    "claude_session_start",
    "codex_observe",
    "codex_poll_latest",
]

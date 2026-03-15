"""Tests for thin memory harness adapters."""

from __future__ import annotations

from pathlib import Path

from src.hive.memory import (
    claude_session_end,
    claude_session_start,
    codex_observe,
    codex_poll_latest,
    observe_project,
    reflect_project,
)
from src.hive.migrate import migrate_v1_to_v2
from src.hive.store.projects import discover_projects


def test_claude_session_hooks_round_trip_context_and_observation(
    temp_hive_dir,
    temp_project,
):
    """Claude session helpers should use the startup and observe flows."""
    del temp_project
    migrate_v1_to_v2(temp_hive_dir)
    project = discover_projects(temp_hive_dir)[0]
    transcript = Path(temp_hive_dir) / "claude-session.md"
    transcript.write_text("Claude session transcript about amber-otter.", encoding="utf-8")

    startup = claude_session_start(
        temp_hive_dir,
        project_id=project.id,
        profile="light",
        query="amber-otter",
    )
    finished = claude_session_end(temp_hive_dir, transcript_path=transcript)

    assert startup["project_id"] == project.id
    assert finished["harness"] == "claude"
    assert Path(finished["observation_path"]).exists()
    assert Path(finished["paths"]["active"]).exists()
    archived = Path(temp_hive_dir) / ".hive" / "memory" / "transcripts" / "claude"
    assert list(archived.glob("*.md"))


def test_codex_observe_supports_explicit_notes_and_polling(
    temp_hive_dir,
    temp_project,
):
    """Codex adapters should support both direct notes and transcript polling."""
    del temp_project
    migrate_v1_to_v2(temp_hive_dir)
    observe_project(temp_hive_dir, note="baseline")
    reflect_project(temp_hive_dir)

    direct = codex_observe(temp_hive_dir, note="silver-heron codex note")
    transcripts_dir = Path(temp_hive_dir) / "codex-transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    first = transcripts_dir / "001.md"
    second = transcripts_dir / "002.md"
    first.write_text("old transcript", encoding="utf-8")
    second.write_text("latest silver-heron transcript", encoding="utf-8")
    polled = codex_poll_latest(temp_hive_dir, transcripts_dir=transcripts_dir)

    assert direct["harness"] == "codex"
    assert Path(direct["paths"]["profile"]).exists()
    assert polled is not None
    assert polled["harness"] == "codex"
    archived = Path(temp_hive_dir) / ".hive" / "memory" / "transcripts" / "codex"
    archived_files = list(archived.glob("*.md"))
    assert archived_files
    assert any("002.md" in file_path.name for file_path in archived_files)


def test_codex_poll_latest_returns_none_for_missing_transcript_dir(temp_hive_dir):
    """Polling should be a safe no-op when no transcript directory exists."""
    assert codex_poll_latest(temp_hive_dir, transcripts_dir=Path(temp_hive_dir) / "missing") is None

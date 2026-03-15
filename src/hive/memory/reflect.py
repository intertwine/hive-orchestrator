"""Memory reflection job."""

from __future__ import annotations

from pathlib import Path

from src.hive.store.layout import memory_scope_dir


def reflect(path: str | Path | None = None, *, scope: str = "project") -> dict[str, Path]:
    """Regenerate reflections, profile, and active memory docs."""
    directory = memory_scope_dir(path, scope=scope)
    directory.mkdir(parents=True, exist_ok=True)
    observations_path = directory / "observations.md"
    observations = (
        observations_path.read_text(encoding="utf-8") if observations_path.exists() else ""
    )
    lines = [line for line in observations.splitlines() if line.strip()]
    last_lines = lines[-10:]
    reflections_path = directory / "reflections.md"
    profile_path = directory / "profile.md"
    active_path = directory / "active.md"
    reflections_path.write_text(
        "# Reflections\n\n" + ("\n".join(last_lines) if last_lines else "No reflections yet.\n"),
        encoding="utf-8",
    )
    profile_path.write_text(
        "# Profile\n\n" + ("\n".join(last_lines[:5]) if last_lines else "No profile yet.\n"),
        encoding="utf-8",
    )
    active_path.write_text(
        "# Active Context\n\n"
        + ("\n".join(last_lines[-5:]) if last_lines else "No active context yet.\n"),
        encoding="utf-8",
    )
    return {
        "reflections": reflections_path,
        "profile": profile_path,
        "active": active_path,
    }

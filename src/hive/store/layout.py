"""Repository layout helpers."""

from __future__ import annotations

import os
from pathlib import Path


def base_path(path: str | Path | None = None) -> Path:
    """Resolve the repo base path."""
    if path is None:
        return Path.cwd()
    return Path(path).resolve()


def hive_dir(path: str | Path | None = None) -> Path:
    """Return the .hive root."""
    return base_path(path) / ".hive"


def memory_dir(path: str | Path | None = None) -> Path:
    """Return the repo-local memory root."""
    return hive_dir(path) / "memory"


def tasks_dir(path: str | Path | None = None) -> Path:
    """Return the task directory."""
    return hive_dir(path) / "tasks"


def runs_dir(path: str | Path | None = None) -> Path:
    """Return the runs directory."""
    return hive_dir(path) / "runs"


def memory_project_dir(path: str | Path | None = None) -> Path:
    """Return the project-memory directory."""
    return memory_dir(path) / "project"


def memory_transcripts_dir(path: str | Path | None = None) -> Path:
    """Return the transcript import directory."""
    return memory_dir(path) / "transcripts"


def global_memory_dir() -> Path:
    """Return the optional user-global memory directory."""
    configured = os.getenv("HIVE_GLOBAL_MEMORY_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    xdg_data_home = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return xdg_data_home / "hive" / "global-memory"


def memory_scope_dir(path: str | Path | None = None, *, scope: str = "project") -> Path:
    """Resolve a memory directory for a supported scope."""
    if scope == "project":
        return memory_project_dir(path)
    if scope == "global":
        return global_memory_dir()
    raise ValueError(f"Unsupported memory scope: {scope}")


def memory_harness_dir(path: str | Path | None = None, *, harness: str) -> Path:
    """Return the transcript import directory for a harness."""
    return memory_transcripts_dir(path) / harness


def events_dir(path: str | Path | None = None) -> Path:
    """Return the events directory."""
    return hive_dir(path) / "events"


def cache_dir(path: str | Path | None = None) -> Path:
    """Return the cache directory."""
    return hive_dir(path) / "cache"


def worktrees_dir(path: str | Path | None = None) -> Path:
    """Return the worktrees directory."""
    return hive_dir(path) / "worktrees"


def ensure_layout(path: str | Path | None = None) -> dict[str, Path]:
    """Create the minimum Hive 2.0 directory layout."""
    root = hive_dir(path)
    directories = {
        "root": root,
        "memory": memory_dir(path),
        "tasks": tasks_dir(path),
        "runs": runs_dir(path),
        "events": events_dir(path),
        "cache": cache_dir(path),
        "worktrees": worktrees_dir(path),
        "memory_project": memory_project_dir(path),
        "memory_transcripts": memory_transcripts_dir(path),
    }
    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)
    return directories

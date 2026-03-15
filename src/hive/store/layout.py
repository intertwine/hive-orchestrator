"""Repository layout helpers."""

from __future__ import annotations

from pathlib import Path


def base_path(path: str | Path | None = None) -> Path:
    """Resolve the repo base path."""
    if path is None:
        return Path.cwd()
    return Path(path).resolve()


def hive_dir(path: str | Path | None = None) -> Path:
    """Return the .hive root."""
    return base_path(path) / ".hive"


def tasks_dir(path: str | Path | None = None) -> Path:
    """Return the task directory."""
    return hive_dir(path) / "tasks"


def runs_dir(path: str | Path | None = None) -> Path:
    """Return the runs directory."""
    return hive_dir(path) / "runs"


def memory_project_dir(path: str | Path | None = None) -> Path:
    """Return the project-memory directory."""
    return hive_dir(path) / "memory" / "project"


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
        "tasks": tasks_dir(path),
        "runs": runs_dir(path),
        "events": events_dir(path),
        "cache": cache_dir(path),
        "worktrees": worktrees_dir(path),
        "memory_project": memory_project_dir(path),
    }
    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)
    return directories

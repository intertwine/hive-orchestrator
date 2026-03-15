"""Repository layout helpers for Hive v2."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.hive.common import ensure_directory


@dataclass(frozen=True)
class HivePaths:
    """Convenience accessors for the repository layout."""

    root: Path

    @property
    def hive_dir(self) -> Path:
        return self.root / ".hive"

    @property
    def tasks_dir(self) -> Path:
        return self.hive_dir / "tasks"

    @property
    def runs_dir(self) -> Path:
        return self.hive_dir / "runs"

    @property
    def events_dir(self) -> Path:
        return self.hive_dir / "events"

    @property
    def cache_dir(self) -> Path:
        return self.hive_dir / "cache"

    @property
    def cache_db(self) -> Path:
        return self.cache_dir / "index.sqlite"

    @property
    def memory_dir(self) -> Path:
        return self.hive_dir / "memory"

    @property
    def project_memory_dir(self) -> Path:
        return self.memory_dir / "project"

    @property
    def transcripts_dir(self) -> Path:
        return self.memory_dir / "transcripts"

    @property
    def worktrees_dir(self) -> Path:
        return self.hive_dir / "worktrees"

    @property
    def global_file(self) -> Path:
        return self.root / "GLOBAL.md"

    @property
    def agents_file(self) -> Path:
        return self.root / "AGENTS.md"

    @property
    def projects_dir(self) -> Path:
        return self.root / "projects"


def get_paths(base_path: str | Path | None = None) -> HivePaths:
    """Resolve the Hive repository layout."""
    root = Path(base_path or ".").resolve()
    return HivePaths(root=root)


def ensure_hive_layout(paths: HivePaths) -> None:
    """Create the core Hive v2 directory layout."""
    for directory in (
        paths.hive_dir,
        paths.tasks_dir,
        paths.runs_dir,
        paths.events_dir,
        paths.cache_dir,
        paths.project_memory_dir,
        paths.transcripts_dir,
        paths.worktrees_dir,
    ):
        ensure_directory(directory)

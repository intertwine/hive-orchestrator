"""Repository layout helpers."""

from __future__ import annotations

import os
from pathlib import Path


def _default_hive_readme() -> str:
    return """# Hive 2.0 Substrate

This directory holds Hive's canonical machine state.

- `.hive/tasks/*.md` contains task records.
- `.hive/runs/*` stores run artifacts and evaluator outputs.
- `.hive/memory/` stores project-local memory docs.
- `.hive/events/*.jsonl` stores the append-only audit log.
- `.hive/cache/` is derived and should stay out of Git.
- `.hive/worktrees/` is scratch space for local run worktrees.
"""


def _ensure_text_file(path: Path, content: str) -> bool:
    if path.exists():
        return False
    path.write_text(content, encoding="utf-8")
    return True


def _ensure_gitignore_entries(root: Path) -> bool:
    gitignore_path = root / ".gitignore"
    existing = gitignore_path.read_text(encoding="utf-8") if gitignore_path.exists() else ""
    required_entries = [
        ".hive/cache/",
        ".hive/worktrees/",
    ]
    missing = [entry for entry in required_entries if entry not in existing.splitlines()]
    if not missing:
        return False

    lines = existing.splitlines()
    if lines and lines[-1].strip():
        lines.append("")
    if missing:
        lines.append("# Hive derived state")
        lines.extend(missing)
    gitignore_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return True


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
    workspace_root = base_path(path)
    root = hive_dir(workspace_root)
    directories = {
        "workspace": workspace_root,
        "root": root,
        "projects": workspace_root / "projects",
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


def bootstrap_workspace(path: str | Path | None = None) -> dict[str, object]:
    """Create the base layout and bootstrap the root human-facing files."""
    from src.hive.projections.agents_md import default_agents_md
    from src.hive.projections.global_md import default_global_md

    directories = ensure_layout(path)
    workspace_root = Path(directories["workspace"])

    created_files: list[str] = []
    updated_files: list[str] = []
    gitignore_path = workspace_root / ".gitignore"
    gitignore_existed = gitignore_path.exists()

    if _ensure_text_file(workspace_root / ".hive" / "README.md", _default_hive_readme()):
        created_files.append(".hive/README.md")
    if _ensure_text_file(workspace_root / "GLOBAL.md", default_global_md()):
        created_files.append("GLOBAL.md")
    if _ensure_text_file(workspace_root / "AGENTS.md", default_agents_md()):
        created_files.append("AGENTS.md")
    if _ensure_gitignore_entries(workspace_root):
        if gitignore_existed:
            updated_files.append(".gitignore")
        else:
            created_files.append(".gitignore")

    return {
        "layout": directories,
        "created_files": created_files,
        "updated_files": updated_files,
    }

"""Accept or reject proposed memory synthesis files."""

from __future__ import annotations

from pathlib import Path

from src.hive.memory.common import project_memory_scope_dir
from src.hive.store.layout import memory_scope_dir


def _memory_dir(
    path: str | Path | None,
    *,
    scope: str,
    project_id: str | None,
) -> Path:
    if scope == "project":
        return project_memory_scope_dir(path, project_id=project_id)
    return memory_scope_dir(path, scope=scope)


def accept_memory_review(
    path: str | Path | None,
    *,
    scope: str = "project",
    project_id: str | None = None,
) -> dict[str, str]:
    """Promote proposed memory docs into the live profile/active/reflections files."""
    directory = _memory_dir(path, scope=scope, project_id=project_id)
    promoted: dict[str, str] = {}
    for stem in ("reflections", "profile", "active"):
        proposed = directory / f"{stem}.proposed.md"
        live = directory / f"{stem}.md"
        if proposed.exists():
            live.write_text(proposed.read_text(encoding="utf-8"), encoding="utf-8")
            proposed.unlink()
            promoted[stem] = str(live)
    review = directory / "memory-review.md"
    if review.exists():
        review.unlink()
    if not promoted:
        raise FileNotFoundError("No proposed memory review is waiting to be accepted.")
    return promoted


def reject_memory_review(
    path: str | Path | None,
    *,
    scope: str = "project",
    project_id: str | None = None,
) -> dict[str, str]:
    """Discard proposed memory review files."""
    directory = _memory_dir(path, scope=scope, project_id=project_id)
    removed: dict[str, str] = {}
    for stem in ("reflections", "profile", "active"):
        proposed = directory / f"{stem}.proposed.md"
        if proposed.exists():
            removed[stem] = str(proposed)
            proposed.unlink()
    review = directory / "memory-review.md"
    if review.exists():
        removed["review"] = str(review)
        review.unlink()
    if not removed:
        raise FileNotFoundError("No proposed memory review is waiting to be rejected.")
    return removed

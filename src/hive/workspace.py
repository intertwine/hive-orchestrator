"""Workspace-level sync helpers for projections and derived state."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import time

try:  # pragma: no cover - available on macOS/Linux, guarded for portability.
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None  # type: ignore[assignment]

from src.hive.projections.agency_md import sync_agency_md
from src.hive.projections.agents_md import sync_agents_md
from src.hive.projections.global_md import sync_global_md
from src.hive.store.cache import rebuild_cache
from src.hive.store.layout import cache_dir


class WorkspaceBusyError(RuntimeError):
    """Raised when a workspace refresh stays busy past the allowed wait."""


@contextmanager
def _workspace_lock(lock_path: Path, *, timeout_seconds: float = 15.0):
    """Serialize projection and cache refreshes across processes."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a+", encoding="utf-8") as handle:
        if fcntl is None:  # pragma: no cover - fallback for non-posix environments.
            yield
            return
        deadline = time.monotonic() + timeout_seconds
        while True:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError as exc:
                if time.monotonic() >= deadline:
                    raise WorkspaceBusyError(
                        "Hive is already refreshing this workspace. "
                        "Wait a moment, then retry the command."
                    ) from exc
                time.sleep(0.05)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def sync_workspace(path: str | Path | None = None) -> None:
    """Refresh projections and the derived cache as one serialized operation."""
    root = Path(path or Path.cwd()).resolve()
    lock_path = cache_dir(root) / "workspace.lock"
    with _workspace_lock(lock_path):
        sync_global_md(root)
        sync_agency_md(root)
        sync_agents_md(root)
        rebuild_cache(root)

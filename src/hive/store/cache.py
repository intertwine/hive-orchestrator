"""Derived SQLite cache builder."""

from __future__ import annotations

from contextlib import contextmanager
import os
from importlib.resources import files
import sqlite3
import time
from pathlib import Path

try:  # pragma: no cover - fcntl is always available on macOS/Linux, but keep import-safe.
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None  # type: ignore[assignment]

from src.hive.store.cache_index import (
    _memory_scope_parts as _memory_scope_parts_impl,
    populate_cache_database,
)
from src.hive.store.layout import cache_dir


class CacheBusyError(RuntimeError):
    """Raised when the derived cache stays locked for too long."""


def _schema_sql() -> str:
    """Load the SQLite schema used for the derived cache."""
    return files("src.hive.store").joinpath("SCHEMA.sql").read_text(encoding="utf-8")


def _memory_scope_parts(relative_path: Path) -> tuple[str, str]:
    """Return the memory scope and key for a relative memory path."""
    return _memory_scope_parts_impl(relative_path)


@contextmanager
def _cache_lock(lock_path: Path, *, timeout_seconds: float = 15.0):
    """Serialize cache rebuilds across processes with a simple file lock."""
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
                    raise CacheBusyError(
                        "Hive is already rebuilding the cache for this workspace. "
                        "Wait a moment, then retry the command."
                    ) from exc
                time.sleep(0.05)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def rebuild_cache(path: str | Path | None = None) -> Path:
    """Rebuild the derived SQLite cache from canonical files."""
    root = Path(path or Path.cwd())
    target_dir = cache_dir(root)
    target_dir.mkdir(parents=True, exist_ok=True)
    db_path = target_dir / "index.sqlite"
    lock_path = target_dir / "index.lock"

    with _cache_lock(lock_path):
        temp_db_path = target_dir / f"index.sqlite.tmp.{os.getpid()}.{time.time_ns()}"
        if temp_db_path.exists():
            temp_db_path.unlink()

        connection = None
        try:
            connection = sqlite3.connect(temp_db_path)
            connection.executescript(_schema_sql())
            search_docs = populate_cache_database(root, connection)
            connection.commit()
            connection.close()
            connection = None
            os.replace(temp_db_path, db_path)
        finally:
            if connection is not None:
                connection.close()
            if temp_db_path.exists():
                temp_db_path.unlink()

        # Build the optional dense vector index under the same lock so
        # concurrent rebuilds cannot overwrite the LanceDB table mid-write.
        try:
            from src.hive.retrieval.dense import (
                DenseDoc,
                build_dense_index,
                is_dense_available,
            )

            if (
                is_dense_available()
                and search_docs
                and not os.environ.get("HIVE_SKIP_DENSE_INDEX")
            ):
                dense_docs = [
                    DenseDoc(
                        doc_id=f"{doc_type}:{file_path}",
                        doc_type=doc_type,
                        title=title,
                        body=body,
                    )
                    for doc_type, file_path, title, body, _metadata in search_docs
                ]
                build_dense_index(target_dir, dense_docs)
        except Exception:  # pylint: disable=broad-except
            pass  # Dense index failure must never block search

    return db_path

"""Clock helpers for Hive 2.0."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    """Return the current UTC timestamp as an ISO-8601 string."""
    return utc_now().isoformat().replace("+00:00", "Z")

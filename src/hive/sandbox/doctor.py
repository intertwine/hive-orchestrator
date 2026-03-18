"""Doctor helpers for sandbox backends."""

from __future__ import annotations

from typing import Any

from src.hive.sandbox.registry import iter_backend_probes


def sandbox_doctor(backend: str | None = None) -> dict[str, Any]:
    """Return truthful sandbox probe data."""
    probes = iter_backend_probes([backend] if backend else None)
    return {
        "ok": True,
        "backends": [probe.to_dict() for probe in probes],
    }


__all__ = ["sandbox_doctor"]

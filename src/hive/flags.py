"""Feature flags for staged v2.3 rollout work."""

from __future__ import annotations

import os


def _env_flag(name: str, *, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def feature_flags() -> dict[str, bool]:
    """Return the normalized v2.3 rollout flags."""
    return {
        "hive.runtime_v2": _env_flag("HIVE_RUNTIME_V2", default=True),
        "hive.sandbox_v2": _env_flag("HIVE_SANDBOX_V2", default=True),
        "hive.hybrid_retrieval_v2": _env_flag("HIVE_HYBRID_RETRIEVAL_V2", default=True),
        "hive.campaigns_v2": _env_flag("HIVE_CAMPAIGNS_V2", default=True),
    }


__all__ = ["feature_flags"]

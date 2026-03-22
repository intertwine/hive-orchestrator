"""Driver registry and lookup helpers."""

from __future__ import annotations

from src.hive.constants import DRIVER_ORDER
from src.hive.drivers.base import Driver
from src.hive.drivers.claude_sdk import ClaudeSDKDriver
from src.hive.drivers.codex import CodexDriver
from src.hive.drivers.local import LocalDriver
from src.hive.drivers.manual import ManualDriver


_DRIVERS: dict[str, Driver] = {
    "local": LocalDriver(),
    "manual": ManualDriver(),
    "codex": CodexDriver(),
    "claude": ClaudeSDKDriver(),
}
_ALIASES = {
    "claude-code": "claude",
}


def normalize_driver_name(name: str | None) -> str | None:
    """Normalize driver names while preserving unknown values for caller-level handling."""
    if name is None:
        return None
    normalized = name.strip().lower()
    if not normalized:
        return None
    return _ALIASES.get(normalized, normalized)


def list_drivers() -> list[Driver]:
    """Return all registered drivers in stable order."""
    return [_DRIVERS[name] for name in DRIVER_ORDER]


def get_driver(name: str) -> Driver:
    """Return a named driver or fail with a product-level error."""
    normalized = normalize_driver_name(name)
    try:
        return _DRIVERS[normalized]
    except KeyError as exc:
        supported = ", ".join(sorted(set(_DRIVERS) | set(_ALIASES)))
        raise ValueError(f"Unsupported driver: {name}. Supported drivers: {supported}") from exc

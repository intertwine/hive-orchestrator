"""Driver registry and lookup helpers."""

from __future__ import annotations

from src.hive.constants import DRIVER_ORDER
from src.hive.drivers.base import Driver
from src.hive.drivers.claude_code import ClaudeCodeDriver
from src.hive.drivers.codex import CodexDriver
from src.hive.drivers.local import LocalDriver
from src.hive.drivers.manual import ManualDriver
from src.hive.drivers.pi import PiDriver


_DRIVERS: dict[str, Driver] = {
    "local": LocalDriver(),
    "manual": ManualDriver(),
    "codex": CodexDriver(),
    "claude-code": ClaudeCodeDriver(),
    "pi": PiDriver(),
}
_ALIASES = {
    "claude": "claude-code",
}


def list_drivers() -> list[Driver]:
    """Return all registered drivers in stable order."""
    return [_DRIVERS[name] for name in DRIVER_ORDER]


def get_driver(name: str) -> Driver:
    """Return a named driver or fail with a product-level error."""
    normalized = name.strip().lower()
    normalized = _ALIASES.get(normalized, normalized)
    try:
        return _DRIVERS[normalized]
    except KeyError as exc:
        supported = ", ".join(sorted(_DRIVERS))
        raise ValueError(f"Unsupported driver: {name}. Supported drivers: {supported}") from exc

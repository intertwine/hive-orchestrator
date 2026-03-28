"""Integration registry for v2.4 adapters, parallel to the driver registry."""

from __future__ import annotations

from typing import Any

from src.hive.integrations.base import AdapterBase


_INTEGRATIONS: dict[str, AdapterBase] = {}
_BOOTSTRAPPED = False


def _bootstrap_bundled() -> None:
    """Auto-register the bundled dummy adapters on first access."""
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return
    _BOOTSTRAPPED = True
    from src.hive.integrations.dummy_gateway import DummyGatewayAdapter
    from src.hive.integrations.dummy_worker import DummyWorkerAdapter

    _INTEGRATIONS.setdefault("dummy-worker", DummyWorkerAdapter())
    _INTEGRATIONS.setdefault("dummy-gateway", DummyGatewayAdapter())


def register_integration(name: str, adapter: AdapterBase) -> None:
    """Register a v2.4 adapter integration."""
    _INTEGRATIONS[name] = adapter


def unregister_integration(name: str) -> None:
    """Remove a registered integration (mainly for testing)."""
    _INTEGRATIONS.pop(name, None)


def list_integrations() -> list[AdapterBase]:
    """Return all registered v2.4 adapters in insertion order."""
    _bootstrap_bundled()
    return list(_INTEGRATIONS.values())


def get_integration(name: str) -> AdapterBase:
    """Return a named integration or raise ValueError."""
    _bootstrap_bundled()
    try:
        return _INTEGRATIONS[name]
    except KeyError as exc:
        available = ", ".join(sorted(_INTEGRATIONS)) or "(none)"
        raise ValueError(
            f"Unknown integration: {name!r}. Registered: {available}"
        ) from exc


def list_all_backends() -> list[dict[str, Any]]:
    """Unified listing of legacy drivers and v2.4 integrations.

    Each entry includes an ``adapter_type`` discriminator:
    ``"legacy_driver"``, ``"worker_session"``, or ``"delegate_gateway"``.
    """
    _bootstrap_bundled()
    from src.hive.drivers.registry import list_drivers

    entries: list[dict[str, Any]] = []

    for driver in list_drivers():
        info = driver.probe()
        entry = info.to_dict()
        entry["adapter_type"] = "legacy_driver"
        entries.append(entry)

    for adapter in _INTEGRATIONS.values():
        info = adapter.probe()
        entry = info.to_dict()
        entry["adapter_type"] = str(adapter.adapter_family)
        entries.append(entry)

    return entries


__all__ = [
    "get_integration",
    "list_all_backends",
    "list_integrations",
    "register_integration",
    "unregister_integration",
]

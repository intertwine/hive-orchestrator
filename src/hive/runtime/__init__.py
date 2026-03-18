"""v2.3 runtime scaffolding exports."""

from __future__ import annotations

from typing import Any

# pylint: disable=import-outside-toplevel

from src.hive.runtime.approvals import ApprovalRequest
from src.hive.runtime.capabilities import CapabilitySnapshot, CapabilitySurface, capability_surface
from src.hive.runtime.events import RUNTIME_EVENT_TYPES
from src.hive.runtime.runpack import (
    SandboxPolicy,
    default_sandbox_policy,
    runtime_manifest,
    sync_runtime_status_artifacts,
    write_runtime_scaffold,
)

__all__ = [
    "ApprovalRequest",
    "CapabilitySnapshot",
    "CapabilitySurface",
    "RUNTIME_EVENT_TYPES",
    "SandboxPolicy",
    "capability_surface",
    "default_sandbox_policy",
    "list_approvals",
    "pending_approvals",
    "request_approval",
    "resolve_approval",
    "resolve_pending_approvals",
    "runtime_manifest",
    "sync_runtime_status_artifacts",
    "write_runtime_scaffold",
]


def list_approvals(*args: Any, **kwargs: Any):
    """Lazily load approval listing helpers to avoid package import cycles."""
    from src.hive.runtime.approvals import list_approvals as _list_approvals

    return _list_approvals(*args, **kwargs)


def pending_approvals(*args: Any, **kwargs: Any):
    """Lazily load pending approval helpers to avoid package import cycles."""
    from src.hive.runtime.approvals import pending_approvals as _pending_approvals

    return _pending_approvals(*args, **kwargs)


def request_approval(*args: Any, **kwargs: Any):
    """Lazily load approval creation helpers to avoid package import cycles."""
    from src.hive.runtime.approvals import request_approval as _request_approval

    return _request_approval(*args, **kwargs)


def resolve_approval(*args: Any, **kwargs: Any):
    """Lazily load approval resolution helpers to avoid package import cycles."""
    from src.hive.runtime.approvals import resolve_approval as _resolve_approval

    return _resolve_approval(*args, **kwargs)


def resolve_pending_approvals(*args: Any, **kwargs: Any):
    """Lazily load bulk approval resolution helpers to avoid package import cycles."""
    from src.hive.runtime.approvals import resolve_pending_approvals as _resolve_pending_approvals

    return _resolve_pending_approvals(*args, **kwargs)

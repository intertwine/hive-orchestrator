"""Normalized v2.3 runtime event vocabulary."""

from __future__ import annotations


RUNTIME_EVENT_TYPES = (
    "run.created",
    "run.prepared",
    "driver.probed",
    "sandbox.selected",
    "driver.launched",
    "driver.attached",
    "driver.status",
    "driver.output.delta",
    "plan.updated",
    "diff.updated",
    "approval.requested",
    "approval.resolved",
    "steer.requested",
    "steer.applied",
    "interrupt.requested",
    "interrupt.applied",
    "artifact.collected",
    "eval.started",
    "eval.completed",
    "promotion.accepted",
    "promotion.escalated",
    "promotion.rejected",
    "run.completed",
)


__all__ = ["RUNTIME_EVENT_TYPES"]

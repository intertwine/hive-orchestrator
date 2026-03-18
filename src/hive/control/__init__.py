"""Agent-first portfolio control helpers for Hive."""

from __future__ import annotations

from typing import Any

# pylint: disable=import-outside-toplevel

__all__ = [
    "campaign_status",
    "create_campaign_flow",
    "finish_run_flow",
    "generate_brief",
    "portfolio_status",
    "recommend_next_task",
    "steer_project",
    "tick_campaign",
    "tick_portfolio",
    "work_on_task",
]


def campaign_status(*args: Any, **kwargs: Any):
    """Lazily load campaign status helpers to avoid package import cycles."""
    from .campaigns import campaign_status as _campaign_status

    return _campaign_status(*args, **kwargs)


def create_campaign_flow(*args: Any, **kwargs: Any):
    """Lazily load campaign creation helpers to avoid package import cycles."""
    from .campaigns import create_campaign_flow as _create_campaign_flow

    return _create_campaign_flow(*args, **kwargs)


def generate_brief(*args: Any, **kwargs: Any):
    """Lazily load brief generation helpers to avoid package import cycles."""
    from .campaigns import generate_brief as _generate_brief

    return _generate_brief(*args, **kwargs)


def tick_campaign(*args: Any, **kwargs: Any):
    """Lazily load campaign ticking helpers to avoid package import cycles."""
    from .campaigns import tick_campaign as _tick_campaign

    return _tick_campaign(*args, **kwargs)


def finish_run_flow(*args: Any, **kwargs: Any):
    """Lazily load finish helpers to avoid package import cycles."""
    from .portfolio import finish_run_flow as _finish_run_flow

    return _finish_run_flow(*args, **kwargs)


def portfolio_status(*args: Any, **kwargs: Any):
    """Lazily load portfolio status helpers to avoid package import cycles."""
    from .portfolio import portfolio_status as _portfolio_status

    return _portfolio_status(*args, **kwargs)


def recommend_next_task(*args: Any, **kwargs: Any):
    """Lazily load recommendation helpers to avoid package import cycles."""
    from .portfolio import recommend_next_task as _recommend_next_task

    return _recommend_next_task(*args, **kwargs)


def steer_project(*args: Any, **kwargs: Any):
    """Lazily load project steering helpers to avoid package import cycles."""
    from .portfolio import steer_project as _steer_project

    return _steer_project(*args, **kwargs)


def tick_portfolio(*args: Any, **kwargs: Any):
    """Lazily load portfolio ticking helpers to avoid package import cycles."""
    from .portfolio import tick_portfolio as _tick_portfolio

    return _tick_portfolio(*args, **kwargs)


def work_on_task(*args: Any, **kwargs: Any):
    """Lazily load task-start helpers to avoid package import cycles."""
    from .portfolio import work_on_task as _work_on_task

    return _work_on_task(*args, **kwargs)

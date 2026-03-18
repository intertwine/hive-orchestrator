"""Campaign model for Hive 2.2."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.hive.clock import utc_now_iso


@dataclass
class CampaignRecord:
    """Canonical one-file-per-campaign record."""

    id: str
    title: str
    goal: str
    project_ids: list[str] = field(default_factory=list)
    status: str = "active"
    campaign_type: str = "delivery"
    driver: str = "local"
    model: str | None = None
    sandbox_profile: str | None = None
    cadence: str = "daily"
    brief_cadence: str = "daily"
    max_active_runs: int = 1
    lane_quotas: dict[str, int] = field(default_factory=dict)
    budget_policy: dict[str, Any] = field(default_factory=dict)
    escalation_policy: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    last_tick_at: str | None = None
    next_tick_at: str | None = None
    notes_md: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    path: Path | None = None

    def to_frontmatter(self) -> dict[str, Any]:
        """Serialize to markdown frontmatter."""
        payload = dict(self.metadata)
        payload.update(
            {
                "id": self.id,
                "title": self.title,
                "goal": self.goal,
                "project_ids": self.project_ids,
                "status": self.status,
                "type": self.campaign_type,
                "driver": self.driver,
                "model": self.model,
                "sandbox_profile": self.sandbox_profile,
                "cadence": self.cadence,
                "brief_cadence": self.brief_cadence,
                "max_active_runs": self.max_active_runs,
                "lane_quotas": self.lane_quotas,
                "budget_policy": self.budget_policy,
                "escalation_policy": self.escalation_policy,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
                "last_tick_at": self.last_tick_at,
                "next_tick_at": self.next_tick_at,
            }
        )
        return payload

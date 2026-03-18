"""Campaign storage and ticking helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, TypedDict

from src.hive.clock import utc_now_iso
from src.hive.ids import new_id
from src.hive.models.campaign import CampaignRecord
from src.hive.store.layout import briefs_dir, campaigns_dir
from src.security import safe_dump_agency_md, safe_load_agency_md

CAMPAIGN_TYPES = ("delivery", "research", "maintenance", "review")
CAMPAIGN_LANES = ("exploit", "explore", "review", "maintenance")
DEFAULT_LANE_QUOTAS = {
    "delivery": {"exploit": 70, "explore": 10, "review": 20, "maintenance": 0},
    "research": {"exploit": 40, "explore": 40, "review": 20, "maintenance": 0},
    "maintenance": {"exploit": 20, "explore": 0, "review": 20, "maintenance": 60},
    "review": {"exploit": 10, "explore": 0, "review": 80, "maintenance": 10},
}
DEFAULT_BUDGET_POLICY = {
    "delivery": {"max_cost_usd": 2.0, "max_tokens": 20000},
    "research": {"max_cost_usd": 3.0, "max_tokens": 30000},
    "maintenance": {"max_cost_usd": 1.0, "max_tokens": 12000},
    "review": {"max_cost_usd": 1.5, "max_tokens": 16000},
}
DEFAULT_ESCALATION_POLICY = {
    "delivery": {"on_budget_threshold": "review", "on_eval_reject": "review"},
    "research": {"on_budget_threshold": "pause", "on_eval_reject": "review"},
    "maintenance": {"on_budget_threshold": "pause", "on_eval_reject": "review"},
    "review": {"on_budget_threshold": "review", "on_eval_reject": "review"},
}

_CAMPAIGN_OPTION_KEYS = {
    "campaign_type",
    "driver",
    "model",
    "sandbox_profile",
    "cadence",
    "brief_cadence",
    "max_active_runs",
    "lane_quotas",
    "budget_policy",
    "escalation_policy",
    "notes_md",
}


class _CampaignRequest(TypedDict):
    title: str
    goal: str
    project_ids: list[str]
    campaign_type: str
    driver: str
    model: str | None
    sandbox_profile: str | None
    cadence: str
    brief_cadence: str
    max_active_runs: int
    lane_quotas: dict[str, int]
    budget_policy: dict[str, Any]
    escalation_policy: dict[str, Any]
    notes_md: str


def default_lane_quotas(campaign_type: str) -> dict[str, int]:
    """Return the normalized default lane quotas for a campaign type."""
    normalized_type = campaign_type if campaign_type in DEFAULT_LANE_QUOTAS else "delivery"
    return dict(DEFAULT_LANE_QUOTAS[normalized_type])


def _default_budget_policy(campaign_type: str) -> dict[str, Any]:
    normalized_type = campaign_type if campaign_type in DEFAULT_BUDGET_POLICY else "delivery"
    return dict(DEFAULT_BUDGET_POLICY[normalized_type])


def _default_escalation_policy(campaign_type: str) -> dict[str, Any]:
    normalized_type = (
        campaign_type if campaign_type in DEFAULT_ESCALATION_POLICY else "delivery"
    )
    return dict(DEFAULT_ESCALATION_POLICY[normalized_type])


def _normalized_campaign_type(value: object) -> str:
    normalized = str(value or "delivery").strip().lower()
    return normalized if normalized in CAMPAIGN_TYPES else "delivery"


def _normalized_lane_quotas(
    value: object,
    *,
    campaign_type: str,
) -> dict[str, int]:
    quotas = default_lane_quotas(campaign_type)
    if isinstance(value, dict):
        for lane in CAMPAIGN_LANES:
            if lane in value:
                quotas[lane] = max(0, int(value.get(lane) or 0))
    return quotas


def _campaign_body(goal: str, notes_md: str = "") -> str:
    notes = (
        notes_md.strip()
        or "Use this space for operator notes, constraints, and campaign updates."
    )
    return f"""# Goal

{goal.strip()}

## Notes

{notes}
"""


def _campaign_path(path: str | Path | None, campaign_id: str) -> Path:
    return campaigns_dir(path) / f"campaign_{campaign_id}.md"


def campaign_artifacts_dir(path: str | Path | None, campaign_id: str) -> Path:
    """Return the artifact directory for one campaign."""
    return campaigns_dir(path) / "artifacts" / campaign_id


def _parse_campaign(path: Path) -> CampaignRecord:
    parsed = safe_load_agency_md(path)
    metadata = dict(parsed.metadata)
    campaign_type = _normalized_campaign_type(metadata.get("type"))
    return CampaignRecord(
        id=str(metadata.get("id") or path.stem.removeprefix("campaign_")),
        title=str(metadata.get("title") or path.stem),
        goal=str(metadata.get("goal") or "").strip(),
        project_ids=[str(value) for value in metadata.get("project_ids", [])],
        status=str(metadata.get("status") or "active"),
        campaign_type=campaign_type,
        driver=str(metadata.get("driver") or "local"),
        model=str(metadata.get("model") or "").strip() or None,
        sandbox_profile=str(metadata.get("sandbox_profile") or "").strip() or None,
        cadence=str(metadata.get("cadence") or "daily"),
        brief_cadence=str(metadata.get("brief_cadence") or "daily"),
        max_active_runs=int(metadata.get("max_active_runs", 1)),
        lane_quotas=_normalized_lane_quotas(metadata.get("lane_quotas"), campaign_type=campaign_type),
        budget_policy=(
            dict(metadata.get("budget_policy"))
            if isinstance(metadata.get("budget_policy"), dict)
            else _default_budget_policy(campaign_type)
        ),
        escalation_policy=(
            dict(metadata.get("escalation_policy"))
            if isinstance(metadata.get("escalation_policy"), dict)
            else _default_escalation_policy(campaign_type)
        ),
        created_at=str(metadata.get("created_at") or utc_now_iso()),
        updated_at=str(metadata.get("updated_at") or utc_now_iso()),
        last_tick_at=str(metadata.get("last_tick_at") or "").strip() or None,
        next_tick_at=str(metadata.get("next_tick_at") or "").strip() or None,
        notes_md=parsed.content,
        metadata={
            key: value
            for key, value in metadata.items()
            if key
            not in {
                "id",
                "title",
                "goal",
                "project_ids",
                "status",
                "type",
                "driver",
                "model",
                "sandbox_profile",
                "cadence",
                "brief_cadence",
                "max_active_runs",
                "lane_quotas",
                "budget_policy",
                "escalation_policy",
                "created_at",
                "updated_at",
                "last_tick_at",
                "next_tick_at",
            }
        },
        path=path,
    )


def list_campaigns(path: str | Path | None = None) -> list[CampaignRecord]:
    """List campaigns from the canonical store."""
    root = campaigns_dir(path)
    if not root.exists():
        return []
    return sorted(
        (_parse_campaign(item) for item in root.glob("campaign_*.md")),
        key=lambda c: c.id,
    )


def get_campaign(path: str | Path | None, campaign_id: str) -> CampaignRecord:
    """Load a campaign by id."""
    target = _campaign_path(path, campaign_id)
    if target.exists():
        return _parse_campaign(target)
    for campaign in list_campaigns(path):
        if campaign.id == campaign_id:
            return campaign
    raise FileNotFoundError(f"Campaign not found: {campaign_id}")


def save_campaign(path: str | Path | None, campaign: CampaignRecord) -> CampaignRecord:
    """Persist a campaign back to markdown."""
    target = campaign.path or _campaign_path(path, campaign.id)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        safe_dump_agency_md(
            campaign.to_frontmatter(),
            _campaign_body(campaign.goal, campaign.notes_md),
        ),
        encoding="utf-8",
    )
    campaign.path = target
    return campaign


def _campaign_request(
    title: str,
    goal: str,
    project_ids: list[str],
    options: dict[str, Any],
) -> _CampaignRequest:
    unexpected = sorted(set(options) - _CAMPAIGN_OPTION_KEYS)
    if unexpected:
        unexpected_list = ", ".join(unexpected)
        raise TypeError(f"Unsupported campaign option(s): {unexpected_list}")
    model = options.get("model")
    campaign_type = _normalized_campaign_type(options.get("campaign_type"))
    lane_quotas = _normalized_lane_quotas(options.get("lane_quotas"), campaign_type=campaign_type)
    budget_policy = (
        dict(options.get("budget_policy"))
        if isinstance(options.get("budget_policy"), dict)
        else _default_budget_policy(campaign_type)
    )
    escalation_policy = (
        dict(options.get("escalation_policy"))
        if isinstance(options.get("escalation_policy"), dict)
        else _default_escalation_policy(campaign_type)
    )
    return {
        "title": title.strip(),
        "goal": goal.strip(),
        "project_ids": list(project_ids),
        "campaign_type": campaign_type,
        "driver": str(options.get("driver", "local")),
        "model": None if model is None else str(model),
        "sandbox_profile": str(options.get("sandbox_profile") or "").strip() or None,
        "cadence": str(options.get("cadence", "daily")),
        "brief_cadence": str(options.get("brief_cadence", "daily")),
        "max_active_runs": int(options.get("max_active_runs", 1)),
        "lane_quotas": lane_quotas,
        "budget_policy": budget_policy,
        "escalation_policy": escalation_policy,
        "notes_md": str(options.get("notes_md", "")),
    }


def create_campaign(
    path: str | Path | None,
    *,
    title: str,
    goal: str,
    project_ids: list[str],
    **options: Any,
) -> CampaignRecord:
    """Create and persist a new campaign from the stable keyword API."""
    request = _campaign_request(title, goal, project_ids, options)
    campaign = CampaignRecord(
        id=new_id("camp"),
        title=request["title"],
        goal=request["goal"],
        project_ids=list(request["project_ids"]),
        campaign_type=request["campaign_type"],
        driver=request["driver"],
        model=request["model"],
        sandbox_profile=request["sandbox_profile"],
        cadence=request["cadence"],
        brief_cadence=request["brief_cadence"],
        max_active_runs=request["max_active_runs"],
        lane_quotas=request["lane_quotas"],
        budget_policy=request["budget_policy"],
        escalation_policy=request["escalation_policy"],
        notes_md=request["notes_md"],
    )
    return save_campaign(path, campaign)


def next_tick_at(campaign: CampaignRecord) -> str | None:
    """Return the next scheduled campaign tick timestamp."""
    if campaign.cadence == "daily":
        return (
            datetime.now(timezone.utc) + timedelta(days=1)
        ).isoformat().replace("+00:00", "Z")
    if campaign.cadence == "weekly":
        return (
            datetime.now(timezone.utc) + timedelta(days=7)
        ).isoformat().replace("+00:00", "Z")
    return None


def write_brief(path: str | Path | None, *, slug: str, title: str, body: str) -> Path:
    """Write a brief artifact under .hive/briefs."""
    target = briefs_dir(path) / f"{slug}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"# {title}\n\n{body.strip()}\n", encoding="utf-8")
    return target


__all__ = [
    "CAMPAIGN_LANES",
    "CAMPAIGN_TYPES",
    "campaign_artifacts_dir",
    "create_campaign",
    "default_lane_quotas",
    "get_campaign",
    "list_campaigns",
    "next_tick_at",
    "save_campaign",
    "write_brief",
]

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

_CAMPAIGN_OPTION_KEYS = {
    "driver",
    "model",
    "cadence",
    "brief_cadence",
    "max_active_runs",
    "notes_md",
}


class _CampaignRequest(TypedDict):
    title: str
    goal: str
    project_ids: list[str]
    driver: str
    model: str | None
    cadence: str
    brief_cadence: str
    max_active_runs: int
    notes_md: str


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


def _parse_campaign(path: Path) -> CampaignRecord:
    parsed = safe_load_agency_md(path)
    metadata = dict(parsed.metadata)
    return CampaignRecord(
        id=str(metadata.get("id") or path.stem.removeprefix("campaign_")),
        title=str(metadata.get("title") or path.stem),
        goal=str(metadata.get("goal") or "").strip(),
        project_ids=[str(value) for value in metadata.get("project_ids", [])],
        status=str(metadata.get("status") or "active"),
        driver=str(metadata.get("driver") or "local"),
        model=str(metadata.get("model") or "").strip() or None,
        cadence=str(metadata.get("cadence") or "daily"),
        brief_cadence=str(metadata.get("brief_cadence") or "daily"),
        max_active_runs=int(metadata.get("max_active_runs", 1)),
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
                "driver",
                "model",
                "cadence",
                "brief_cadence",
                "max_active_runs",
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
    return {
        "title": title.strip(),
        "goal": goal.strip(),
        "project_ids": list(project_ids),
        "driver": str(options.get("driver", "local")),
        "model": None if model is None else str(model),
        "cadence": str(options.get("cadence", "daily")),
        "brief_cadence": str(options.get("brief_cadence", "daily")),
        "max_active_runs": int(options.get("max_active_runs", 1)),
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
        driver=request["driver"],
        model=request["model"],
        cadence=request["cadence"],
        brief_cadence=request["brief_cadence"],
        max_active_runs=request["max_active_runs"],
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

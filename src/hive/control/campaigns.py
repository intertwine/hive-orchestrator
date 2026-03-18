"""Campaign orchestration helpers for Hive 2.2."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.hive.clock import utc_now_iso
from src.hive.constants import RUN_ACTIVE_STATUSES
from src.hive.control.portfolio import portfolio_status, recommend_next_task, work_on_task
from src.hive.runs.engine import load_run
from src.hive.store.campaigns import (
    create_campaign,
    get_campaign,
    list_campaigns,
    next_tick_at,
    save_campaign,
    write_brief,
)
from src.hive.store.events import emit_event
from src.hive.store.layout import runs_dir


def _campaign_runs(root: Path, campaign_id: str) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for metadata_path in sorted(runs_dir(root).glob("run_*/metadata.json")):
        run = load_run(root, metadata_path.parent.name)
        if run.get("campaign_id") == campaign_id:
            runs.append(run)
    runs.sort(key=lambda item: item.get("started_at") or item["id"], reverse=True)
    return runs


def _best_campaign_recommendation(root: Path, project_ids: list[str]) -> dict[str, Any] | None:
    """Return the best next-task recommendation across campaign projects."""
    recommendation: dict[str, Any] | None = None
    best_score = float("-inf")
    for project_id in project_ids:
        candidate = recommend_next_task(root, project_id=project_id, emit_decision_event=False)
        if candidate is not None:
            candidate_payload = dict(candidate)
            candidate_score = float(candidate_payload["score"])
            if recommendation is None or candidate_score > best_score:
                recommendation = candidate_payload
                best_score = candidate_score
    return recommendation


def campaign_status(path: str | Path | None, campaign_id: str) -> dict[str, Any]:
    """Return a normalized status payload for a campaign."""
    root = Path(path or Path.cwd()).resolve()
    campaign = get_campaign(root, campaign_id)
    runs = _campaign_runs(root, campaign.id)
    active_runs = [run for run in runs if run.get("status") in RUN_ACTIVE_STATUSES]
    accepted_runs = [run for run in runs if run.get("status") == "accepted"][:5]
    recommendation = _best_campaign_recommendation(root, campaign.project_ids)
    return {
        "campaign": {
            "id": campaign.id,
            "title": campaign.title,
            "goal": campaign.goal,
            "project_ids": campaign.project_ids,
            "status": campaign.status,
            "driver": campaign.driver,
            "model": campaign.model,
            "cadence": campaign.cadence,
            "brief_cadence": campaign.brief_cadence,
            "max_active_runs": campaign.max_active_runs,
            "last_tick_at": campaign.last_tick_at,
            "next_tick_at": campaign.next_tick_at,
            "path": str(campaign.path) if campaign.path else None,
        },
        "active_runs": active_runs,
        "accepted_runs": accepted_runs,
        "recommended_next": recommendation,
    }


# pylint: disable-next=too-many-arguments
def create_campaign_flow(
    path: str | Path | None,
    *,
    title: str,
    goal: str,
    project_ids: list[str],
    driver: str = "local",
    model: str | None = None,
    cadence: str = "daily",
    brief_cadence: str = "daily",
    max_active_runs: int = 1,
    notes_md: str = "",
) -> dict[str, Any]:
    """Create a campaign and emit its canonical event."""
    root = Path(path or Path.cwd()).resolve()
    campaign = create_campaign(
        root,
        title=title,
        goal=goal,
        project_ids=project_ids,
        driver=driver,
        model=model,
        cadence=cadence,
        brief_cadence=brief_cadence,
        max_active_runs=max_active_runs,
        notes_md=notes_md,
    )
    emit_event(
        root,
        actor={"kind": "human", "id": "operator"},
        entity_type="campaign",
        entity_id=campaign.id,
        event_type="campaign.created",
        source="campaign.create",
        payload={
            "title": campaign.title,
            "goal": campaign.goal,
            "project_ids": campaign.project_ids,
            "driver": campaign.driver,
        },
        campaign_id=campaign.id,
    )
    return campaign_status(root, campaign.id)


def tick_campaign(
    path: str | Path | None,
    campaign_id: str,
    *,
    owner: str | None = None,
) -> dict[str, Any]:
    """Launch the next set of runs for a bounded campaign."""
    root = Path(path or Path.cwd()).resolve()
    campaign = get_campaign(root, campaign_id)
    status = campaign_status(root, campaign_id)
    active_runs = list(status["active_runs"])
    launches: list[dict[str, Any]] = []
    while len(active_runs) + len(launches) < max(campaign.max_active_runs, 1):
        recommendation = _best_campaign_recommendation(root, campaign.project_ids)
        if recommendation is None:
            break
        payload = work_on_task(
            root,
            task_id=recommendation["task"]["id"],
            owner=owner,
            driver=campaign.driver,
            model=campaign.model,
            campaign_id=campaign.id,
            checkpoint=True,
            checkpoint_message=f"Checkpoint campaign {campaign.title}",
        )
        launches.append(payload["run"])
    campaign.last_tick_at = utc_now_iso()
    campaign.next_tick_at = next_tick_at(campaign)
    campaign.updated_at = utc_now_iso()
    save_campaign(root, campaign)
    emit_event(
        root,
        actor={"kind": "system", "id": "hive"},
        entity_type="campaign",
        entity_id=campaign.id,
        event_type="campaign.tick",
        source="campaign.tick",
        payload={"launched_runs": [run["id"] for run in launches]},
        campaign_id=campaign.id,
    )
    return campaign_status(root, campaign.id) | {"launched_runs": launches}


def generate_brief(path: str | Path | None, *, cadence: str = "daily") -> dict[str, Any]:
    """Generate a searchable portfolio brief under .hive/briefs."""
    root = Path(path or Path.cwd()).resolve()
    portfolio = portfolio_status(root)
    campaigns = [campaign_status(root, campaign.id) for campaign in list_campaigns(root)]
    slug = f"{cadence}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    lines = [
        f"Cadence: {cadence}",
        "",
        "## Portfolio",
        f"- Projects: {len(portfolio['projects'])}",
        f"- Active runs: {len(portfolio['active_runs'])}",
        f"- Recent management events: {len(portfolio['recent_events'])}",
    ]
    if portfolio["recommended_next"]:
        recommendation = dict(portfolio["recommended_next"])
        task_payload = dict(recommendation["task"])
        project_payload = dict(recommendation["project"])
        lines.extend(
            [
                "",
                "## Recommended Next",
                f"- Task: {task_payload['title']} ({task_payload['id']})",
                f"- Project: {project_payload['title']}",
            ]
        )
    if campaigns:
        lines.extend(["", "## Campaigns"])
        for campaign in campaigns:
            lines.append(
                f"- {campaign['campaign']['title']}: {len(campaign['active_runs'])} active run(s), "
                f"{len(campaign['accepted_runs'])} recent accepted run(s)"
            )
    brief_path = write_brief(
        root,
        slug=slug,
        title=f"Hive {cadence.title()} Brief",
        body="\n".join(lines),
    )
    return {
        "path": str(brief_path),
        "cadence": cadence,
        "campaigns": campaigns,
        "portfolio": portfolio,
    }

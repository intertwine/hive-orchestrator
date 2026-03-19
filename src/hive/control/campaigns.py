"""Campaign orchestration helpers for Hive 2.3."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

from src.hive.clock import utc_now_iso
from src.hive.constants import RUN_ACTIVE_STATUSES
from src.hive.control.portfolio import portfolio_status, recommend_next_task, work_on_task
from src.hive.drivers import SteeringRequest
from src.hive.runs.engine import load_run, steer_run
from src.hive.scheduler.query import ready_tasks
from src.hive.store.campaigns import (
    CAMPAIGN_LANES,
    campaign_artifacts_dir,
    create_campaign,
    default_lane_quotas,
    get_campaign,
    list_campaigns,
    next_tick_at,
    save_campaign,
    write_brief,
)
from src.hive.store.events import emit_event
from src.hive.store.layout import runs_dir

REVIEW_QUEUE_STATUSES = {"awaiting_review", "escalated"}


def _campaign_runs(root: Path, campaign_id: str) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for metadata_path in sorted(runs_dir(root).glob("run_*/metadata.json")):
        run = load_run(root, metadata_path.parent.name)
        if run.get("campaign_id") == campaign_id:
            runs.append(run)
    runs.sort(key=lambda item: item.get("started_at") or item["id"], reverse=True)
    return runs


def _project_active_runs(root: Path, project_ids: list[str]) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    project_filter = set(project_ids)
    for metadata_path in sorted(runs_dir(root).glob("run_*/metadata.json")):
        run = load_run(root, metadata_path.parent.name)
        if project_filter and str(run.get("project_id") or "") not in project_filter:
            continue
        if str(run.get("status") or "") not in RUN_ACTIVE_STATUSES:
            continue
        runs.append(run)
    runs.sort(key=lambda item: item.get("started_at") or item["id"], reverse=True)
    return runs


def _campaign_paths(root: Path, campaign_id: str) -> dict[str, Path]:
    state_dir = campaign_artifacts_dir(root, campaign_id)
    state_dir.mkdir(parents=True, exist_ok=True)
    return {
        "candidate_set": state_dir / "candidate-set.json",
        "decision": state_dir / "decision.json",
        "history": state_dir / "decisions.ndjson",
    }


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _text_terms(text: str) -> set[str]:
    return {term.casefold() for term in re.findall(r"[A-Za-z0-9_-]+", text)}


def _task_lane(task: dict[str, Any]) -> str:
    text = " ".join(
        [
            str(task.get("title") or ""),
            str(task.get("summary_md") or ""),
            " ".join(str(label) for label in task.get("labels", []) or []),
        ]
    ).casefold()
    if any(term in text for term in ("review", "eval", "approve", "qa")):
        return "review"
    if any(term in text for term in ("maintenance", "cleanup", "chore", "upgrade", "deps")):
        return "maintenance"
    if any(term in text for term in ("research", "explore", "investigate", "spike")):
        return "explore"
    return "exploit"


def _run_lane(run: dict[str, Any]) -> str:
    existing_lane = str(run.get("lane") or "").strip()
    if existing_lane in CAMPAIGN_LANES:
        return existing_lane
    decision_path = Path(str(run.get("scheduler_decision_path") or ""))
    if decision_path.exists():
        decision = _load_json(decision_path)
        lane = str(decision.get("selected_lane") or decision.get("lane") or "").strip()
        if lane in CAMPAIGN_LANES:
            return lane
    if str(run.get("status") or "") in REVIEW_QUEUE_STATUSES:
        return "review"
    if str(run.get("health") or "") == "paused":
        return "exploit"
    return "exploit"


def _annotate_run_lane(run: dict[str, Any]) -> dict[str, Any]:
    payload = dict(run)
    payload["lane"] = _run_lane(run)
    return payload


def _active_lane_counts(runs: list[dict[str, Any]]) -> dict[str, int]:
    counts = {lane: 0 for lane in CAMPAIGN_LANES}
    for run in runs:
        counts[_run_lane(run)] += 1
    return counts


def _lane_deficits(campaign, active_runs: list[dict[str, Any]]) -> dict[str, float]:
    counts = _active_lane_counts(active_runs)
    max_slots = max(int(campaign.max_active_runs), 1)
    return {
        lane: round(
            float(campaign.lane_quotas.get(lane, 0)) / 100.0
            - (float(counts.get(lane, 0)) / float(max_slots)),
            3,
        )
        for lane in CAMPAIGN_LANES
    }


def _recommended_driver(campaign) -> str:
    return str(campaign.driver or "local")


def _recommended_sandbox(campaign) -> str:
    return str(campaign.sandbox_profile or "default")


def _campaign_alignment(campaign, task: dict[str, Any]) -> float:
    goal_terms = _text_terms(campaign.goal)
    task_terms = _text_terms(
        " ".join(
            [
                str(task.get("title") or ""),
                str(task.get("summary_md") or ""),
                " ".join(str(label) for label in task.get("labels", []) or []),
            ]
        )
    )
    overlap = len(goal_terms & task_terms)
    base = 0.6 if str(task.get("project_id") or "") in campaign.project_ids else 0.2
    return round(min(1.0, base + (0.1 * overlap)), 3)


def _harness_fit(driver: str, lane: str) -> float:
    if driver == "codex":
        return 0.95 if lane in {"exploit", "maintenance"} else 0.7
    if driver in {"claude", "claude-code"}:
        return 0.95 if lane in {"explore", "review"} else 0.7
    if driver == "local":
        return 0.75
    if driver == "manual":
        return 0.55
    return 0.65


def _sandbox_fit(sandbox: str) -> float:
    if sandbox == "local-safe":
        return 0.9
    if sandbox == "local-fast":
        return 0.75
    if sandbox:
        return 0.7
    return 0.5


def _cost_penalty(driver: str) -> float:
    return {
        "manual": -0.05,
        "local": -0.1,
        "codex": -0.25,
        "claude": -0.25,
        "claude-code": -0.25,
    }.get(driver, -0.15)


def _context_freshness(active_runs: list[dict[str, Any]], task: dict[str, Any]) -> float:
    project_id = str(task.get("project_id") or "")
    if any(str(run.get("project_id") or "") == project_id for run in active_runs):
        return 0.8
    return 0.55


def _task_overlap_penalty(
    active_runs: list[dict[str, Any]],
    task: dict[str, Any],
    lane: str,
) -> float:
    penalty = 0.0
    task_id = str(task.get("id") or "")
    project_id = str(task.get("project_id") or "")
    for run in active_runs:
        if str(run.get("task_id") or "") == task_id:
            penalty -= 1.0
        elif str(run.get("project_id") or "") == project_id:
            penalty -= 0.35
        elif _run_lane(run) == lane:
            penalty -= 0.05
    return round(penalty, 3)


def _review_backlog(active_runs: list[dict[str, Any]]) -> int:
    return sum(1 for run in active_runs if str(run.get("status") or "") in REVIEW_QUEUE_STATUSES)


def _project_balance_bonus(
    project_ids: list[str],
    active_runs: list[dict[str, Any]],
    task: dict[str, Any],
) -> float:
    counts = {project_id: 0 for project_id in project_ids}
    project_id = str(task.get("project_id") or "")
    if project_id not in counts:
        return 0.0
    for run in active_runs:
        active_project_id = str(run.get("project_id") or "")
        if active_project_id in counts:
            counts[active_project_id] += 1
    if not counts:
        return 0.0
    min_count = min(counts.values())
    max_count = max(counts.values())
    if max_count == min_count:
        return 0.0
    spread = max(max_count - min_count, 1)
    bonus = (max_count - counts[project_id]) / spread
    return round(0.35 * bonus, 3)


def _task_candidate(
    campaign,
    task: dict[str, Any],
    active_runs: list[dict[str, Any]],
) -> dict[str, Any]:
    lane = _task_lane(task)
    driver = _recommended_driver(campaign)
    sandbox = _recommended_sandbox(campaign)
    unblock_value = min(
        1.0,
        float((task.get("graph_rank") or {}).get("task_unblock_count", 0)) / 3.0,
    )
    review_backlog = _review_backlog(active_runs)
    scores = {
        "campaign_alignment": _campaign_alignment(campaign, task),
        "readiness": 1.0 if str(task.get("status") or "") == "ready" else 0.4,
        "blocker_unlock_value": round(unblock_value, 3),
        "evaluator_pass_probability": 0.85 if lane in {"review", "maintenance"} else 0.7,
        "harness_fit": round(_harness_fit(driver, lane), 3),
        "sandbox_fit": round(_sandbox_fit(sandbox), 3),
        "context_freshness": round(_context_freshness(active_runs, task), 3),
        "project_balance_bonus": _project_balance_bonus(
            list(campaign.project_ids),
            active_runs,
            task,
        ),
        "learning_value": (
            0.95 if lane == "explore" else 0.65 if campaign.campaign_type == "research" else 0.4
        ),
        "estimated_cost_penalty": _cost_penalty(driver),
        "overlap_penalty": _task_overlap_penalty(active_runs, task, lane),
        "review_backlog_penalty_if_wrong_lane": round(
            -0.15 * review_backlog if review_backlog and lane != "review" else 0.0,
            3,
        ),
    }
    return {
        "candidate_id": str(task["id"]),
        "kind": "task",
        "action": "launch",
        "launchable": True,
        "title": str(task.get("title") or task["id"]),
        "project_id": str(task.get("project_id") or ""),
        "task_id": str(task["id"]),
        "lane": lane,
        "scores": scores,
        "total": round(sum(float(value) for value in scores.values()), 3),
        "recommended_driver": driver,
        "recommended_sandbox": sandbox,
    }


def _resume_candidate(campaign, run: dict[str, Any]) -> dict[str, Any]:
    lane = _run_lane(run)
    driver = str(run.get("driver") or _recommended_driver(campaign))
    sandbox = _recommended_sandbox(campaign)
    scores = {
        "campaign_alignment": 0.85,
        "readiness": 0.9,
        "blocker_unlock_value": 0.4,
        "evaluator_pass_probability": 0.75,
        "harness_fit": round(_harness_fit(driver, lane), 3),
        "sandbox_fit": round(_sandbox_fit(sandbox), 3),
        "context_freshness": 0.95,
        "learning_value": 0.35,
        "estimated_cost_penalty": _cost_penalty(driver),
        "overlap_penalty": 0.0,
        "review_backlog_penalty_if_wrong_lane": 0.0,
    }
    return {
        "candidate_id": str(run["id"]),
        "kind": "run_resume",
        "action": "resume",
        "launchable": True,
        "title": f"Resume {run['id']}",
        "project_id": str(run.get("project_id") or ""),
        "run_id": str(run["id"]),
        "lane": lane,
        "scores": scores,
        "total": round(sum(float(value) for value in scores.values()), 3),
        "recommended_driver": driver,
        "recommended_sandbox": sandbox,
    }


def _review_candidate(run: dict[str, Any]) -> dict[str, Any]:
    scores = {
        "campaign_alignment": 0.8,
        "readiness": 1.0,
        "blocker_unlock_value": 0.2,
        "evaluator_pass_probability": 1.0,
        "harness_fit": 0.0,
        "sandbox_fit": 0.0,
        "context_freshness": 0.8,
        "learning_value": 0.25,
        "estimated_cost_penalty": 0.0,
        "overlap_penalty": 0.0,
        "review_backlog_penalty_if_wrong_lane": 0.0,
    }
    return {
        "candidate_id": str(run["id"]),
        "kind": "run_review",
        "action": "attention",
        "launchable": False,
        "title": f"Review {run['id']}",
        "project_id": str(run.get("project_id") or ""),
        "run_id": str(run["id"]),
        "lane": "review",
        "scores": scores,
        "total": round(sum(float(value) for value in scores.values()), 3),
        "recommended_driver": str(run.get("driver") or ""),
        "recommended_sandbox": "",
    }


def _candidate_pool(
    root: Path,
    campaign,
    active_runs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for run in active_runs:
        if str(run.get("health") or "") == "paused":
            candidates.append(_resume_candidate(campaign, run))
        if str(run.get("status") or "") in REVIEW_QUEUE_STATUSES:
            candidates.append(_review_candidate(run))
    for project_id in campaign.project_ids:
        for task in ready_tasks(root, project_id=project_id, limit=6):
            candidates.append(_task_candidate(campaign, dict(task), active_runs))
    candidates.sort(
        key=lambda item: (-float(item["total"]), str(item["lane"]), str(item["candidate_id"]))
    )
    return candidates


def _select_candidate(
    candidates: list[dict[str, Any]],
    lane_deficits: dict[str, float],
) -> tuple[dict[str, Any] | None, str]:
    if not candidates:
        return None, "no candidate satisfied the current campaign policy"
    best_candidate: dict[str, Any] | None = None
    best_deficit = float("-inf")
    best_total = float("-inf")
    for lane in CAMPAIGN_LANES:
        lane_candidates = [candidate for candidate in candidates if candidate.get("lane") == lane]
        if not lane_candidates:
            continue
        selected = max(lane_candidates, key=lambda item: float(item["total"]))
        deficit = float(lane_deficits.get(lane, 0.0))
        total = float(selected["total"])
        if deficit > best_deficit or (deficit == best_deficit and total > best_total):
            best_candidate = selected
            best_deficit = deficit
            best_total = total
    if best_candidate is not None:
        return (
            best_candidate,
            f"highest {best_candidate['lane']} score under current lane quotas",
        )
    selected = max(candidates, key=lambda item: float(item["total"]))
    return selected, "highest total score across all lanes"


def _persist_campaign_decision(
    root: Path,
    campaign_id: str,
    *,
    candidate_set: dict[str, Any],
    decision: dict[str, Any],
) -> dict[str, str]:
    paths = _campaign_paths(root, campaign_id)
    _write_json(paths["candidate_set"], candidate_set)
    _write_json(paths["decision"], decision)
    _append_jsonl(paths["history"], decision)
    return {key: str(value) for key, value in paths.items()}


def _preview_campaign_decision(
    root: Path,
    campaign,
    active_runs: list[dict[str, Any]],
    *,
    scoring_runs: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    policy_runs = list(scoring_runs or active_runs)
    lane_deficits = _lane_deficits(campaign, active_runs)
    candidate_set = {
        "ts": utc_now_iso(),
        "campaign_id": campaign.id,
        "campaign_type": campaign.campaign_type,
        "lane_quotas": campaign.lane_quotas,
        "active_runs_by_lane": _active_lane_counts(active_runs),
        "lane_deficits": lane_deficits,
        "active_runs_by_project": {
            project_id: sum(
                1 for run in policy_runs if str(run.get("project_id") or "") == project_id
            )
            for project_id in campaign.project_ids
        },
        "candidates": _candidate_pool(root, campaign, policy_runs),
    }
    selected, reason = _select_candidate(list(candidate_set["candidates"]), lane_deficits)
    decision_preview = {
        "ts": utc_now_iso(),
        "campaign_id": campaign.id,
        "campaign_type": campaign.campaign_type,
        "selected_candidate_id": selected["candidate_id"] if selected else None,
        "selected_lane": selected["lane"] if selected else None,
        "selected_action": selected["action"] if selected else "idle",
        "reason": reason,
        "selected_candidate": selected,
    }
    return candidate_set, decision_preview


def _sync_run_scheduler_artifacts(
    run: dict[str, Any],
    *,
    candidate_set: dict[str, Any],
    decision: dict[str, Any],
) -> None:
    candidate_path_value = str(run.get("scheduler_candidate_set_path") or "")
    decision_path_value = str(run.get("scheduler_decision_path") or "")
    if candidate_path_value:
        _write_json(Path(candidate_path_value), candidate_set)
    if decision_path_value:
        _write_json(Path(decision_path_value), decision)


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
    active_runs = [
        _annotate_run_lane(run) for run in runs if run.get("status") in RUN_ACTIVE_STATUSES
    ]
    scoring_runs = [
        _annotate_run_lane(run) for run in _project_active_runs(root, campaign.project_ids)
    ]
    accepted_runs = [_annotate_run_lane(run) for run in runs if run.get("status") == "accepted"][:5]
    recommendation = _best_campaign_recommendation(root, campaign.project_ids)
    artifact_paths = _campaign_paths(root, campaign.id)
    preview_candidate_set, decision_preview = _preview_campaign_decision(
        root,
        campaign,
        active_runs,
        scoring_runs=scoring_runs,
    )
    latest_candidate_set = _load_json(artifact_paths["candidate_set"])
    latest_decision = _load_json(artifact_paths["decision"])
    return {
        "campaign": {
            "id": campaign.id,
            "title": campaign.title,
            "goal": campaign.goal,
            "type": campaign.campaign_type,
            "project_ids": campaign.project_ids,
            "lane_quotas": campaign.lane_quotas or default_lane_quotas(campaign.campaign_type),
            "budget_policy": campaign.budget_policy,
            "escalation_policy": campaign.escalation_policy,
            "status": campaign.status,
            "driver": campaign.driver,
            "model": campaign.model,
            "sandbox_profile": campaign.sandbox_profile,
            "cadence": campaign.cadence,
            "brief_cadence": campaign.brief_cadence,
            "max_active_runs": campaign.max_active_runs,
            "last_tick_at": campaign.last_tick_at,
            "next_tick_at": campaign.next_tick_at,
            "path": str(campaign.path) if campaign.path else None,
            "artifact_paths": {key: str(value) for key, value in artifact_paths.items()},
            "latest_candidate_set_path": str(artifact_paths["candidate_set"]),
            "latest_decision_path": str(artifact_paths["decision"]),
        },
        "active_runs": active_runs,
        "active_runs_by_lane": _active_lane_counts(active_runs),
        "active_runs_by_project": preview_candidate_set["active_runs_by_project"],
        "accepted_runs": accepted_runs,
        "recommended_next": recommendation,
        "candidate_set_preview": preview_candidate_set,
        "decision_preview": decision_preview,
        "latest_candidate_set": latest_candidate_set,
        "latest_decision": latest_decision,
    }


# pylint: disable-next=too-many-arguments
def create_campaign_flow(
    path: str | Path | None,
    *,
    title: str,
    goal: str,
    project_ids: list[str],
    campaign_type: str = "delivery",
    lane_quotas: dict[str, int] | None = None,
    sandbox_profile: str | None = None,
    budget_policy: dict[str, Any] | None = None,
    escalation_policy: dict[str, Any] | None = None,
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
        campaign_type=campaign_type,
        lane_quotas=lane_quotas,
        sandbox_profile=sandbox_profile,
        budget_policy=budget_policy,
        escalation_policy=escalation_policy,
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
            "campaign_type": campaign.campaign_type,
            "project_ids": campaign.project_ids,
            "driver": campaign.driver,
            "lane_quotas": campaign.lane_quotas,
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
    """Launch or rebalance the next campaign action under logged policy."""
    root = Path(path or Path.cwd()).resolve()
    campaign = get_campaign(root, campaign_id)
    status = campaign_status(root, campaign_id)
    active_runs = list(status["active_runs"])
    scoring_runs = [
        _annotate_run_lane(run) for run in _project_active_runs(root, campaign.project_ids)
    ]
    launches: list[dict[str, Any]] = []
    resumed_runs: list[dict[str, Any]] = []
    attention: list[dict[str, Any]] = []
    launch_decisions: list[dict[str, Any]] = []
    while len(active_runs) + len(launches) < max(campaign.max_active_runs, 1):
        candidate_set, preview = _preview_campaign_decision(
            root,
            campaign,
            active_runs,
            scoring_runs=scoring_runs,
        )
        selected = preview["selected_candidate"]
        reason = str(preview["reason"])
        if selected is None:
            decision = {
                "ts": utc_now_iso(),
                "campaign_id": campaign.id,
                "campaign_type": campaign.campaign_type,
                "selected_candidate_id": None,
                "selected_lane": None,
                "selected_action": "idle",
                "reason": reason,
                "launched_run_ids": [],
                "resumed_run_ids": [],
            }
            _persist_campaign_decision(
                root,
                campaign.id,
                candidate_set=candidate_set,
                decision=decision,
            )
            launch_decisions.append(decision)
            break
        decision = {
            "ts": utc_now_iso(),
            "campaign_id": campaign.id,
            "campaign_type": campaign.campaign_type,
            "selected_candidate_id": selected["candidate_id"],
            "selected_lane": selected["lane"],
            "selected_action": selected["action"],
            "recommended_driver": selected.get("recommended_driver"),
            "recommended_sandbox": selected.get("recommended_sandbox"),
            "reason": reason,
            "selected_candidate": selected,
            "launched_run_ids": [],
            "resumed_run_ids": [],
        }
        if selected["action"] == "launch":
            payload = work_on_task(
                root,
                task_id=selected["task_id"],
                owner=owner,
                driver=str(selected.get("recommended_driver") or campaign.driver),
                model=campaign.model,
                campaign_id=campaign.id,
                profile="default",
                checkpoint=True,
                checkpoint_message=f"Checkpoint campaign {campaign.title}",
            )
            launches.append(payload["run"])
            active_runs.append(_annotate_run_lane(payload["run"]))
            scoring_runs.append(_annotate_run_lane(payload["run"]))
            decision["launched_run_ids"] = [payload["run"]["id"]]
            _sync_run_scheduler_artifacts(
                payload["run"],
                candidate_set=candidate_set,
                decision=decision,
            )
        elif selected["action"] == "resume":
            resumed = steer_run(
                root,
                str(selected["run_id"]),
                SteeringRequest(
                    action="resume",
                    reason=(
                        f"Campaign {campaign.title} resumed paused work in lane "
                        f"{selected['lane']}."
                    ),
                ),
                actor=owner or "manager",
            )
            resumed_runs.append(dict(resumed["run"]))
            decision["resumed_run_ids"] = [selected["run_id"]]
        else:
            attention.append(
                {
                    "candidate_id": selected["candidate_id"],
                    "lane": selected["lane"],
                    "reason": reason,
                    "title": selected["title"],
                }
            )
        _persist_campaign_decision(
            root,
            campaign.id,
            candidate_set=candidate_set,
            decision=decision,
        )
        launch_decisions.append(decision)
        if selected["action"] != "launch":
            break
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
        payload={
            "launched_runs": [run["id"] for run in launches],
            "resumed_runs": [run["id"] for run in resumed_runs],
            "attention": attention,
        },
        campaign_id=campaign.id,
    )
    return campaign_status(root, campaign.id) | {
        "launched_runs": launches,
        "resumed_runs": resumed_runs,
        "attention": attention,
        "launch_decisions": launch_decisions,
    }


def generate_brief(path: str | Path | None, *, cadence: str = "daily") -> dict[str, Any]:
    """Generate a searchable portfolio brief under .hive/briefs."""
    root = Path(path or Path.cwd()).resolve()
    portfolio = portfolio_status(root)
    campaigns = [campaign_status(root, campaign.id) for campaign in list_campaigns(root)]
    slug = f"{cadence}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    lines = [
        f"Cadence: {cadence}",
        "",
        "## What changed",
        f"- Projects: {len(portfolio['projects'])}",
        f"- Active runs: {len(portfolio['active_runs'])}",
        f"- Recent management events: {len(portfolio['recent_events'])}",
    ]
    lines.extend(["", "## What Hive recommends next"])
    if portfolio["recommended_next"]:
        recommendation = dict(portfolio["recommended_next"])
        task_payload = dict(recommendation["task"])
        project_payload = dict(recommendation["project"])
        lines.extend(
            [
                f"- Task: {task_payload['title']} ({task_payload['id']})",
                f"- Project: {project_payload['title']}",
            ]
        )
    else:
        lines.append("- No ready portfolio recommendation is available right now.")
    if campaigns:
        lines.extend(["", "## Campaigns"])
        for campaign in campaigns:
            latest_decision = campaign.get("latest_decision") or {}
            lines.append(
                f"- {campaign['campaign']['title']} [{campaign['campaign']['type']}]: "
                f"{len(campaign['active_runs'])} active run(s), "
                f"{len(campaign['accepted_runs'])} recent accepted run(s), "
                f"lanes={campaign['active_runs_by_lane']}"
            )
            if latest_decision.get("reason"):
                lines.append(
                    f"  recommendation: {latest_decision['reason']} "
                    f"(lane={latest_decision.get('selected_lane')}, "
                    f"candidate={latest_decision.get('selected_candidate_id')})"
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

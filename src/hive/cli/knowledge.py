"""Memory, context, sync, and portfolio Hive CLI commands."""

# pylint: disable=line-too-long,too-many-lines,too-many-locals,too-many-statements
# pylint: disable=too-many-branches,too-many-return-statements,import-outside-toplevel

from __future__ import annotations

import sqlite3
from pathlib import Path

from src.hive.cli.common import emit, emit_error, clean_string_list
from src.hive.control import (
    campaign_status,
    create_campaign_flow,
    generate_brief,
    portfolio_status,
    steer_project,
    tick_campaign,
    tick_portfolio,
)
from src.hive.context_bundle import build_context_bundle
from src.hive.memory.observe import observe
from src.hive.memory.reflect import reflect
from src.hive.memory.review import accept_memory_review, reject_memory_review
from src.hive.memory.search import search
from src.hive.migrate.v1_to_v2 import migrate_v1_to_v2
from src.hive.scheduler.query import dependency_summary
from src.hive.store.cache import CacheBusyError, rebuild_cache
from src.hive.store.events import emit_event
from src.hive.workspace import WorkspaceBusyError, resolve_workspace_path, sync_workspace


def _lane_quota_map(values: list[str] | None) -> dict[str, int] | None:
    quotas: dict[str, int] = {}
    for value in values or []:
        lane, separator, amount = value.partition("=")
        if not separator:
            raise ValueError(f"Lane quota must look like lane=percent, got {value!r}")
        normalized_lane = lane.strip().lower()
        if normalized_lane not in {"exploit", "explore", "review", "maintenance"}:
            raise ValueError(f"Unsupported lane quota {normalized_lane!r}")
        quotas[normalized_lane] = max(0, int(amount.strip()))
    return quotas or None


def dispatch(args, root: Path) -> int:
    """Dispatch knowledge and portfolio commands."""
    try:
        if args.command == "memory":
            if args.memory_command == "observe":
                output_path = observe(
                    root,
                    transcript_path=args.transcript_path,
                    note=args.note,
                    scope=args.scope,
                    harness=args.harness,
                    project_id=args.project,
                )
                rebuild_cache(root)
                return emit(
                    {"ok": True, "message": f"Recorded observation at {output_path}", "path": str(output_path)},
                    args.json,
                )
            if args.memory_command == "reflect":
                output_paths = {
                    key: str(value)
                    for key, value in reflect(
                        root,
                        scope=args.scope,
                        project_id=args.project,
                        propose=args.propose,
                    ).items()
                }
                rebuild_cache(root)
                event_type = "memory.proposed" if args.propose else "memory.accepted"
                emit_event(
                    root,
                    actor={"kind": "system", "id": "hive"},
                    entity_type="memory",
                    entity_id=args.project or args.scope,
                    event_type=event_type,
                    source="memory.reflect",
                    payload={"paths": output_paths, "scope": args.scope, "project_id": args.project},
                    project_id=args.project,
                )
                return emit(
                    {
                        "ok": True,
                        "message": (
                            "Wrote proposed memory review documents"
                            if args.propose
                            else "Wrote reflection documents"
                        ),
                        "paths": output_paths,
                    },
                    args.json,
                )
            if args.memory_command == "accept":
                promoted = accept_memory_review(root, scope=args.scope, project_id=args.project)
                rebuild_cache(root)
                emit_event(
                    root,
                    actor={"kind": "human", "id": "operator"},
                    entity_type="memory",
                    entity_id=args.project or args.scope,
                    event_type="memory.accepted",
                    source="memory.review",
                    payload={"paths": promoted, "scope": args.scope, "project_id": args.project},
                    project_id=args.project,
                )
                return emit({"ok": True, "message": "Accepted proposed memory changes", "paths": promoted}, args.json)
            if args.memory_command == "reject":
                removed = reject_memory_review(root, scope=args.scope, project_id=args.project)
                rebuild_cache(root)
                emit_event(
                    root,
                    actor={"kind": "human", "id": "operator"},
                    entity_type="memory",
                    entity_id=args.project or args.scope,
                    event_type="memory.rejected",
                    source="memory.review",
                    payload={"paths": removed, "scope": args.scope, "project_id": args.project},
                    project_id=args.project,
                )
                return emit({"ok": True, "message": "Rejected proposed memory changes", "paths": removed}, args.json)
            if args.memory_command == "search":
                return emit(
                    {
                        "ok": True,
                        "message": f"Found memory results for {args.query!r}",
                        "results": search(
                            root,
                            args.query,
                            scope=args.scope,
                            project_id=args.project,
                            task_id=args.task,
                            limit=args.limit,
                        ),
                    },
                    args.json,
                )
        if args.command == "context":
            if args.context_command == "startup":
                bundle = build_context_bundle(
                    root,
                    project_ref=args.project,
                    mode="startup",
                    profile=args.profile,
                    query=args.query,
                    task_id=args.task,
                    refresh=True,
                )
                if args.output:
                    output_path = resolve_workspace_path(root, args.output)
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_text(str(bundle["rendered"]), encoding="utf-8")
                    return emit(
                        {
                            "ok": True,
                            "message": f"Wrote startup context to {output_path}",
                            "output_path": str(output_path),
                            "project": bundle["project_payload"],
                            "next_steps": [
                                f"Open {output_path}",
                                "Copy the bundle into your agent, or reuse it as a "
                                "handoff artifact.",
                            ],
                        },
                        args.json,
                    )
                if args.json:
                    return emit({"ok": True, "context": bundle["context"]}, args.json)
                return emit({"ok": True, "rendered_context": bundle["rendered"]}, args.json)
            if args.context_command == "handoff":
                bundle = build_context_bundle(root, project_ref=args.project, mode="handoff", refresh=True)
                if args.output:
                    output_path = resolve_workspace_path(root, args.output)
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_text(str(bundle["rendered"]), encoding="utf-8")
                    return emit(
                        {
                            "ok": True,
                            "message": f"Wrote handoff context to {output_path}",
                            "output_path": str(output_path),
                            "project": bundle["project_payload"],
                        },
                        args.json,
                    )
                if args.json:
                    return emit({"ok": True, "context": bundle["context"]}, args.json)
                return emit({"ok": True, "rendered_context": bundle["rendered"]}, args.json)
        if args.command == "sync" and args.sync_command == "projections":
            sync_workspace(root)
            return emit({"ok": True, "message": "Synced projections"}, args.json)
        if args.command == "migrate" and args.migrate_command == "v1-to-v2":
            report = migrate_v1_to_v2(
                root,
                dry_run=args.dry_run,
                project_filter=args.project,
                owner=args.owner,
                rewrite=args.rewrite,
            )
            payload = report.to_dict()
            payload["ok"] = report.ok
            return emit(payload, args.json)
        if args.command == "deps":
            return emit({"ok": True, "summary": dependency_summary(root)}, args.json)
        if args.command == "portfolio":
            if args.portfolio_command == "status":
                payload = portfolio_status(root)
                return emit(
                    {
                        "ok": True,
                        "message": "Loaded portfolio status",
                        "projects": payload["projects"],
                        "tasks": payload["ready_tasks"],
                        "active_runs": payload["active_runs"],
                        "evaluating_runs": payload["evaluating_runs"],
                        "recommendation": payload["recommended_next"],
                        "recent_events": payload["recent_events"],
                    },
                    args.json,
                )
            if args.portfolio_command == "steer":
                if args.pause and args.resume:
                    raise ValueError("Use either --pause or --resume, not both.")
                if args.force_review and args.clear_force_review:
                    raise ValueError("Use either --force-review or --clear-force-review, not both.")
                payload = steer_project(
                    root,
                    args.project_ref,
                    paused=True if args.pause else False if args.resume else None,
                    focus_task_id=args.focus_task,
                    clear_focus=args.clear_focus,
                    boost=args.boost,
                    force_review=True if args.force_review else False if args.clear_force_review else None,
                    note=args.note,
                    actor=args.owner,
                )
                return emit(
                    {"ok": True, "message": f"Updated steering for {payload['project']['id']}", "project": payload["project"], "steering": payload["steering"]},
                    args.json,
                )
            if args.portfolio_command == "tick":
                payload = tick_portfolio(
                    root,
                    mode=args.mode,
                    owner=args.owner,
                    project_id=args.project_id,
                    profile=args.profile,
                    output_path=args.output,
                    run_id=args.run_id,
                )
                response = {"ok": True, "message": f"Completed portfolio tick in {args.mode} mode"}
                response.update(payload)
                return emit(response, args.json)
        if args.command == "campaign":
            if args.campaign_command == "list":
                campaigns = []
                from src.hive.store.campaigns import list_campaigns  # pylint: disable=import-outside-toplevel

                for campaign in list_campaigns(root):
                    if args.project_id and args.project_id not in campaign.project_ids:
                        continue
                    campaigns.append(campaign_status(root, campaign.id)["campaign"])
                return emit({"ok": True, "campaigns": campaigns}, args.json)
            if args.campaign_command == "create":
                payload = create_campaign_flow(
                    root,
                    title=args.title,
                    goal=args.goal,
                    project_ids=clean_string_list(args.project_id),
                    campaign_type=args.type,
                    driver=args.driver,
                    model=args.model,
                    sandbox_profile=(args.sandbox_profile or "").strip() or None,
                    cadence=args.cadence,
                    brief_cadence=args.brief_cadence,
                    max_active_runs=args.max_active_runs,
                    lane_quotas=_lane_quota_map(args.lane_quota),
                    budget_policy={
                        key: value
                        for key, value in {
                            "max_cost_usd": args.budget_cap_usd,
                            "max_tokens": args.budget_cap_tokens,
                        }.items()
                        if value is not None
                    }
                    or None,
                    escalation_policy=(
                        {"default_mode": str(args.escalation_mode).strip()}
                        if args.escalation_mode
                        else None
                    ),
                    notes_md=(args.notes or "").strip(),
                )
                sync_workspace(root)
                return emit({"ok": True} | payload, args.json)
            if args.campaign_command == "status":
                return emit({"ok": True} | campaign_status(root, args.campaign_id), args.json)
            if args.campaign_command == "tick":
                payload = tick_campaign(root, args.campaign_id, owner=args.owner)
                sync_workspace(root)
                return emit({"ok": True} | payload, args.json)
        if args.command == "brief":
            cadence = "daily" if args.brief_command == "daily" else "weekly"
            payload = generate_brief(root, cadence=cadence)
            sync_workspace(root)
            return emit({"ok": True} | payload, args.json)
    except (CacheBusyError, WorkspaceBusyError, FileNotFoundError, ValueError, sqlite3.Error) as exc:
        return emit_error(exc, args.json)
    return 0

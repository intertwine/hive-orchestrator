"""FastAPI backend for the Hive observe console."""

from __future__ import annotations

from importlib.resources import files
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel

from src.hive import __version__
from src.hive.console.state import build_home_view, build_inbox, list_runs, load_run_detail
from src.hive.control import campaign_status
from src.hive.context_bundle import build_context_bundle
from src.hive.drivers import SteeringRequest
from src.hive.program.doctor import doctor_program
from src.hive.search import search_workspace
from src.hive.store.campaigns import list_campaigns
from src.hive.runs.engine import steer_run
from src.hive.store.projects import discover_projects, get_project
from src.hive.workspace import sync_workspace


def _console_allow_origins() -> list[str]:
    configured = os.getenv("HIVE_CONSOLE_ALLOW_ORIGINS", "")
    return [item.strip() for item in configured.split(",") if item.strip()]


def _console_allow_origin_regex() -> str:
    return os.getenv(
        "HIVE_CONSOLE_ALLOW_ORIGIN_REGEX",
        r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    )


app = FastAPI(
    title="Hive Observe Console API",
    version=__version__,
    description="Observe-and-steer backend for the Hive 2.2 console.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_console_allow_origins(),
    allow_origin_regex=_console_allow_origin_regex(),
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class SteeringInput(BaseModel):
    """Typed steering request body for the console API."""

    action: str
    reason: str | None = None
    target: dict | None = None
    budget_delta: dict | None = None
    note: str | None = None
    actor: str | None = None


def _workspace_root(path: str | None = None) -> Path:
    configured = path or os.getenv("HIVE_BASE_PATH") or os.getcwd()
    return Path(configured).resolve()


def _console_asset_root() -> Path | None:
    source_root = Path(__file__).resolve().parent.parent / "resources" / "console"
    if source_root.exists():
        return source_root
    resource_package = f"{(__package__ or 'src.hive.console').rsplit('.', 1)[0]}.resources"
    packaged = files(resource_package).joinpath("console")
    candidate = Path(str(packaged))
    if candidate.exists():
        return candidate
    return None


@app.get("/")
def root_redirect() -> RedirectResponse:
    """Redirect the bare API root to the packaged console when available."""
    asset_root = _console_asset_root()
    if asset_root and (asset_root / "index.html").exists():
        return RedirectResponse(url="/console/", status_code=307)
    return RedirectResponse(url="/health", status_code=307)


@app.get("/console")
@app.get("/console/")
def console_index():
    """Serve the packaged React console when assets are available."""
    asset_root = _console_asset_root()
    if not asset_root:
        raise HTTPException(
            status_code=404,
            detail=(
                "Packaged console assets are not available in this build. "
                "Run the frontend build or use the API endpoints directly."
            ),
        )
    index_path = asset_root / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Console index.html is missing.")
    return FileResponse(index_path)


@app.get("/console/{asset_path:path}")
def console_assets(asset_path: str):
    """Serve packaged React console assets with SPA fallback."""
    asset_root = _console_asset_root()
    if not asset_root:
        raise HTTPException(status_code=404, detail="Console assets are not available.")
    target = (asset_root / asset_path).resolve()
    if target.exists() and target.is_file() and asset_root in target.parents:
        return FileResponse(target)
    index_path = asset_root / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Console index.html is missing.")
    return FileResponse(index_path)


@app.get("/health")
def health(path: str | None = Query(default=None)) -> dict:
    """Return a lightweight health payload for the console."""
    root = _workspace_root(path)
    return {
        "ok": True,
        "workspace": str(root),
        "version": app.version,
    }


@app.get("/status")
def status(path: str | None = Query(default=None)) -> dict:
    """Return lightweight workspace counts for the observe console shell."""
    root = _workspace_root(path)
    return {
        "ok": True,
        "workspace": str(root),
        "projects": len(discover_projects(root)),
        "runs": len(list_runs(root)),
        "inbox": len(build_inbox(root)),
    }


@app.get("/home")
def home(path: str | None = Query(default=None)) -> dict:
    """Return the main observe-console home payload."""
    root = _workspace_root(path)
    sync_workspace(root)
    return {"ok": True, "home": build_home_view(root)}


@app.get("/inbox")
def inbox(path: str | None = Query(default=None)) -> dict:
    """Return typed attention items for the operator inbox."""
    root = _workspace_root(path)
    sync_workspace(root)
    return {"ok": True, "items": build_inbox(root)}


@app.get("/runs")
def runs(
    path: str | None = Query(default=None),
    project_id: str | None = Query(default=None),
    driver: str | None = Query(default=None),
    health_status: str | None = Query(default=None, alias="health"),
    campaign_id: str | None = Query(default=None),
) -> dict:
    """Return the unified runs board payload."""
    root = _workspace_root(path)
    sync_workspace(root)
    return {
        "ok": True,
        "runs": list_runs(
            root,
            project_id=project_id,
            driver=driver,
            health=health_status,
            campaign_id=campaign_id,
        ),
    }


@app.get("/runs/{run_id}")
def run_detail(run_id: str, path: str | None = Query(default=None)) -> dict:
    """Return the detailed run payload for a single run."""
    root = _workspace_root(path)
    sync_workspace(root)
    try:
        detail = load_run_detail(root, run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "detail": detail}


@app.post("/runs/{run_id}/steer")
def run_steer(run_id: str, request: SteeringInput, path: str | None = Query(default=None)) -> dict:
    """Apply a typed steering action to a run."""
    root = _workspace_root(path)
    sync_workspace(root)
    try:
        payload = steer_run(
            root,
            run_id,
            SteeringRequest(
                action=request.action,
                reason=request.reason,
                target=request.target,
                budget_delta=request.budget_delta,
                note=request.note,
            ),
            actor=request.actor,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    sync_workspace(root)
    return {"ok": True, **payload}


@app.get("/projects")
def projects(path: str | None = Query(default=None)) -> dict:
    """Return discoverable projects for the console."""
    root = _workspace_root(path)
    sync_workspace(root)
    return {
        "ok": True,
        "projects": [
            {
                "id": project.id,
                "slug": project.slug,
                "title": project.title,
                "status": project.status,
                "priority": project.priority,
                "owner": project.owner,
                "path": str(project.agency_path),
                "program_path": str(project.program_path),
            }
            for project in discover_projects(root)
        ],
    }


@app.get("/campaigns")
def campaigns(path: str | None = Query(default=None)) -> dict:
    """Return campaign summaries for the observe console."""
    root = _workspace_root(path)
    sync_workspace(root)
    return {
        "ok": True,
        "campaigns": [
            {
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
            }
            for campaign in list_campaigns(root)
        ],
    }


@app.get("/campaigns/{campaign_id}")
def campaign_detail(campaign_id: str, path: str | None = Query(default=None)) -> dict:
    """Return one campaign plus its active/accepted runs."""
    root = _workspace_root(path)
    sync_workspace(root)
    try:
        return {"ok": True} | campaign_status(root, campaign_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/search")
def search(
    query: str = Query(...),
    path: str | None = Query(default=None),
    scope: list[str] | None = Query(default=None),
    limit: int = Query(default=8),
) -> dict:
    """Return unified search results for the console."""
    root = _workspace_root(path)
    sync_workspace(root)
    return {
        "ok": True,
        "results": search_workspace(root, query, scopes=scope, limit=limit),
    }


@app.get("/projects/{project_ref}/doctor")
def project_program_doctor(project_ref: str, path: str | None = Query(default=None)) -> dict:
    """Return a structured program doctor report for one project."""
    root = _workspace_root(path)
    sync_workspace(root)
    try:
        report = doctor_program(root, project_ref)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, "doctor": report}


@app.get("/projects/{project_ref}/context")
def project_context(
    project_ref: str,
    path: str | None = Query(default=None),
    mode: str = Query(default="startup"),
    profile: str = Query(default="light"),
) -> dict:
    """Return a rendered context bundle for a project."""
    root = _workspace_root(path)
    sync_workspace(root)
    try:
        project = get_project(root, project_ref)
        bundle = build_context_bundle(root, project_ref=project.id, mode=mode, profile=profile)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "ok": True,
        "project": {
            "id": project.id,
            "slug": project.slug,
            "title": project.title,
            "path": str(project.agency_path),
        },
        "rendered": str(bundle["rendered"]),
        "context": bundle["context"],
    }

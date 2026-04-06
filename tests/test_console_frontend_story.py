"""Lightweight smoke checks for the React observe-console scaffold."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_console_frontend_scaffold_exposes_the_primary_routes():
    """The new console scaffold should keep the RFC's command-center routes in place."""
    package_json = json.loads(
        (REPO_ROOT / "frontend" / "console" / "package.json").read_text(encoding="utf-8")
    )
    app_tsx = (REPO_ROOT / "frontend" / "console" / "src" / "App.tsx").read_text(
        encoding="utf-8"
    )
    readme = (REPO_ROOT / "frontend" / "console" / "README.md").read_text(encoding="utf-8")

    assert package_json["name"] == "@mellona-hive/console"
    assert package_json["scripts"]["dev"] == "vite"
    assert "Route index" in app_tsx
    assert 'path="home"' in app_tsx
    assert 'path="inbox"' in app_tsx
    assert 'path="runs"' in app_tsx
    assert 'path="runs/:runId"' in app_tsx
    assert 'path="campaigns"' in app_tsx
    assert 'path="projects"' in app_tsx
    assert 'path="search"' in app_tsx
    assert 'path="integrations"' in app_tsx
    assert 'path="notifications"' in app_tsx
    assert 'path="activity"' in app_tsx
    assert 'path="settings"' in app_tsx
    assert (REPO_ROOT / "frontend" / "console" / "src" / "routes" / "RunDetailPage.tsx").exists()
    assert (REPO_ROOT / "frontend" / "console" / "src" / "routes" / "IntegrationsPage.tsx").exists()
    assert (REPO_ROOT / "frontend" / "console" / "src" / "routes" / "NotificationsPage.tsx").exists()
    assert (REPO_ROOT / "frontend" / "console" / "src" / "routes" / "ActivityPage.tsx").exists()
    assert (REPO_ROOT / "frontend" / "console" / "src" / "routes" / "SettingsPage.tsx").exists()
    assert "hive console serve" in readme
    assert "Observe Console" in readme or "observe console" in readme.lower()

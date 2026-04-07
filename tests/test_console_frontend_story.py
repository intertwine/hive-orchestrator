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
    assert (
        REPO_ROOT / "frontend" / "console" / "src" / "routes" / "RunDetailPage.tsx"
    ).exists()
    assert (
        REPO_ROOT / "frontend" / "console" / "src" / "components" / "ConsoleEventBus.tsx"
    ).exists()
    assert (
        REPO_ROOT / "frontend" / "console" / "src" / "routes" / "IntegrationsPage.tsx"
    ).exists()
    assert (
        REPO_ROOT / "frontend" / "console" / "src" / "routes" / "NotificationsPage.tsx"
    ).exists()
    assert (
        REPO_ROOT / "frontend" / "console" / "src" / "routes" / "ActivityPage.tsx"
    ).exists()
    assert (
        REPO_ROOT / "frontend" / "console" / "src" / "routes" / "SettingsPage.tsx"
    ).exists()
    assert "hive console serve" in readme
    assert "Observe Console" in readme or "observe console" in readme.lower()


def test_console_desktop_bootstrap_stays_a_thin_wrapper():
    """The desktop beta should reuse the shared console frontend instead of forking it."""
    package_json = json.loads(
        (REPO_ROOT / "frontend" / "console" / "package.json").read_text(encoding="utf-8")
    )
    tauri_config = json.loads(
        (
            REPO_ROOT / "frontend" / "console" / "src-tauri" / "tauri.conf.json"
        ).read_text(encoding="utf-8")
    )
    capability = json.loads(
        (
            REPO_ROOT
            / "frontend"
            / "console"
            / "src-tauri"
            / "capabilities"
            / "default.json"
        ).read_text(encoding="utf-8")
    )
    readme = (
        REPO_ROOT / "frontend" / "console" / "README.md"
    ).read_text(encoding="utf-8")

    assert (
        package_json["scripts"]["desktop:dev"]
        == "vite --config vite.desktop.config.ts --host 127.0.0.1 --port 4175"
    )
    assert (
        package_json["scripts"]["desktop:build"]
        == "vite build --config vite.desktop.config.ts"
    )
    assert package_json["scripts"]["tauri:dev"] == "tauri dev"
    assert package_json["scripts"]["tauri:build"] == "tauri build"
    assert (
        package_json["scripts"]["tauri:check"] == "tauri build --debug --no-bundle"
    )
    assert package_json["devDependencies"]["@tauri-apps/cli"] == "2.10.1"
    assert tauri_config["productName"] == "Agent Hive Command Center"
    assert tauri_config["identifier"] == "com.intertwine.agent-hive"
    assert tauri_config["build"]["frontendDist"] == "../dist-desktop"
    assert tauri_config["build"]["devUrl"] == "http://127.0.0.1:4175"
    assert tauri_config["build"]["beforeDevCommand"] == "pnpm run desktop:dev"
    assert tauri_config["build"]["beforeBuildCommand"] == "pnpm run desktop:build"
    assert tauri_config["app"]["security"]["capabilities"] == ["default"]
    assert capability["permissions"] == ["core:default"]
    assert (REPO_ROOT / "frontend" / "console" / "vite.desktop.config.ts").exists()
    assert (REPO_ROOT / "frontend" / "console" / "vite.shared.ts").exists()
    assert "pnpm run tauri:dev" in readme
    assert "same React app" in readme
    assert "http://127.0.0.1:8787" in readme
    assert "hive console api" in readme

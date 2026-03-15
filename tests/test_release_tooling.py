"""Tests for packaging and release tooling."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tomllib

import yaml


def _load_module(module_name: str, relative_path: str):
    """Load a repository script as a Python module."""
    root = Path(__file__).resolve().parents[1]
    module_path = root / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError(f"Unable to load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_bump_version_only_updates_project_section(tmp_path):
    """Bumping should leave other version keys untouched."""
    module = _load_module("bump_version_script", "scripts/bump_version.py")
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(
        "\n".join(
            [
                "[project]",
                'name = "agent-hive"',
                'version = "1.2.3"',
                "",
                "[tool.demo]",
                'version = "keep-me"',
                "",
            ]
        ),
        encoding="utf-8",
    )

    old_version, new_version = module.update_pyproject_version(pyproject_path, "patch")
    rendered = pyproject_path.read_text(encoding="utf-8")

    assert old_version == "1.2.3"
    assert new_version == "1.2.4"
    assert 'version = "1.2.4"' in rendered
    assert 'version = "keep-me"' in rendered


def test_generate_homebrew_formula_uses_stable_help_assertion():
    """Generated formulas should exercise the real doctor JSON entrypoint."""
    module = _load_module("generate_homebrew_formula", "scripts/generate_homebrew_formula.py")
    source_artifact = module.Artifact(
        name="agent-hive",
        version="1.2.3",
        url="https://example.com/agent-hive-1.2.3.tar.gz",
        sha256="a" * 64,
    )
    wheel_artifact = module.Artifact(
        name="agent-hive",
        version="1.2.3",
        url="https://example.com/agent_hive-1.2.3-py3-none-any.whl",
        sha256="b" * 64,
    )

    formula = module.render_formula(
        class_name="AgentHive",
        desc="Hive test formula",
        homepage="https://example.com/agent-hive",
        root=source_artifact,
        root_wheel=wheel_artifact,
        license_name="MIT",
        python_dep="python@3.13",
        common_resources=[],
        arm_resources=[],
        intel_resources=[],
    )

    assert 'assert_match "\\"ok\\": true", shell_output("#{bin}/hive doctor --json")' in formula


def test_public_top_level_packages_are_available():
    """Installed users should see top-level hive packages, not just src.* imports."""
    hive = importlib.import_module("hive")
    hive_main = importlib.import_module("hive.__main__")
    hive_cli_main = importlib.import_module("hive.cli.main")
    hive_mcp = importlib.import_module("hive_mcp")
    hive_mcp_main = importlib.import_module("hive_mcp.__main__")
    hive_mcp_server = importlib.import_module("hive_mcp.server")

    assert hive.__version__
    assert callable(hive_main.main)
    assert callable(hive_cli_main.main)
    assert hive_mcp.__version__
    assert callable(hive_mcp_main.run)
    assert callable(hive_mcp_server.main)


def test_public_hive_module_entrypoint_exists():
    """`python -m hive` should resolve through a real public package module."""
    entrypoint = Path(__file__).resolve().parents[1] / "hive" / "__main__.py"
    assert entrypoint.exists()


def test_pyproject_all_extra_covers_optional_runtime_surfaces():
    """The convenience `all` extra should include every optional runtime surface."""
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    payload = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    extras = payload["project"]["optional-dependencies"]

    assert extras["all"] == [
        "streamlit>=1.51.0,<2.0.0",
        "mcp~=1.22.0",
        "fastapi>=0.115.0,<1.0.0",
        "uvicorn>=0.32.0,<1.0.0",
        "weave>=0.51.0,<1.0.0",
    ]


def test_opencode_mcp_command_requests_optional_extra():
    """The OpenCode MCP config should bootstrap the optional runtime dependency."""
    config_path = Path(__file__).resolve().parents[1] / ".opencode" / "opencode.json"
    payload = json.loads(config_path.read_text(encoding="utf-8"))

    assert payload["mcp"]["hive"]["command"] == ["uv", "run", "--extra", "mcp", "hive-mcp"]


def test_verify_claude_workspace_state_fails_when_ready_check_breaks(monkeypatch, capsys):
    """Workspace verification should fail if `hive task ready` cannot be read."""
    module = _load_module("verify_claude_app_script", "scripts/verify_claude_app.py")

    responses = iter(
        [
            {"checks": {"layout": True}, "projects": 1, "tasks": 3},
            None,
        ]
    )
    monkeypatch.setattr(module, "run_hive_json", lambda args: next(responses))

    assert module.check_workspace_state() is False
    captured = capsys.readouterr()
    assert "Could not read ready-task state" in captured.out


def test_release_smoke_script_exercises_python_module_entrypoint():
    """Release install smoke tests should cover `python -m hive`, not just console scripts."""
    script = (Path(__file__).resolve().parents[1] / "scripts" / "smoke_release_install.sh").read_text(
        encoding="utf-8"
    )

    assert '"$venv_dir/bin/python" -m hive --version >/dev/null' in script
    assert '"$venv_dir/bin/python" -m hive --path "$workspace" doctor --json >/dev/null' in script


def test_release_workflow_requires_tag_and_homebrew_verification():
    """Tagged releases should be gated by both tag validation and Homebrew verification."""
    workflow_path = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "release.yml"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))

    publish_steps = workflow["jobs"]["publish-pypi"]["steps"]
    guard_step = next(step for step in publish_steps if step["name"] == "Require a version tag ref")
    assert "refs/tags/v*" in guard_step["run"]

    verify_homebrew = workflow["jobs"]["verify-homebrew"]
    assert verify_homebrew["runs-on"] == "macos-latest"

    update_homebrew_needs = workflow["jobs"]["update-homebrew"]["needs"]
    assert update_homebrew_needs == ["publish-pypi", "verify-homebrew"]


def test_makefile_supports_overriding_homebrew_package_version():
    """Maintainers should be able to point formula generation at an already-published version."""
    makefile = (Path(__file__).resolve().parents[1] / "Makefile").read_text(encoding="utf-8")

    assert "HOMEBREW_PACKAGE_VERSION ?=" in makefile
    assert '--package-version "$(HOMEBREW_PACKAGE_VERSION)"' in makefile

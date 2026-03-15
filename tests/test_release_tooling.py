"""Tests for packaging and release tooling."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tomllib


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

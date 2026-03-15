"""Tests for packaging and release tooling."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


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
    """Generated formulas should assert on a stable help prefix."""
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

    assert 'assert_match "usage: hive", shell_output("#{bin}/hive --help")' in formula

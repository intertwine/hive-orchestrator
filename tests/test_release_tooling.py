"""Tests for packaging and release tooling."""

# pylint: disable=line-too-long,duplicate-code

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
                'name = "mellona-hive"',
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
        name="mellona-hive",
        version="1.2.3",
        url="https://example.com/mellona-hive-1.2.3.tar.gz",
        sha256="a" * 64,
    )

    formula = module.render_formula(
        class_name="MellonaHive",
        desc="Hive test formula",
        homepage="https://example.com/mellona-hive",
        root=source_artifact,
        license_name="MIT",
        python_dep="python@3.13",
        common_resources=[],
        arm_resources=[],
        intel_resources=[],
    )

    assert 'assert_match "\\"ok\\": true", shell_output("#{bin}/hive doctor --json")' in formula
    assert 'pip", "install", "--no-deps", "--no-build-isolation", buildpath' in formula


def test_generate_homebrew_formula_uses_platform_resource_blocks_and_short_desc():
    """Platform-specific wheels should nest inside one resource block and keep a short description."""
    module = _load_module(
        "generate_homebrew_formula_platform", "scripts/generate_homebrew_formula.py"
    )
    source_artifact = module.Artifact(
        name="mellona-hive",
        version="1.2.3",
        url="https://example.com/mellona-hive-1.2.3.tar.gz",
        sha256="a" * 64,
    )
    arm_pyyaml = module.Artifact(
        name="pyyaml",
        version="6.0.3",
        url="https://example.com/pyyaml-arm.whl",
        sha256="c" * 64,
    )
    intel_pyyaml = module.Artifact(
        name="pyyaml",
        version="6.0.3",
        url="https://example.com/pyyaml-intel.whl",
        sha256="d" * 64,
    )

    formula = module.render_formula(
        class_name="MellonaHive",
        desc="CLI-first orchestration platform for autonomous agents with Git-backed task, run, and memory state",
        homepage="https://example.com/mellona-hive",
        root=source_artifact,
        license_name="MIT",
        python_dep="python@3.13",
        common_resources=[],
        arm_resources=[arm_pyyaml],
        intel_resources=[intel_pyyaml],
    )

    assert '  desc "Git-backed control plane for autonomous agent work"' in formula
    assert '  depends_on "libyaml"' in formula
    assert '  resource "pyyaml" do' in formula
    assert "  on_arm do" in formula
    assert "  on_intel do" in formula
    assert '    url "https://example.com/pyyaml-arm.whl"' in formula
    assert '    url "https://example.com/pyyaml-intel.whl"' in formula
    assert '  on_arm do\n    resource "pyyaml"' not in formula
    assert 'resource "mellona-hive"' not in formula


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


def test_public_package_versions_match_pyproject():
    """Published package metadata and public module versions should stay aligned."""
    payload = tomllib.loads(
        (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    )
    expected = payload["project"]["version"]
    hive = importlib.import_module("hive")
    hive_mcp = importlib.import_module("hive_mcp")

    assert payload["project"]["name"] == "mellona-hive"
    assert hive.__version__ == expected
    assert hive_mcp.__version__ == expected


def test_public_hive_module_entrypoint_exists():
    """`python -m hive` should resolve through a real public package module."""
    entrypoint = Path(__file__).resolve().parents[1] / "hive" / "__main__.py"
    assert entrypoint.exists()


def test_pyproject_runtime_extras_cover_console_and_optional_surfaces():
    """Runtime extras should keep the console alias and convenience bundle aligned."""
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    payload = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    extras = payload["project"]["optional-dependencies"]

    assert extras["dashboard"] == [
        "fastapi>=0.115.0,<1.0.0",
        "uvicorn>=0.32.0,<1.0.0",
    ]
    assert extras["console"] == [
        "fastapi>=0.115.0,<1.0.0",
        "uvicorn>=0.32.0,<1.0.0",
    ]
    assert extras["drivers-claude"] == [
        "claude-code-sdk>=0.0.25,<1.0.0",
    ]
    assert extras["sandbox-e2b"] == [
        "e2b>=2.2.5,<3.0.0",
    ]
    assert extras["sandbox-daytona"] == [
        "daytona>=0.152.0,<1.0.0",
    ]
    assert extras["all"] == [
        "claude-code-sdk>=0.0.25,<1.0.0",
        "e2b>=2.2.5,<3.0.0",
        "daytona>=0.152.0,<1.0.0",
        "mcp~=1.22.0",
        "fastapi>=0.115.0,<1.0.0",
        "uvicorn>=0.32.0,<1.0.0",
        "weave>=0.51.0,<1.0.0",
        "lancedb>=0.20.0,<1.0.0",
        "fastembed>=0.5.0,<1.0.0",
    ]
    assert extras["retrieval"] == [
        "lancedb>=0.20.0,<1.0.0",
        "fastembed>=0.5.0,<1.0.0",
    ]


def test_release_guide_and_smoke_script_cover_sandbox_doctor():
    """Public release verification should exercise the packaged sandbox doctor surface."""
    release_doc = (Path(__file__).resolve().parents[1] / "docs" / "RELEASING.md").read_text(
        encoding="utf-8"
    )
    smoke_script = (
        Path(__file__).resolve().parents[1] / "scripts" / "smoke_release_install.sh"
    ).read_text(encoding="utf-8")

    assert 'hive --path "$release_verify_dir" sandbox doctor --json' in release_doc
    assert './pip-verify/bin/hive --path "$release_verify_dir" sandbox doctor --json' in release_doc
    assert (
        'pipx run --spec mellona-hive hive --path "$release_verify_dir" sandbox doctor --json'
        in release_doc
    )
    assert '"$hive_bin" --path "$workspace" sandbox doctor --json >/dev/null' in smoke_script
    assert '"$pipx_bin/hive" --path "$workspace" sandbox doctor --json >/dev/null' in smoke_script
    assert '"$venv_dir/bin/hive" --path "$workspace" sandbox doctor --json >/dev/null' in smoke_script
    assert "HIVE_RUN_E2B_ACCEPTANCE=1" in release_doc
    assert "tests/test_remote_sandbox_acceptance.py -k e2b -q" in release_doc
    assert "HIVE_RUN_DAYTONA_ACCEPTANCE=1" in release_doc
    assert "tests/test_remote_sandbox_acceptance.py -k daytona -q" in release_doc
    assert "do not prove these sandbox extras" in release_doc


def test_wheel_force_include_does_not_duplicate_recipe_files():
    """Wheel force-include rules should not map a directory and its files twice."""
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    payload = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    force_include = payload["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]

    assert "docs/recipes" in force_include
    assert "docs/recipes/observe-and-steer.md" not in force_include
    assert "docs/recipes/program-doctor.md" not in force_include
    assert "docs/recipes/driver-handoffs.md" not in force_include


def test_wheel_force_include_uses_repo_docs_as_the_only_markdown_source():
    """Packaged docs should come from repo docs at build time, not checked-in mirrors."""
    repo_root = Path(__file__).resolve().parents[1]
    pyproject = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))
    force_include = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
    docs_dir = repo_root / "src" / "hive" / "resources" / "docs"
    mirror_files = sorted(
        str(path.relative_to(repo_root))
        for path in (docs_dir.rglob("*") if docs_dir.exists() else [])
        if path.is_file()
    )

    assert force_include["README.md"] == "src/hive/resources/docs/README.md"
    assert force_include["docs/START_HERE.md"] == "src/hive/resources/docs/START_HERE.md"
    assert force_include["docs/QUICKSTART.md"] == "src/hive/resources/docs/QUICKSTART.md"
    assert (
        force_include["docs/ADOPT_EXISTING_REPO.md"]
        == "src/hive/resources/docs/ADOPT_EXISTING_REPO.md"
    )
    assert force_include["docs/V2_4_STATUS.md"] == "src/hive/resources/docs/V2_4_STATUS.md"
    assert force_include["docs/V2_5_STATUS.md"] == "src/hive/resources/docs/V2_5_STATUS.md"
    assert force_include["docs/hive-v2.4-rfc"] == "src/hive/resources/docs/hive-v2.4-rfc"
    assert (
        force_include["docs/hive-post-v2.4-rfcs"]
        == "src/hive/resources/docs/hive-post-v2.4-rfcs"
    )
    assert mirror_files == []


def test_packaged_search_indexes_v25_status_and_planning_docs():
    """Installed API search should expose the active v2.5 ledger and planning corpus."""
    search_source = (Path(__file__).resolve().parents[1] / "src" / "hive" / "search.py").read_text(
        encoding="utf-8"
    )

    assert '"docs/V2_5_STATUS.md"' in search_source
    assert '"docs/hive-post-v2.4-rfcs/docs/HANDOFF_TO_CODEX.md"' in search_source
    assert (
        '"docs/hive-post-v2.4-rfcs/docs/hive-v2.5-rfc/HIVE_V2_5_COMMAND_CENTER_RFC.md"'
        in search_source
    )


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
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "smoke_release_install.sh"
    script = script_path.read_text(encoding="utf-8")

    assert '"$venv_dir/bin/python" -m hive --path "$workspace" doctor --json >/dev/null' in script
    assert '"$venv_dir/bin/python" -m hive --version >/dev/null' in script


def test_release_smoke_script_prefers_supported_python():
    """Release install smoke checks should use the pinned release interpreter contract."""
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "smoke_release_install.sh"
    script = script_path.read_text(encoding="utf-8")

    assert 'DIST_PACKAGE_NAME="${DIST_PACKAGE_NAME:-mellona-hive}"' in script
    assert 'RELEASE_PYTHON_VERSION="${RELEASE_PYTHON_VERSION:-3.11}"' in script
    assert "resolve_release_python_bin()" in script
    assert 'uv python find --no-project "$RELEASE_PYTHON_VERSION"' in script
    assert 'uv python install "$RELEASE_PYTHON_VERSION"' in script
    assert 'WHEEL_GLOB="${DIST_PACKAGE_NAME//-/_}-*.whl"' in script
    assert 'python_bin="$(resolve_release_python_bin)"' in script
    assert 'uv tool install --force --from "$WHEEL_PATH" "$DIST_PACKAGE_NAME"' in script
    assert "python3 -m venv" not in script
    assert "command -v python3 || command -v python" not in script


def test_release_smoke_script_proves_installed_search_usefulness():
    """Release install smoke should verify packaged search results, not only init/doctor."""
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "smoke_release_install.sh"
    script = script_path.read_text(encoding="utf-8")

    assert "run_installed_search_smoke()" in script
    assert "assert_search_payload()" in script
    assert '"$hive_bin" --path "$workspace" search "runtime contract" --scope api --limit 5 --json' in script
    assert '"$hive_bin" --path "$workspace" search "DelegateGatewayAdapter" --scope api --limit 5 --json' in script
    assert '"$hive_bin" --path "$workspace" search "sandbox doctor" --scope examples --limit 5 --json' in script
    assert "package:docs/hive-v2.3-rfc/HIVE_V2_3_RUNTIME_AND_SANDBOX_SPEC.md" in script
    assert "package:docs/hive-v2.4-rfc/HIVE_V2_4_ADAPTER_MODEL_AND_LINK_SPEC.md" in script
    assert "package:docs/recipes/sandbox-doctor.md" in script


def test_release_workflow_requires_tag_and_homebrew_verification():
    """Tagged releases should be gated by both tag validation and Homebrew verification."""
    workflow_path = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "release.yml"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    workflow_text = workflow_path.read_text(encoding="utf-8")

    assert workflow["env"]["DIST_PACKAGE_NAME"] == "mellona-hive"
    assert workflow["env"]["HOMEBREW_FORMULA_NAME"] == "mellona-hive"
    publish_steps = workflow["jobs"]["publish-pypi"]["steps"]
    guard_step = next(
        (step for step in publish_steps if step["name"] == "Require a version tag ref"),
        None,
    )
    assert guard_step is not None, "Missing 'Require a version tag ref' step in publish-pypi"
    assert "refs/tags/v*" in guard_step["run"]
    assert (
        "ref: ${{ github.event_name == 'workflow_dispatch' && format('refs/tags/{0}', inputs.release_ref) || github.ref }}"
        in workflow_text
    )
    assert (
        "skip-existing: ${{ github.event_name == 'workflow_dispatch' && inputs.skip_existing || false }}"
        in workflow_text
    )
    assert publish_steps[1]["name"] == "Require a version tag ref"
    workflow_on = workflow.get("on", workflow.get(True))
    dispatch_inputs = workflow_on["workflow_dispatch"]["inputs"]
    assert dispatch_inputs["release_ref"]["required"] is True
    assert dispatch_inputs["skip_existing"]["default"] is False

    verify_homebrew = workflow["jobs"]["verify-homebrew"]
    assert verify_homebrew["runs-on"] == "macos-latest"

    update_homebrew_needs = workflow["jobs"]["update-homebrew"]["needs"]
    assert update_homebrew_needs == ["publish-pypi", "verify-homebrew"]
    assert "git status --porcelain -- Formula/${{ env.HOMEBREW_FORMULA_NAME }}.rb" in workflow_text


def test_makefile_supports_overriding_homebrew_package_version():
    """Maintainers should be able to point formula generation at an already-published version."""
    makefile = (Path(__file__).resolve().parents[1] / "Makefile").read_text(encoding="utf-8")

    assert "HOMEBREW_PACKAGE_VERSION ?=" in makefile
    assert '--package-version "$(HOMEBREW_PACKAGE_VERSION)"' in makefile


def test_makefile_supports_overriding_release_python_version():
    """Release smoke checks should use the same pinned interpreter contract as CI."""
    makefile = (Path(__file__).resolve().parents[1] / "Makefile").read_text(encoding="utf-8")

    assert "RELEASE_PYTHON_VERSION ?= 3.11" in makefile
    assert "DIST_PACKAGE_NAME ?= mellona-hive" in makefile
    assert "HOMEBREW_FORMULA_NAME ?= mellona-hive" in makefile
    assert (
        'DIST_PACKAGE_NAME="$(DIST_PACKAGE_NAME)" RELEASE_PYTHON_VERSION="$(RELEASE_PYTHON_VERSION)" ./scripts/smoke_release_install.sh'
        in makefile
    )


def test_makefile_clean_removes_stale_release_artifacts():
    """Release builds should start from a clean dist/build state."""
    makefile = (Path(__file__).resolve().parents[1] / "Makefile").read_text(encoding="utf-8")

    assert "rm -rf dist build ./*.egg-info" in makefile


def test_releasing_guide_derives_the_tagged_version_from_pyproject():
    """Release docs should avoid hardcoded version examples that go stale."""
    guide = (Path(__file__).resolve().parents[1] / "docs" / "RELEASING.md").read_text(
        encoding="utf-8"
    )

    assert "VERSION=\"$(uv run python - <<'PY'" in guide
    assert 'git commit -m "Release v${VERSION}"' in guide
    assert 'git tag "v${VERSION}"' in guide

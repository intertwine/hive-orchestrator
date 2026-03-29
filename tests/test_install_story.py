"""Regression checks for the public install and launch story."""

# pylint: disable=line-too-long,duplicate-code

from __future__ import annotations

from pathlib import Path
import tomllib


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_package_metadata_points_users_at_public_start_here_docs():
    """PyPI metadata should send users to the product docs, not the maintainer README."""
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["readme"] == {
        "file": "docs/PYPI_README.md",
        "content-type": "text/markdown",
    }
    assert pyproject["project"]["urls"]["Documentation"].endswith("/docs/START_HERE.md")
    assert (
        "docs/PYPI_README.md"
        in pyproject["tool"]["hatch"]["build"]["targets"]["sdist"]["only-include"]
    )
    assert "docs" not in pyproject["tool"]["hatch"]["build"]["targets"]["sdist"]["only-include"]


def test_packaged_docs_include_v23_rfc_corpus():
    """Installed search should retain the v2.3 RFC bundle."""
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    force_include = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
    sdist_only_include = pyproject["tool"]["hatch"]["build"]["targets"]["sdist"]["only-include"]

    assert "docs/hive-v2.3-rfc" in force_include
    assert "docs/hive-v2.3-rfc" in sdist_only_include


def test_packaged_docs_include_v24_status_and_rfc_corpus():
    """Installed search should retain the v2.4 ledger and RFC bundle."""
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    force_include = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
    sdist_only_include = pyproject["tool"]["hatch"]["build"]["targets"]["sdist"]["only-include"]

    assert "docs/V2_4_STATUS.md" in force_include
    assert "docs/hive-v2.4-rfc" in force_include
    assert "docs/V2_4_STATUS.md" in sdist_only_include
    assert "docs/hive-v2.4-rfc" in sdist_only_include


def test_public_readmes_surface_three_clear_entry_points():
    """User-facing docs should separate fresh installs, existing repos, and maintainers."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    start_here = (REPO_ROOT / "docs" / "START_HERE.md").read_text(encoding="utf-8")
    pypi_readme = (REPO_ROOT / "docs" / "PYPI_README.md").read_text(encoding="utf-8")

    assert "Install Hive" in readme
    assert "Adopt Hive In An Existing Repo" in readme
    assert "Maintain or publish Hive" in readme
    assert "control plane" in readme.lower()
    assert "Mellona" in readme
    assert "Keep your agent. Add a control plane." in readme
    assert "Try It In 90 Seconds" in readme
    assert "Pi" in readme
    assert "OpenClaw" in readme
    assert "Hermes" in readme
    assert "Native Harnesses" in readme

    assert "Fresh Workspace" in start_here
    assert "Existing Repo" in start_here
    assert "Maintainers" in start_here
    assert "Native Harness Paths" in start_here
    assert "Mellona" in start_here
    assert "Create a small React website about bees." in start_here
    assert "run worktree" in start_here
    assert "Pi harness guide" in start_here
    assert "OpenClaw harness guide" in start_here
    assert "Hermes harness guide" in start_here

    assert "make install-dev" not in pypi_readme
    assert "src.agent_dispatcher" not in pypi_readme
    assert "Mellona" in pypi_readme
    assert "Keep your agent. Add a control plane." in pypi_readme
    assert "Create a small React website about bees." in pypi_readme
    assert "run worktree" in pypi_readme
    assert "Pi" in pypi_readme
    assert "OpenClaw" in pypi_readme
    assert "Hermes" in pypi_readme


def test_public_docs_recommend_console_extra_in_install():
    """Install docs should recommend the console extra as the default install path."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    start_here = (REPO_ROOT / "docs" / "START_HERE.md").read_text(encoding="utf-8")
    quickstart = (REPO_ROOT / "docs" / "QUICKSTART.md").read_text(encoding="utf-8")
    pypi_readme = (REPO_ROOT / "docs" / "PYPI_README.md").read_text(encoding="utf-8")

    # Console should be in the primary install command, not relegated to optional extras
    assert "mellona-hive[console]" in readme
    assert "mellona-hive[console]" in start_here
    assert "mellona-hive[console]" in quickstart
    assert "mellona-hive[console]" in pypi_readme
    # CLI-only install should still be documented as an alternative
    assert "cli-only" in readme.lower()
    assert "cli-only" in start_here.lower()


def test_public_docs_cover_sandbox_extras_and_doctor_recipe():
    """Install docs should explain sandbox extras and point at sandbox doctor guidance."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    start_here = (REPO_ROOT / "docs" / "START_HERE.md").read_text(encoding="utf-8")
    quickstart = (REPO_ROOT / "docs" / "QUICKSTART.md").read_text(encoding="utf-8")
    pypi_readme = (REPO_ROOT / "docs" / "PYPI_README.md").read_text(encoding="utf-8")
    operator_flows = (REPO_ROOT / "docs" / "OPERATOR_FLOWS.md").read_text(encoding="utf-8")
    sandbox_doc = (REPO_ROOT / "docs" / "recipes" / "sandbox-doctor.md").read_text(
        encoding="utf-8"
    )

    assert "mellona-hive[sandbox-e2b]" in readme
    assert "mellona-hive[sandbox-daytona]" in readme
    assert "hive sandbox doctor --json" in readme
    assert "mellona-hive[sandbox-e2b]" in start_here
    assert "mellona-hive[sandbox-daytona]" in start_here
    assert "hive sandbox doctor --json" in start_here
    assert "hive sandbox doctor --json" in quickstart
    assert "mellona-hive[sandbox-e2b]" in pypi_readme
    assert "mellona-hive[sandbox-daytona]" in pypi_readme
    assert "hive sandbox doctor --json" in operator_flows
    assert "local-fast` is weaker than `local-safe" in sandbox_doc
    assert "HIVE_DAYTONA_SNAPSHOT" in sandbox_doc
    assert "supports network modes `deny` and `inherit` only" in sandbox_doc


def test_onboarding_docs_explain_local_smoke_is_only_a_placeholder():
    """Onboarding docs should distinguish a wired-up loop from a real quality gate."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    quickstart = (REPO_ROOT / "docs" / "QUICKSTART.md").read_text(encoding="utf-8")
    pypi_readme = (REPO_ROOT / "docs" / "PYPI_README.md").read_text(encoding="utf-8")
    recipe = (REPO_ROOT / "docs" / "recipes" / "program-doctor.md").read_text(encoding="utf-8")

    assert "placeholder `local-smoke` evaluator" in readme
    assert "does not validate project behavior" in quickstart
    assert "placeholder `local-smoke` evaluator" in pypi_readme
    assert "bootstrap placeholder" in recipe


def test_pypi_readme_keeps_mcp_as_an_optional_extra():
    """The package README should not imply the thin MCP adapter is part of the base install."""
    pypi_readme = (REPO_ROOT / "docs" / "PYPI_README.md").read_text(encoding="utf-8")

    assert "mellona-hive[console]" in pypi_readme
    assert "mellona-hive[mcp]" in pypi_readme


def test_start_here_install_matrix_covers_common_installers_and_homebrew_limit():
    """Everyday users should see the real install choices and the Homebrew boundary."""
    start_here = (REPO_ROOT / "docs" / "START_HERE.md").read_text(encoding="utf-8")

    assert "uv tool install" in start_here
    assert "pipx install" in start_here
    assert "python -m pip install" in start_here
    assert "brew install intertwine/tap/mellona-hive" in start_here
    assert "Base CLI only" in start_here or "base CLI" in start_here.lower()


def test_native_harness_recipe_docs_exist_and_surface_integrate_doctor_paths():
    """The v2.4 harness-native onboarding guides should be checked in and diagnosable."""
    pi = (REPO_ROOT / "docs" / "recipes" / "pi-harness.md").read_text(encoding="utf-8")
    openclaw = (REPO_ROOT / "docs" / "recipes" / "openclaw-harness.md").read_text(
        encoding="utf-8"
    )
    hermes = (REPO_ROOT / "docs" / "recipes" / "hermes-harness.md").read_text(
        encoding="utf-8"
    )

    assert "hive integrate doctor pi --json" in pi
    assert "pi-hive open" in pi
    assert "pi-hive attach" in pi
    assert "hive integrate doctor openclaw --json" in openclaw
    assert "hive integrate attach openclaw" in openclaw
    assert "attach-only in v2.4" in openclaw
    assert "hive integrate doctor hermes --json" in hermes
    assert "hive integrate attach hermes" in hermes
    assert "never bulk-imported automatically" in hermes


def test_existing_repo_guide_surfaces_init_and_migration_paths():
    """Existing-repo adoption should be easy to find and should cover legacy migration."""
    adopt = (REPO_ROOT / "docs" / "ADOPT_EXISTING_REPO.md").read_text(encoding="utf-8")

    assert "hive adopt app" in adopt
    assert "hive init" in adopt
    assert "hive console serve" in adopt
    assert "hive migrate v1-to-v2 --dry-run" in adopt
    assert "hive migrate v1-to-v2 --rewrite" in adopt


def test_makefile_marks_itself_as_a_checkout_surface():
    """The root Makefile should read as a maintainer toolbelt."""
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

    assert "AGENT HIVE - MAINTAINER COMMANDS" in makefile
    assert "Installed users should use the `hive` CLI directly." in makefile
    assert "dev-quickstart:" in makefile
    assert "make quickstart is a maintainer shortcut from a source checkout." in makefile
    assert "Maintainers can use: make dev-quickstart" in makefile


def test_claude_app_doc_keeps_dispatcher_diagnostics_in_checkout_only_section():
    """The GitHub App guide should keep checkout-only diagnostics out of the normal user path."""
    install_doc = (REPO_ROOT / "docs" / "INSTALL_CLAUDE_APP.md").read_text(encoding="utf-8")
    before_checkout_only, after_checkout_only = install_doc.split(
        "## Checkout-only dispatcher diagnostics",
        1,
    )

    assert "uv run python -m src.agent_dispatcher --dry-run" not in before_checkout_only
    assert "uv run python -m src.agent_dispatcher --dry-run" in after_checkout_only


def test_release_guide_uses_throwaway_dirs_for_public_install_verification():
    """Release verification should exercise packaged installs in clean directories."""
    release_doc = (REPO_ROOT / "docs" / "RELEASING.md").read_text(encoding="utf-8")

    assert "release_verify_dir=$(mktemp -d)" in release_doc
    assert "Do not run these" in release_doc
    assert "maintainer checkout" in release_doc
    assert "workspace_dir=$(mktemp -d)" in release_doc
    assert "./pip-verify/bin/hive --version" in release_doc
    assert "./pip-verify/bin/hive doctor --json" in release_doc
    assert 'hive onboard demo --prompt "Create a small React website about bees."' in release_doc

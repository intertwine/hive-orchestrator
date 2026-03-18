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
    assert "docs/PYPI_README.md" in pyproject["tool"]["hatch"]["build"]["targets"]["sdist"]["only-include"]
    assert "docs" not in pyproject["tool"]["hatch"]["build"]["targets"]["sdist"]["only-include"]


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

    assert "Fresh Workspace" in start_here
    assert "Existing Repo" in start_here
    assert "Maintainers" in start_here
    assert "Mellona" in start_here

    assert "make install-dev" not in pypi_readme
    assert "src.agent_dispatcher" not in pypi_readme
    assert "Mellona" in pypi_readme


def test_start_here_install_matrix_covers_common_installers_and_homebrew_limit():
    """Everyday users should see the real install choices and the Homebrew boundary."""
    start_here = (REPO_ROOT / "docs" / "START_HERE.md").read_text(encoding="utf-8")

    assert "uv tool install mellona-hive" in start_here
    assert "pipx install mellona-hive" in start_here
    assert "python -m pip install mellona-hive" in start_here
    assert "brew install intertwine/tap/mellona-hive" in start_here
    assert "Homebrew currently ships the base CLI" in start_here


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
    assert "hive quickstart demo --title \"Demo project\"" in release_doc

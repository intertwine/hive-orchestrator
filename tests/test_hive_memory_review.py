"""Tests for memory delta proposal and review flows."""

# pylint: disable=missing-function-docstring,missing-class-docstring,unused-argument
# pylint: disable=import-error,no-name-in-module,line-too-long,too-few-public-methods
# pylint: disable=duplicate-code

from __future__ import annotations

import json
from pathlib import Path

from hive.cli.main import main as hive_main
from src.hive.store.projects import create_project


def _invoke_cli_json(capsys, argv: list[str]) -> dict:
    exit_code = hive_main(argv)
    captured = capsys.readouterr()
    assert exit_code == 0
    return json.loads(captured.out)


class TestMemoryReview:
    """Memory synthesis should support propose/accept/reject review loops."""

    def test_memory_propose_accept_and_reject(self, temp_hive_dir, capsys):
        create_project(temp_hive_dir, "demo", title="Demo")
        _invoke_cli_json(
            capsys,
            [
                "--path",
                temp_hive_dir,
                "--json",
                "memory",
                "observe",
                "--project",
                "demo",
                "--note",
                "The team prefers small, reviewable slices.",
            ],
        )

        proposed = _invoke_cli_json(
            capsys,
            [
                "--path",
                temp_hive_dir,
                "--json",
                "memory",
                "reflect",
                "--project",
                "demo",
                "--propose",
            ],
        )
        assert proposed["paths"]["profile"].endswith("profile.proposed.md")
        assert Path(proposed["paths"]["review"]).exists()

        accepted = _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "memory", "accept", "--project", "demo"],
        )
        assert accepted["paths"]["profile"].endswith("profile.md")
        assert Path(accepted["paths"]["profile"]).exists()

        _invoke_cli_json(
            capsys,
            [
                "--path",
                temp_hive_dir,
                "--json",
                "memory",
                "reflect",
                "--project",
                "demo",
                "--propose",
            ],
        )
        rejected = _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "memory", "reject", "--project", "demo"],
        )
        assert rejected["paths"]["profile"].endswith("profile.proposed.md")

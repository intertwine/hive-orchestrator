"""Tests for Hive 2.2 Program Doctor flows."""

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


class TestProgramDoctor:
    """Program Doctor should explain policy gaps and offer guided fixes."""

    def test_doctor_program_suggests_stack_template_and_flags_missing_gates(
        self, temp_hive_dir, capsys
    ):
        create_project(temp_hive_dir, "demo", title="Demo")
        (Path(temp_hive_dir) / "pyproject.toml").write_text(
            "[project]\nname = 'demo'\nversion = '0.1.0'\n",
            encoding="utf-8",
        )
        (Path(temp_hive_dir) / "tests").mkdir()

        payload = _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "doctor", "program", "demo"],
        )

        issue_codes = {issue["code"] for issue in payload["issues"]}
        assert payload["status"] == "fail"
        assert payload["blocked_autonomous_promotion"] is True
        assert "missing_required_evaluator" in issue_codes
        assert payload["suggested_templates"][0]["id"] == "pytest"

    def test_program_add_evaluator_applies_template_and_unblocks_program(self, temp_hive_dir, capsys):
        create_project(temp_hive_dir, "demo", title="Demo")
        (Path(temp_hive_dir) / "pyproject.toml").write_text(
            "[project]\nname = 'demo'\nversion = '0.1.0'\n",
            encoding="utf-8",
        )
        (Path(temp_hive_dir) / "tests").mkdir()

        applied = _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "program", "add-evaluator", "demo", "pytest"],
        )
        follow_up = _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "program", "doctor", "demo"],
        )

        assert applied["applied_template"]["id"] == "pytest"
        assert follow_up["blocked_autonomous_promotion"] is False
        assert follow_up["status"] in {"pass", "warn"}

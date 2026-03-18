"""Tests for Hive 2.2 Program Doctor flows."""

# pylint: disable=missing-function-docstring,missing-class-docstring,unused-argument
# pylint: disable=import-error,no-name-in-module,line-too-long,too-few-public-methods

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

    def test_doctor_program_blank_repo_suggests_generic_starter_template(
        self, temp_hive_dir, capsys
    ):
        create_project(temp_hive_dir, "demo", title="Demo")

        payload = _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "doctor", "program", "demo"],
        )

        issue_codes = {issue["code"] for issue in payload["issues"]}
        missing_required = next(
            issue for issue in payload["issues"] if issue["code"] == "missing_required_evaluator"
        )
        assert payload["status"] == "fail"
        assert payload["blocked_autonomous_promotion"] is True
        assert "missing_required_evaluator" in issue_codes
        assert payload["suggested_templates"][0]["id"] == "local-smoke"
        assert missing_required["suggested_command"] == "hive program add-evaluator demo local-smoke"

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
        assert follow_up["status"] == "pass"
        assert follow_up["headline"] == "PROGRAM.md looks healthy"
        assert follow_up["program_summary"]["evaluator_count"] == 1
        assert follow_up["program_summary"]["promotion_gate_active"] is True
        assert "1 evaluator configured" in follow_up["summary_lines"]
        assert "promotion gate active" in follow_up["summary_lines"]

    def test_program_add_evaluator_applies_generic_template_in_blank_repo(
        self, temp_hive_dir, capsys
    ):
        create_project(temp_hive_dir, "demo", title="Demo")

        applied = _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "program", "add-evaluator", "demo", "local-smoke"],
        )
        follow_up = _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "program", "doctor", "demo"],
        )

        assert applied["applied_template"]["id"] == "local-smoke"
        assert applied["applied_template"]["command"] == "python3 -c \"print('local smoke ok')\""
        assert follow_up["blocked_autonomous_promotion"] is False
        assert follow_up["status"] == "pass"
        assert follow_up["program_summary"]["starter_evaluator_in_place"] is True
        assert "starter evaluator still in place" in follow_up["summary_lines"]

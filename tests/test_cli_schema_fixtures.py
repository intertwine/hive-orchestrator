"""Fixture-backed CLI schema checks for the v2.2 manager loop."""

# pylint: disable=missing-function-docstring,missing-class-docstring,unused-argument
# pylint: disable=import-error,no-name-in-module,line-too-long,too-few-public-methods
# pylint: disable=too-many-return-statements,duplicate-code

from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any

import pytest

from hive.cli.main import main as hive_main

from src.hive.store.task_files import create_task
from tests.conftest import init_git_repo, write_safe_program


REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(name="schema_fixture")
def fixture_schema_fixture() -> dict[str, Any]:
    """Load the CLI contract fixture with a test-scoped failure if it is missing or malformed."""
    return json.loads(
        (REPO_ROOT / "tests" / "fixtures" / "cli_schema" / "v2_2_manager_loop.json").read_text(
            encoding="utf-8"
        )
    )


def _invoke_cli_json(capsys, argv: list[str]) -> dict[str, Any]:
    exit_code = hive_main(argv)
    captured = capsys.readouterr()
    assert exit_code == 0, captured.err
    return json.loads(captured.out)


def _commit_all(root: Path, message: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )


def _collect_path_values(payload: dict[str, Any], path: str) -> list[Any]:
    # The fixture DSL is intentionally strict today. Every referenced path must exist, so future
    # optional fields should either get a new schema marker or stay out of this contract fixture.
    values: list[Any] = [payload]
    for segment in path.split("."):
        expand_list = segment.endswith("[]")
        key = segment[:-2] if expand_list else segment
        next_values: list[Any] = []
        for value in values:
            assert isinstance(value, dict), f"Path {path!r} expected object at {segment!r}: {value!r}"
            assert key in value, f"Path {path!r} is missing key {key!r}"
            child = value[key]
            if expand_list:
                assert isinstance(child, list), f"Path {path!r} expected list at {segment!r}"
                next_values.extend(child)
            else:
                next_values.append(child)
        values = next_values
    return values


def _value_for_compare(path: str, payload: dict[str, Any]) -> Any:
    values = _collect_path_values(payload, path)
    if "[]" not in path and len(values) == 1:
        return values[0]
    return values


def _matches_type(value: Any, expected: str) -> bool:
    type_names = [item.strip() for item in expected.split("|")]
    for type_name in type_names:
        if type_name == "string" and isinstance(value, str):
            return True
        if type_name == "boolean" and isinstance(value, bool):
            return True
        if type_name == "integer" and isinstance(value, int) and not isinstance(value, bool):
            return True
        if type_name == "number" and isinstance(value, (int, float)) and not isinstance(value, bool):
            return True
        if type_name == "list" and isinstance(value, list):
            return True
        if type_name == "object" and isinstance(value, dict):
            return True
        if type_name == "null" and value is None:
            return True
    return False


def _assert_schema(command_name: str, payload: dict[str, Any], schema: dict[str, Any]) -> None:
    for path in schema.get("non_empty", []):
        value = _value_for_compare(path, payload)
        if isinstance(value, list):
            assert value, f"{command_name}: expected non-empty {path}"
        elif isinstance(value, dict):
            assert value, f"{command_name}: expected non-empty object at {path}"
        elif isinstance(value, str):
            assert value.strip(), f"{command_name}: expected non-empty string at {path}"
        else:
            assert value is not None, f"{command_name}: expected value at {path}"

    for path, expected_type in schema.get("types", {}).items():
        values = _collect_path_values(payload, path)
        assert values, f"{command_name}: no values found for {path}"
        for value in values:
            assert _matches_type(value, expected_type), (
                f"{command_name}: {path} expected {expected_type}, got {type(value).__name__}: {value!r}"
            )

    for path, expected in schema.get("equals", {}).items():
        actual = _value_for_compare(path, payload)
        assert actual == expected, f"{command_name}: {path} expected {expected!r}, got {actual!r}"

    for path, expected_values in schema.get("contains", {}).items():
        actual = _value_for_compare(path, payload)
        haystack = actual if isinstance(actual, list) else [actual]
        for expected in expected_values:
            assert expected in haystack, f"{command_name}: {path} missing {expected!r} in {haystack!r}"


def _build_cli_payloads(temp_hive_dir: str, capsys) -> dict[str, dict[str, Any]]:
    # This helper is intentionally sequential because later manager-loop payloads depend on earlier
    # setup state: onboarded project -> committed workspace -> active run -> campaign + brief.
    root = Path(temp_hive_dir)
    init_git_repo(root)

    payloads: dict[str, dict[str, Any]] = {
        "drivers_list": _invoke_cli_json(capsys, ["--path", temp_hive_dir, "--json", "drivers", "list"])
    }

    _invoke_cli_json(capsys, ["--path", temp_hive_dir, "--json", "onboard", "demo", "--title", "Demo"])
    write_safe_program(root, "demo")
    create_task(
        root,
        "demo",
        "CLI schema task",
        status="ready",
        priority=1,
        acceptance=["CLI schema proofs stay stable and reviewable."],
        summary_md="A dedicated task for the CLI schema fixture tests.",
    )
    _commit_all(root, "Bootstrap CLI schema workspace")

    payloads["next"] = _invoke_cli_json(
        capsys,
        ["--path", temp_hive_dir, "--json", "next", "--project-id", "demo"],
    )
    payloads["work_local"] = _invoke_cli_json(
        capsys,
        [
            "--path",
            temp_hive_dir,
            "--json",
            "work",
            "--project-id",
            "demo",
            "--owner",
            "schema-operator",
            "--driver",
            "local",
            "--output",
            "SESSION.md",
        ],
    )
    run_id = str(payloads["work_local"]["run"]["id"])
    payloads["finish_local"] = _invoke_cli_json(
        capsys,
        ["--path", temp_hive_dir, "--json", "finish", run_id, "--owner", "schema-operator"],
    )
    payloads["portfolio_status"] = _invoke_cli_json(
        capsys,
        ["--path", temp_hive_dir, "--json", "portfolio", "status"],
    )
    payloads["campaign_create"] = _invoke_cli_json(
        capsys,
        [
            "--path",
            temp_hive_dir,
            "--json",
            "campaign",
            "create",
            "--title",
            "Launch week",
            "--goal",
            "Ship it",
            "--project-id",
            "demo",
        ],
    )
    payloads["brief_daily"] = _invoke_cli_json(
        capsys,
        ["--path", temp_hive_dir, "--json", "brief", "daily"],
    )

    _invoke_cli_json(capsys, ["--path", temp_hive_dir, "--json", "onboard", "app", "--title", "App"])
    (root / "pyproject.toml").write_text(
        "[project]\nname = 'app'\nversion = '0.1.0'\n",
        encoding="utf-8",
    )
    (root / "tests").mkdir(exist_ok=True)
    payloads["program_doctor"] = _invoke_cli_json(
        capsys,
        ["--path", temp_hive_dir, "--json", "program", "doctor", "app"],
    )
    return payloads


class TestCliSchemaFixtures:
    """Freeze the operator-loop JSON contracts in fixture-backed checks."""

    def test_manager_loop_cli_payloads_match_fixture_contracts(
        self, temp_hive_dir, capsys, schema_fixture
    ):
        payloads = _build_cli_payloads(temp_hive_dir, capsys)

        assert set(payloads) == set(schema_fixture["commands"])
        for command_name, schema in schema_fixture["commands"].items():
            _assert_schema(command_name, payloads[command_name], schema)

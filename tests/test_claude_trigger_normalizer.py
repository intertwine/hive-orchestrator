"""Regression tests for Claude-review trigger normalization."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


SCRIPT_PATH = Path(".github/scripts/normalize_claude_trigger.py")


def _run_script(event_path: Path) -> None:
    """Run the workflow helper against a temporary event payload."""
    subprocess.run(
        [sys.executable, str(SCRIPT_PATH), str(event_path)],
        cwd=Path(__file__).resolve().parents[1],
        check=True,
    )


def test_normalize_claude_trigger_rewrites_comment_case_variants(tmp_path):
    """Uppercase trigger mentions should be normalized for the action."""
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps({"comment": {"body": "Please review this, @Claude and @CLAUDE."}}),
        encoding="utf-8",
    )

    _run_script(event_path)

    payload = json.loads(event_path.read_text(encoding="utf-8"))
    assert payload["comment"]["body"] == "Please review this, @claude and @claude."


def test_normalize_claude_trigger_preserves_related_mentions(tmp_path):
    """Only the bare trigger should change; related mentions stay intact."""
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps(
            {
                "issue": {
                    "body": (
                        "Keep @claude-code and @claude-beta untouched while "
                        "normalizing @Claude."
                    )
                }
            }
        ),
        encoding="utf-8",
    )

    _run_script(event_path)

    payload = json.loads(event_path.read_text(encoding="utf-8"))
    assert payload["issue"]["body"] == (
        "Keep @claude-code and @claude-beta untouched while normalizing @claude."
    )

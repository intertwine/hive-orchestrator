"""Versioned event-schema fixture checks for Hive 2.2."""

from __future__ import annotations

import json
from pathlib import Path

from src.hive.constants import (
    ARTIFACT_EVENT_TYPES,
    CAMPAIGN_EVENT_TYPES,
    EVENT_SCHEMA_VERSION,
    MEMORY_EVENT_TYPES,
    RUN_EVENT_TYPES,
    STEERING_EVENT_TYPES,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_event_schema_fixture_matches_current_constants():
    """The versioned event fixture should track the normalized event vocabulary."""
    fixture = json.loads(
        (REPO_ROOT / "tests" / "fixtures" / "event_schema" / "v2_2_event_types.json").read_text(
            encoding="utf-8"
        )
    )

    assert fixture["version"] == EVENT_SCHEMA_VERSION
    assert fixture["run"] == list(RUN_EVENT_TYPES)
    assert fixture["artifact"] == list(ARTIFACT_EVENT_TYPES)
    assert fixture["steering"] == list(STEERING_EVENT_TYPES)
    assert fixture["memory"] == list(MEMORY_EVENT_TYPES)
    assert fixture["campaign"] == list(CAMPAIGN_EVENT_TYPES)

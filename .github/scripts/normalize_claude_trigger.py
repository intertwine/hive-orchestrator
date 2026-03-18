#!/usr/bin/env python3
"""Normalize @Claude mention casing in GitHub event payloads."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from typing import Any

TRIGGER_PATTERN = re.compile(r"(?<![\w-])@claude(?![\w-])", re.IGNORECASE)


def normalize_trigger_mentions(payload: dict[str, Any]) -> bool:
    """Rewrite case variants like @Claude to the lowercase action trigger."""

    changed = False
    for field, key in (("comment", "body"), ("review", "body"), ("issue", "body")):
        section = payload.get(field)
        if not isinstance(section, dict):
            continue
        value = section.get(key)
        if not isinstance(value, str):
            continue
        normalized = TRIGGER_PATTERN.sub("@claude", value)
        if normalized != value:
            section[key] = normalized
            changed = True
    return changed


def main(argv: list[str]) -> int:
    """Normalize a GitHub Actions event payload in place."""

    if len(argv) != 2:
        print("usage: normalize_claude_trigger.py <event-path>", file=sys.stderr)
        return 2

    event_path = Path(argv[1])
    payload = json.loads(event_path.read_text(encoding="utf-8"))
    changed = normalize_trigger_mentions(payload)
    if changed:
        event_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

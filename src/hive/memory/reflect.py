"""Memory reflection job."""

from __future__ import annotations

from pathlib import Path
import re

from src.hive.store.layout import memory_scope_dir


def _observation_lines(observations: str) -> list[str]:
    return [line.strip() for line in observations.splitlines() if line.strip()]


def _unique_lines(lines: list[str], *, limit: int) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for line in lines:
        key = line.casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(line)
        if len(unique) >= limit:
            break
    return unique


def _recurring_terms(lines: list[str], *, limit: int = 3) -> list[str]:
    counts: dict[str, int] = {}
    for line in lines:
        for word in re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", line.casefold()):
            if word in {"with", "that", "this", "from", "into", "have", "your", "they"}:
                continue
            counts[word] = counts.get(word, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [word for word, count in ranked if count > 1][:limit]


def reflect(path: str | Path | None = None, *, scope: str = "project") -> dict[str, Path]:
    """Regenerate reflections, profile, and active memory docs."""
    directory = memory_scope_dir(path, scope=scope)
    directory.mkdir(parents=True, exist_ok=True)
    observations_path = directory / "observations.md"
    observations = (
        observations_path.read_text(encoding="utf-8") if observations_path.exists() else ""
    )
    lines = _observation_lines(observations)
    recent_lines = lines[-10:]
    active_lines = recent_lines[-3:]
    profile_lines = _unique_lines(lines, limit=5)
    recurring_terms = _recurring_terms(lines)
    reflections_path = directory / "reflections.md"
    profile_path = directory / "profile.md"
    active_path = directory / "active.md"
    reflections_path.write_text(
        "\n".join(
            [
                "# Reflections",
                "",
                "## Patterns",
                (
                    f"- Captured {len(lines)} observations."
                    if lines
                    else "- No reflections yet."
                ),
                (
                    "- Recurring themes: " + ", ".join(f"`{term}`" for term in recurring_terms)
                    if recurring_terms
                    else "- No recurring themes identified yet."
                ),
                "",
                "## Recent Signals",
                *(
                    recent_lines
                    if recent_lines
                    else ["- No recent project signals captured yet."]
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )
    profile_path.write_text(
        "\n".join(
            [
                "# Profile",
                "",
                "## Stable Context",
                *(
                    profile_lines
                    if profile_lines
                    else ["- No stable profile details captured yet."]
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )
    active_path.write_text(
        "\n".join(
            [
                "# Active Context",
                "",
                "## Right Now",
                *(
                    active_lines
                    if active_lines
                    else ["- No active context yet."]
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {
        "reflections": reflections_path,
        "profile": profile_path,
        "active": active_path,
    }

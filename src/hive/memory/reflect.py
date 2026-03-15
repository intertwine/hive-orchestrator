"""Memory reflection job."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import re

from src.hive.memory.common import project_memory_read_dirs, project_memory_scope_dir
from src.hive.store.layout import memory_scope_dir

OBSERVATION_RE = re.compile(
    r"^- \*\*(?P<timestamp>[^*]+)\*\* \((?P<source>[^)]+)\): (?P<text>.+)$"
)
STOP_WORDS = {
    "with",
    "that",
    "this",
    "from",
    "into",
    "have",
    "your",
    "they",
    "about",
    "while",
    "there",
    "their",
    "would",
    "could",
}


def _observation_entries(observations: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for raw_line in observations.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = OBSERVATION_RE.match(line)
        if match:
            entries.append(match.groupdict())
            continue
        entries.append({"timestamp": "", "source": "legacy", "text": line.lstrip("- ").strip()})
    return entries


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).casefold()


def _group_entries(entries: list[dict[str, str]]) -> list[dict[str, object]]:
    groups: dict[str, dict[str, object]] = {}
    for entry in entries:
        key = _normalize_text(entry["text"])
        if not key:
            continue
        bucket = groups.setdefault(
            key,
            {
                "text": entry["text"].strip(),
                "count": 0,
                "sources": [],
                "timestamps": [],
            },
        )
        bucket["count"] = int(bucket["count"]) + 1
        if entry["source"] and entry["source"] not in bucket["sources"]:
            bucket["sources"].append(entry["source"])
        if entry["timestamp"]:
            bucket["timestamps"].append(entry["timestamp"])
    return sorted(
        groups.values(),
        key=lambda item: (
            -int(item["count"]),
            str(item["timestamps"][-1] if item["timestamps"] else ""),
            str(item["text"]).lower(),
        ),
        reverse=False,
    )


def _top_terms(entries: list[dict[str, str]], *, limit: int = 5) -> list[str]:
    counts: Counter[str] = Counter()
    for entry in entries:
        for word in re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", entry["text"].casefold()):
            if word in STOP_WORDS:
                continue
            counts[word] += 1
    return [word for word, count in counts.most_common() if count > 1][:limit]


def _render_items(items: list[dict[str, object]], *, empty_message: str) -> list[str]:
    if not items:
        return [f"- {empty_message}"]
    lines: list[str] = []
    for item in items:
        provenance = ", ".join(str(source) for source in item["sources"][:3]) or "manual"
        seen = int(item["count"])
        marker = "time" if seen == 1 else "times"
        lines.append(f"- {item['text']} _(seen {seen} {marker}; sources: {provenance})_")
    return lines


def _extract_existing_items(path: Path) -> list[str]:
    if not path.exists():
        return []
    items: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() == "## Changes":
            break
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        items.append(stripped[2:].split(" _(", 1)[0].strip())
    return items


def _render_change_block(previous: list[str], current: list[str]) -> list[str]:
    previous_keys = {_normalize_text(item): item for item in previous}
    current_keys = {_normalize_text(item): item for item in current}
    added = [current_keys[key] for key in current_keys.keys() - previous_keys.keys()]
    removed = [previous_keys[key] for key in previous_keys.keys() - current_keys.keys()]
    lines = ["## Changes", ""]
    if not previous and current:
        lines.append("- Initial synthesis created from current observations.")
        lines.append("")
        return lines
    lines.append("### Added")
    if added:
        lines.extend(f"- {item}" for item in added)
    else:
        lines.append("- No new synthesized items.")
    lines.append("")
    lines.append("### Removed")
    if removed:
        lines.extend(f"- {item}" for item in removed)
    else:
        lines.append("- No items dropped from synthesis.")
    lines.append("")
    return lines


def _write_summary_doc(
    path: Path,
    *,
    heading: str,
    section_heading: str,
    items: list[dict[str, object]],
    empty_message: str,
) -> None:
    previous_items = _extract_existing_items(path)
    current_items = [str(item["text"]).strip() for item in items]
    path.write_text(
        "\n".join(
            [
                f"# {heading}",
                "",
                f"## {section_heading}",
                *_render_items(items, empty_message=empty_message),
                "",
                *_render_change_block(previous_items, current_items),
            ]
        ),
        encoding="utf-8",
    )


def _load_observations_from_candidates(
    path: str | Path | None,
    *,
    scope: str,
    project_id: str | None,
) -> tuple[Path, str]:
    if scope != "project" or not project_id:
        directory = project_memory_scope_dir(path) if scope == "project" else memory_scope_dir(
            path,
            scope=scope,
        )
        observations_path = directory / "observations.md"
        content = observations_path.read_text(encoding="utf-8") if observations_path.exists() else ""
        return directory, content

    candidate_dirs = project_memory_read_dirs(path, project_id=project_id)
    primary_dir = candidate_dirs[0]
    content_parts: list[str] = []
    for directory in candidate_dirs:
        observations_path = directory / "observations.md"
        if observations_path.exists():
            content_parts.append(observations_path.read_text(encoding="utf-8"))
    return primary_dir, "\n".join(part for part in content_parts if part.strip())


def reflect(
    path: str | Path | None = None,
    *,
    scope: str = "project",
    project_id: str | None = None,
) -> dict[str, Path]:
    """Regenerate reflections, profile, and active memory docs."""
    directory, observations = _load_observations_from_candidates(
        path,
        scope=scope,
        project_id=project_id,
    )
    directory.mkdir(parents=True, exist_ok=True)
    entries = _observation_entries(observations)
    grouped = _group_entries(entries)
    recent_groups = sorted(
        grouped,
        key=lambda item: str(item["timestamps"][-1] if item["timestamps"] else ""),
        reverse=True,
    )
    profile_groups = grouped[:5]
    active_groups = recent_groups[:4]
    recurring_terms = _top_terms(entries)

    reflections_path = directory / "reflections.md"
    profile_path = directory / "profile.md"
    active_path = directory / "active.md"

    reflections_lines = [
        "# Reflections",
        "",
        "## Patterns",
        (
            f"- Synthesized {len(grouped)} distinct memory signals from {len(entries)} observations."
            if entries
            else "- No reflections yet."
        ),
        (
            "- Recurring themes: " + ", ".join(f"`{term}`" for term in recurring_terms)
            if recurring_terms
            else "- No recurring themes identified yet."
        ),
        "",
        "## Highest-Signal Notes",
        *_render_items(recent_groups[:6], empty_message="No recent project signals captured yet."),
        "",
    ]
    reflections_path.write_text("\n".join(reflections_lines), encoding="utf-8")

    _write_summary_doc(
        profile_path,
        heading="Profile",
        section_heading="Stable Context",
        items=profile_groups,
        empty_message="No stable profile details captured yet.",
    )
    _write_summary_doc(
        active_path,
        heading="Active Context",
        section_heading="Right Now",
        items=active_groups,
        empty_message="No active context yet.",
    )

    return {
        "reflections": reflections_path,
        "profile": profile_path,
        "active": active_path,
    }

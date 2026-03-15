"""Markdown/frontmatter helpers."""

from __future__ import annotations

import re
from typing import Iterable

from src.security import safe_dump_agency_md


SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def split_sections(body: str) -> dict[str, str]:
    """Split a markdown body into `##` sections."""
    sections: dict[str, str] = {}
    matches = list(SECTION_RE.finditer(body))
    if not matches:
        return sections

    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        title = match.group(1).strip()
        sections[title] = body[start:end].strip()
    return sections


def build_sections(ordered_titles: Iterable[str], sections: dict[str, str]) -> str:
    """Render markdown sections in a deterministic order."""
    rendered: list[str] = []
    used: set[str] = set()
    for title in ordered_titles:
        content = sections.get(title)
        if content is None:
            continue
        rendered.append(f"## {title}\n\n{content}".rstrip())
        used.add(title)

    for title, content in sections.items():
        if title in used:
            continue
        rendered.append(f"## {title}\n\n{content}".rstrip())

    return "\n\n".join(rendered).strip()


def dump_markdown(metadata: dict, body: str) -> str:
    """Serialize markdown with safe YAML frontmatter."""
    return safe_dump_agency_md(metadata, body.strip() + ("\n" if body.strip() else ""))


def replace_marker_block(content: str, begin: str, end: str, replacement: str) -> str:
    """Replace or append a bounded generated markdown block."""
    pattern = re.compile(rf"{re.escape(begin)}[\s\S]*?{re.escape(end)}", re.MULTILINE)
    block = f"{begin}\n{replacement.rstrip()}\n{end}"
    if pattern.search(content):
        return pattern.sub(block, content, count=1)

    base = content.rstrip()
    separator = "\n\n" if base else ""
    return f"{base}{separator}{block}\n"

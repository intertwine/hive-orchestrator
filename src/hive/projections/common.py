"""Common projection helpers."""

from __future__ import annotations

from pathlib import Path


def replace_marker_block(text: str, begin: str, end: str, body: str) -> str:
    """Replace or append a bounded generated section."""
    block = f"{begin}\n{body}\n{end}"
    if begin in text and end in text:
        start = text.index(begin)
        finish = text.index(end, start) + len(end)
        return f"{text[:start].rstrip()}\n\n{block}\n{text[finish:].lstrip()}"
    suffix = "" if text.endswith("\n") else "\n"
    return f"{text}{suffix}\n{block}\n"


def ensure_file(path: Path, default_content: str) -> str:
    """Read a file, creating it if needed."""
    if not path.exists():
        path.write_text(default_content, encoding="utf-8")
    return path.read_text(encoding="utf-8")

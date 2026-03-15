"""Projection renderer for the root AGENTS.md shim."""

from __future__ import annotations

from pathlib import Path

from src.hive.projections.common import replace_marker_block

BEGIN = "<!-- hive:begin compatibility -->"
END = "<!-- hive:end compatibility -->"


def _render_shim() -> str:
    return "\n".join(
        [
            "## Hive 2.0 compatibility",
            "",
            "1. Use the `hive` CLI first.",
            "2. Prefer `--json` for machine-readable operations.",
            "3. Treat `.hive/tasks/*.md` as canonical task state.",
            "4. Read `projects/*/PROGRAM.md` before autonomous edits.",
        ]
    )


def sync_agents_md(path: str | Path | None = None) -> Path:
    """Append or update the bounded Hive compatibility section."""
    root = Path(path or Path.cwd())
    agents_path = root / "AGENTS.md"
    content = agents_path.read_text(encoding="utf-8") if agents_path.exists() else "# AGENTS\n"
    updated = replace_marker_block(content, BEGIN, END, _render_shim())
    agents_path.write_text(updated, encoding="utf-8")
    return agents_path

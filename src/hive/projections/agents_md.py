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


def _default_agents_md() -> str:
    return "\n".join(
        [
            "# AGENTS",
            "",
            "Use the `hive` CLI first.",
            "",
            "- Canonical task state lives in `.hive/tasks/*.md`.",
            "- Narrative project docs live in `projects/*/AGENCY.md`.",
            "- `projects/*/PROGRAM.md` defines evaluator, path, and command policy.",
            "- Run `hive context startup --project <project-id> --json` before autonomous edits.",
            "- Run `hive sync projections --json` after canonical task or run changes.",
            "",
            BEGIN,
            END,
            "",
        ]
    )


def sync_agents_md(path: str | Path | None = None) -> Path:
    """Append or update the bounded Hive compatibility section."""
    root = Path(path or Path.cwd())
    agents_path = root / "AGENTS.md"
    content = (
        agents_path.read_text(encoding="utf-8") if agents_path.exists() else _default_agents_md()
    )
    updated = replace_marker_block(content, BEGIN, END, _render_shim())
    agents_path.write_text(updated, encoding="utf-8")
    return agents_path

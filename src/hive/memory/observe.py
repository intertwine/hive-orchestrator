"""Memory observation job."""

from __future__ import annotations

from pathlib import Path

from src.hive.clock import utc_now_iso
from src.hive.store.layout import memory_project_dir


def observe(
    path: str | Path | None = None,
    *,
    transcript_path: str | Path | None = None,
    note: str | None = None,
) -> Path:
    """Append a compressed observation entry."""
    directory = memory_project_dir(path)
    directory.mkdir(parents=True, exist_ok=True)
    observations_path = directory / "observations.md"
    if transcript_path:
        raw = Path(transcript_path).read_text(encoding="utf-8")
        snippet = raw[:1000].strip()
        source = str(transcript_path)
    else:
        snippet = (note or "Manual observation checkpoint.").strip()
        source = "manual"
    with open(observations_path, "a", encoding="utf-8") as handle:
        handle.write(f"- **{utc_now_iso()}** ({source}): {snippet}\n")
    return observations_path

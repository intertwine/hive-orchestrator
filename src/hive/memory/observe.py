"""Memory observation job."""

from __future__ import annotations

from pathlib import Path
import shutil

from src.hive.clock import utc_now_iso
from src.hive.ids import new_id
from src.hive.store.layout import memory_harness_dir, memory_scope_dir


def _copy_transcript(
    path: str | Path | None,
    *,
    harness: str,
    transcript_path: str | Path,
) -> Path:
    target_dir = memory_harness_dir(path, harness=harness)
    target_dir.mkdir(parents=True, exist_ok=True)
    source_path = Path(transcript_path)
    target_path = target_dir / f"{new_id('evt')}_{source_path.name}"
    shutil.copy2(source_path, target_path)
    return target_path


def observe(
    path: str | Path | None = None,
    *,
    transcript_path: str | Path | None = None,
    note: str | None = None,
    scope: str = "project",
    harness: str | None = None,
) -> Path:
    """Append a compressed observation entry."""
    directory = memory_scope_dir(path, scope=scope)
    directory.mkdir(parents=True, exist_ok=True)
    observations_path = directory / "observations.md"
    if transcript_path:
        source_path = (
            _copy_transcript(path, harness=harness, transcript_path=transcript_path)
            if harness
            else Path(transcript_path)
        )
        raw = source_path.read_text(encoding="utf-8")
        snippet = raw[:1000].strip()
        source = f"{harness}:{source_path}" if harness else str(source_path)
    else:
        snippet = (note or "Manual observation checkpoint.").strip()
        source = harness or "manual"
    with open(observations_path, "a", encoding="utf-8") as handle:
        handle.write(f"- **{utc_now_iso()}** ({source}): {snippet}\n")
    return observations_path

"""Trajectory JSONL writer and loader."""

from __future__ import annotations

import json
from pathlib import Path

from src.hive.trajectory.schema import TrajectoryEvent


def trajectory_file(
    base_path: str | Path,
    *,
    run_id: str | None = None,
    delegate_session_id: str | None = None,
) -> Path:
    """Return the trajectory JSONL path for a run or delegate session."""
    root = Path(base_path).resolve()
    if run_id:
        return root / ".hive" / "runs" / run_id / "trajectory.jsonl"
    if delegate_session_id:
        return root / ".hive" / "delegates" / delegate_session_id / "trajectory.jsonl"
    raise ValueError("Either run_id or delegate_session_id is required.")


def append_trajectory_event(
    base_path: str | Path,
    event: TrajectoryEvent,
) -> None:
    """Append a trajectory event to the appropriate JSONL file."""
    path = trajectory_file(
        base_path,
        run_id=event.run_id,
        delegate_session_id=event.delegate_session_id,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(event.to_dict(), sort_keys=True) + "\n")


def load_trajectory(
    base_path: str | Path,
    *,
    run_id: str | None = None,
    delegate_session_id: str | None = None,
) -> list[TrajectoryEvent]:
    """Load and parse trajectory events from a JSONL file."""
    path = trajectory_file(
        base_path,
        run_id=run_id,
        delegate_session_id=delegate_session_id,
    )
    if not path.exists():
        return []
    events: list[TrajectoryEvent] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(TrajectoryEvent.from_dict(json.loads(line)))
    return events


__all__ = ["append_trajectory_event", "load_trajectory", "trajectory_file"]

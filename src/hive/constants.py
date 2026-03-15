"""Shared constants for Hive 2.0."""

TASK_KINDS = {"epic", "task", "bug", "spike", "chore", "review", "experiment"}
TASK_STATUSES = {
    "proposed",
    "ready",
    "claimed",
    "in_progress",
    "blocked",
    "review",
    "done",
    "archived",
}
RUN_STATUSES = {
    "planned",
    "running",
    "evaluating",
    "accepted",
    "rejected",
    "escalated",
    "aborted",
}
EXECUTOR_NAMES = {"local", "github-actions"}
EDGE_TYPES = {"blocks", "parent_of", "relates_to", "duplicates", "supersedes"}
PRIORITY_MAP = {"critical": 0, "high": 1, "medium": 2, "low": 3}

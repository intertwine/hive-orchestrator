"""Shared constants for Hive 2.x."""

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
    "queued",
    "compiling_context",
    "launching",
    "running",
    "awaiting_input",
    "awaiting_review",
    "blocked",
    "completed_candidate",
    "accepted",
    "rejected",
    "escalated",
    "cancelled",
    "failed",
    # Legacy aliases retained while v2.2 finishes replacing older internals.
    "planned",
    "evaluating",
    "aborted",
}
RUN_ACTIVE_STATUSES = {
    "queued",
    "compiling_context",
    "launching",
    "running",
    "awaiting_input",
    "awaiting_review",
    "blocked",
    "completed_candidate",
    "evaluating",
}
RUN_TERMINAL_STATUSES = {"accepted", "rejected", "escalated", "cancelled", "failed", "aborted"}
EXECUTOR_NAMES = {"local", "github-actions"}
DRIVER_NAMES = {"local", "manual", "codex", "claude", "claude-code", "pi"}
DRIVER_ORDER = ("local", "manual", "codex", "claude", "pi")
EDGE_TYPES = {"blocks", "parent_of", "relates_to", "duplicates", "supersedes"}
PRIORITY_MAP = {"critical": 0, "high": 1, "medium": 2, "low": 3}
RUN_EVENT_TYPES = (
    "run.queued",
    "run.context_compiled",
    "run.launch_started",
    "run.launched",
    "run.status.changed",
    "run.awaiting_input",
    "run.awaiting_review",
    "run.completed_candidate",
    "run.accepted",
    "run.rejected",
    "run.escalated",
    "run.cancelled",
    "run.failed",
)
ARTIFACT_EVENT_TYPES = (
    "artifact.added",
    "eval.started",
    "eval.completed",
    "eval.failed",
    "review.summary_generated",
)
STEERING_EVENT_TYPES = (
    "steering.pause",
    "steering.resume",
    "steering.cancel",
    "steering.reroute_requested",
    "steering.rerouted",
    "steering.note_added",
    "steering.budget_changed",
    "steering.approve",
    "steering.reject",
    "steering.rollback",
    "steering.sidequest_created",
)
MEMORY_EVENT_TYPES = ("context.compiled", "memory.proposed", "memory.accepted", "memory.rejected")
CAMPAIGN_EVENT_TYPES = (
    "campaign.created",
    "campaign.tick",
    "campaign.goal_updated",
    "campaign.completed",
)
EVENT_SCHEMA_VERSION = "2.2.0"

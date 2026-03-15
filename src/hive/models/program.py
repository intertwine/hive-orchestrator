"""Program contract model."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.hive.constants import EXECUTOR_NAMES


def _require_mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"PROGRAM.md {name} must be a mapping")
    return dict(value)


def _require_string_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"PROGRAM.md {name} must be a list of strings")
    return list(value)


def _require_number(value: Any, name: str) -> float:
    if not isinstance(value, (int, float)):
        raise ValueError(f"PROGRAM.md {name} must be numeric")
    return float(value)


@dataclass
class ProgramRecord:
    """Canonical PROGRAM.md representation."""

    path: Path
    body: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def unsafe_without_evaluators(self) -> bool:
        """Return whether this program explicitly opts into ungated autonomous acceptance."""
        promotion = self.metadata.get("promotion", {})
        return bool(promotion.get("allow_unsafe_without_evaluators", False))

    def allow_accept_without_changes(self) -> bool:
        """Return whether this program explicitly opts into accepting no-op runs."""
        promotion = self.metadata.get("promotion", {})
        return bool(promotion.get("allow_accept_without_changes", False))

    def evaluator_ids(self) -> list[str]:
        """Return declared evaluator IDs in definition order."""
        return [str(evaluator["id"]) for evaluator in self.metadata.get("evaluators", [])]

    def required_evaluator_ids(self) -> list[str]:
        """Return required evaluator IDs in definition order."""
        return [
            str(evaluator["id"])
            for evaluator in self.metadata.get("evaluators", [])
            if evaluator.get("required", True)
        ]

    def validate(self) -> None:
        """Validate and normalize the MVP program schema in place.

        This method intentionally uses ``setdefault`` to populate omitted optional keys in
        ``self.metadata`` so downstream callers can rely on normalized structures after
        validation.
        """
        required = ["program_version", "mode", "default_executor"]
        missing = [key for key in required if key not in self.metadata]
        if missing:
            raise ValueError(f"PROGRAM.md is missing required fields: {', '.join(missing)}")

        if not isinstance(self.metadata["program_version"], int):
            raise ValueError("PROGRAM.md program_version must be an integer")
        if not isinstance(self.metadata["mode"], str):
            raise ValueError("PROGRAM.md mode must be a string")
        if self.metadata["default_executor"] not in EXECUTOR_NAMES:
            raise ValueError(
                "PROGRAM.md default_executor must be one of: " + ", ".join(sorted(EXECUTOR_NAMES))
            )

        budgets = _require_mapping(self.metadata.setdefault("budgets", {}), "budgets")
        for key in ["max_wall_clock_minutes", "max_steps", "max_tokens", "max_cost_usd"]:
            if key not in budgets:
                raise ValueError(f"PROGRAM.md budgets is missing required field: {key}")
            _require_number(budgets[key], f"budgets.{key}")

        paths = _require_mapping(self.metadata.setdefault("paths", {}), "paths")
        _require_string_list(paths.setdefault("allow", []), "paths.allow")
        _require_string_list(paths.setdefault("deny", []), "paths.deny")

        commands = _require_mapping(self.metadata.setdefault("commands", {}), "commands")
        _require_string_list(commands.setdefault("allow", []), "commands.allow")
        _require_string_list(commands.setdefault("deny", []), "commands.deny")

        evaluators = self.metadata.setdefault("evaluators", [])
        if not isinstance(evaluators, list):
            raise ValueError("PROGRAM.md evaluators must be a list")
        seen_ids: set[str] = set()
        for index, evaluator in enumerate(evaluators):
            if not isinstance(evaluator, dict):
                raise ValueError(f"PROGRAM.md evaluators[{index}] must be a mapping")
            for key in ["id", "command"]:
                if not isinstance(evaluator.get(key), str) or not evaluator[key].strip():
                    raise ValueError(
                        f"PROGRAM.md evaluators[{index}].{key} must be a non-empty string"
                    )
            evaluator["id"] = evaluator["id"].strip()
            if evaluator["id"] in seen_ids:
                raise ValueError(f"PROGRAM.md evaluator IDs must be unique: {evaluator['id']}")
            seen_ids.add(evaluator["id"])
            if "required" in evaluator and not isinstance(evaluator["required"], bool):
                raise ValueError(f"PROGRAM.md evaluators[{index}].required must be a boolean")
            evaluator.setdefault("required", True)

        promotion = _require_mapping(self.metadata.setdefault("promotion", {}), "promotion")
        if not isinstance(promotion.setdefault("allow_unsafe_without_evaluators", False), bool):
            raise ValueError(
                "PROGRAM.md promotion.allow_unsafe_without_evaluators must be a boolean"
            )
        if not isinstance(promotion.setdefault("allow_accept_without_changes", False), bool):
            raise ValueError("PROGRAM.md promotion.allow_accept_without_changes must be a boolean")
        _require_string_list(promotion.setdefault("requires_all", []), "promotion.requires_all")
        _require_string_list(
            promotion.setdefault("review_required_when_paths_match", []),
            "promotion.review_required_when_paths_match",
        )
        if not isinstance(promotion.setdefault("auto_close_task", False), bool):
            raise ValueError("PROGRAM.md promotion.auto_close_task must be a boolean")
        evaluator_ids = self.evaluator_ids()
        unknown_evaluators = [
            evaluator_id
            for evaluator_id in promotion["requires_all"]
            if evaluator_id not in evaluator_ids
        ]
        if unknown_evaluators:
            unknown = ", ".join(sorted(dict.fromkeys(unknown_evaluators)))
            raise ValueError(
                "PROGRAM.md promotion.requires_all contains unknown evaluator IDs: " + unknown
            )
        if not self.unsafe_without_evaluators():
            required_ids = self.required_evaluator_ids()
            if not required_ids:
                raise ValueError(
                    "PROGRAM.md must declare at least one required evaluator unless "
                    "promotion.allow_unsafe_without_evaluators is true"
                )
            if not promotion["requires_all"]:
                raise ValueError(
                    "PROGRAM.md promotion.requires_all must list at least one evaluator unless "
                    "promotion.allow_unsafe_without_evaluators is true"
                )

        escalation = _require_mapping(self.metadata.setdefault("escalation", {}), "escalation")
        _require_string_list(
            escalation.setdefault("when_paths_match", []), "escalation.when_paths_match"
        )
        _require_string_list(
            escalation.setdefault("when_commands_match", []),
            "escalation.when_commands_match",
        )

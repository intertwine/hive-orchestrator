"""PROGRAM.md contract analysis and edit helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.hive.models.program import ProgramRecord
from src.hive.store.projects import get_project
from src.security import safe_dump_agency_md, safe_load_agency_md


@dataclass(frozen=True)
class DetectedStack:
    """Feature flags and script hints inferred from a project tree."""

    python: bool
    node: bool
    rust: bool
    go: bool
    make: bool
    scripts: dict[str, Any]
    package_json_path: str | None


@dataclass(frozen=True)
class ProgramPolicy:
    """Normalized PROGRAM.md policy fields used by the doctor helpers."""

    commands_allow: list[str]
    paths_allow: list[str]
    paths_deny: list[str]
    required_ids: list[str]
    requires_all: list[str]
    unsafe: bool


@dataclass(frozen=True)
class ProgramContract:
    """Normalized PROGRAM.md metadata used by the doctor helpers."""

    metadata: dict[str, Any]
    evaluators: list[dict[str, Any]]
    policy: ProgramPolicy


@dataclass(frozen=True)
class IssueSpec:
    """Structured description for a PROGRAM.md issue."""

    code: str
    severity: str
    message: str
    field: str
    blocking: bool
    fixable: bool
    suggested_command: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert the issue into the JSON shape used by CLI responses."""
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "field": self.field,
            "blocking": self.blocking,
            "fixable": self.fixable,
            "suggested_command": self.suggested_command,
        }


def _normalize_command_id(value: str) -> str:
    return (
        value.strip()
        .lower()
        .replace(" ", "-")
        .replace("_", "-")
        .replace(".", "-")
        .replace("/", "-")
    )


def _load_package_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    values: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        stripped = item.strip()
        if stripped:
            values.append(stripped)
    return values


def _dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _evaluator_ids(
    evaluators: list[dict[str, Any]],
    *,
    required_only: bool = False,
) -> list[str]:
    values: list[str] = []
    for item in evaluators:
        if required_only and not item.get("required", True):
            continue
        identifier = str(item.get("id", "")).strip()
        if identifier:
            values.append(identifier)
    return values


def _detected_stack(root: Path, project_dir: Path) -> DetectedStack:
    package_candidates = [project_dir / "package.json", root / "package.json"]
    py_candidates = [
        project_dir / "pyproject.toml",
        root / "pyproject.toml",
        project_dir / "requirements.txt",
        root / "requirements.txt",
    ]
    rust_candidates = [project_dir / "Cargo.toml", root / "Cargo.toml"]
    go_candidates = [project_dir / "go.mod", root / "go.mod"]
    make_candidates = [project_dir / "Makefile", root / "Makefile"]
    package_json_path = next((path for path in package_candidates if path.exists()), None)
    package_json = _load_package_json(package_json_path)
    scripts = _mapping(package_json.get("scripts"))
    return DetectedStack(
        python=any(path.exists() for path in py_candidates),
        node=package_json_path is not None,
        rust=any(path.exists() for path in rust_candidates),
        go=any(path.exists() for path in go_candidates),
        make=any(path.exists() for path in make_candidates),
        scripts=scripts,
        package_json_path=str(package_json_path) if package_json_path else None,
    )


def _template(
    template_id: str,
    command: str,
    *,
    label: str,
    reason: str,
    required: bool = True,
) -> dict[str, Any]:
    return {
        "id": template_id,
        "label": label,
        "command": command,
        "reason": reason,
        "required": required,
    }


def evaluator_templates(root: Path, project_dir: Path) -> list[dict[str, Any]]:
    """Suggest evaluator templates based on the observed project stack."""
    stack = _detected_stack(root, project_dir)
    templates: list[dict[str, Any]] = []
    scripts = stack.scripts
    if stack.python:
        templates.append(
            _template(
                "pytest",
                "UV_PYTHON=3.11 uv run --extra dev pytest -q",
                label="Pytest suite",
                reason="Detected Python project files or test layout.",
            )
        )
    if stack.make:
        templates.append(
            _template(
                "make-test",
                "make test",
                label="Make test",
                reason="Detected a Makefile that can centralize repo validation.",
            )
        )
        templates.append(
            _template(
                "make-check",
                "make check",
                label="Make check",
                reason="Detected a Makefile with likely combined validation entrypoints.",
                required=False,
            )
        )
    if stack.node:
        if "test" in scripts:
            templates.append(
                _template(
                    "npm-test",
                    "npm run test -- --run",
                    label="NPM test",
                    reason="Detected a package.json test script.",
                )
            )
        if "lint" in scripts:
            templates.append(
                _template(
                    "npm-lint",
                    "npm run lint",
                    label="NPM lint",
                    reason="Detected a package.json lint script.",
                    required=False,
                )
            )
        if "build" in scripts:
            templates.append(
                _template(
                    "npm-build",
                    "npm run build",
                    label="NPM build",
                    reason="Detected a package.json build script.",
                    required=False,
                )
            )
    if stack.rust:
        templates.append(
            _template(
                "cargo-test",
                "cargo test",
                label="Cargo test",
                reason="Detected Cargo.toml.",
            )
        )
    if stack.go:
        templates.append(
            _template(
                "go-test",
                "go test ./...",
                label="Go test",
                reason="Detected go.mod.",
            )
        )
    seen_ids: set[str] = set()
    unique: list[dict[str, Any]] = []
    for candidate in templates:
        if candidate["id"] in seen_ids:
            continue
        seen_ids.add(candidate["id"])
        unique.append(candidate)
    if unique:
        return unique
    return [
        _template(
            "local-smoke",
            "python3 -c \"print('local smoke ok')\"",
            label="Local smoke check",
            reason=(
                "No repo-specific test or lint entrypoint was detected, so Hive can seed "
                "a minimal starter evaluator for the first governed run."
            ),
        )
    ]


def _issue(spec: IssueSpec) -> dict[str, Any]:
    return spec.to_dict()


def _missing_required_evaluator_issue(
    project_id: str,
    suggested_templates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    command_hint = None
    if suggested_templates:
        command_hint = (
            f"hive program add-evaluator {project_id} {suggested_templates[0]['id']}"
        )
    return [
        _issue(
            IssueSpec(
                code="missing_required_evaluator",
                severity="error",
                message=(
                    "Autonomous promotion is blocked because PROGRAM.md "
                    "declares no required evaluator."
                ),
                field="evaluators",
                blocking=True,
                fixable=bool(command_hint),
                suggested_command=command_hint,
            )
        )
    ]


def _missing_promotion_gate_issue() -> list[dict[str, Any]]:
    return [
        _issue(
            IssueSpec(
                code="missing_promotion_gate",
                severity="error",
                message=(
                    "promotion.requires_all is empty, so Hive has no explicit "
                    "evaluator gate to enforce."
                ),
                field="promotion.requires_all",
                blocking=True,
                fixable=False,
            )
        )
    ]


def _required_evaluator_not_gated_issue(
    missing_required_from_requires_all: list[str],
) -> list[dict[str, Any]]:
    return [
        _issue(
            IssueSpec(
                code="required_evaluator_not_gated",
                severity="error",
                message=(
                    "Some required evaluators are not listed in "
                    "promotion.requires_all: "
                    + ", ".join(missing_required_from_requires_all)
                ),
                field="promotion.requires_all",
                blocking=True,
                fixable=False,
            )
        )
    ]


def _unknown_required_evaluator_issue(
    unknown_requires_all: list[str],
) -> list[dict[str, Any]]:
    return [
        _issue(
            IssueSpec(
                code="unknown_required_evaluator",
                severity="error",
                message=(
                    "promotion.requires_all references unknown evaluator IDs: "
                    + ", ".join(unknown_requires_all)
                ),
                field="promotion.requires_all",
                blocking=True,
                fixable=False,
            )
        )
    ]


def _evaluator_command_not_allowlisted_issue(
    missing_command_allow: list[str],
) -> list[dict[str, Any]]:
    return [
        _issue(
            IssueSpec(
                code="evaluator_command_not_allowlisted",
                severity="error",
                message=(
                    "Evaluator commands must be explicitly allow-listed in "
                    "commands.allow: "
                    + ", ".join(missing_command_allow)
                ),
                field="commands.allow",
                blocking=True,
                fixable=False,
            )
        )
    ]


def _missing_path_allowlist_issue() -> list[dict[str, Any]]:
    return [
        _issue(
            IssueSpec(
                code="missing_path_allowlist",
                severity="warning",
                message=(
                    "paths.allow is empty. Hive can still evaluate policy, but the "
                    "contract does not clearly bound where autonomous changes are "
                    "expected."
                ),
                field="paths.allow",
                blocking=False,
                fixable=False,
            )
        )
    ]


def _broad_path_allowlist_issue() -> list[dict[str, Any]]:
    return [
        _issue(
            IssueSpec(
                code="broad_path_allowlist",
                severity="warning",
                message=(
                    "paths.allow includes a broad wildcard, which weakens the safety "
                    "story for autonomous promotion."
                ),
                field="paths.allow",
                blocking=False,
                fixable=False,
            )
        )
    ]


def _missing_path_denylist_issue() -> list[dict[str, Any]]:
    return [
        _issue(
            IssueSpec(
                code="missing_path_denylist",
                severity="warning",
                message=(
                    "paths.deny is empty. Consider explicitly denying secrets, "
                    "deploy, or production paths."
                ),
                field="paths.deny",
                blocking=False,
                fixable=False,
            )
        )
    ]


def _unsafe_autonomy_opt_in_issue() -> list[dict[str, Any]]:
    return [
        _issue(
            IssueSpec(
                code="unsafe_autonomy_opt_in",
                severity="warning",
                message="PROGRAM.md explicitly opts into ungated autonomous promotion.",
                field="promotion.allow_unsafe_without_evaluators",
                blocking=False,
                fixable=False,
            )
        )
    ]


def _load_program_source(program_path: Path) -> tuple[dict[str, Any], str]:
    parsed = safe_load_agency_md(program_path)
    return dict(parsed.metadata), parsed.content


def _program_contract(metadata: dict[str, Any]) -> ProgramContract:
    promotion = _mapping(metadata.get("promotion"))
    evaluators = _dict_list(metadata.get("evaluators"))
    commands = _mapping(metadata.get("commands"))
    paths = _mapping(metadata.get("paths"))
    policy = ProgramPolicy(
        commands_allow=_string_list(commands.get("allow")),
        paths_allow=_string_list(paths.get("allow")),
        paths_deny=_string_list(paths.get("deny")),
        required_ids=_evaluator_ids(evaluators, required_only=True),
        requires_all=_string_list(promotion.get("requires_all")),
        unsafe=bool(promotion.get("allow_unsafe_without_evaluators", False)),
    )
    return ProgramContract(metadata=metadata, evaluators=evaluators, policy=policy)


def _program_issues(
    project_id: str,
    contract: ProgramContract,
    suggested_templates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    policy = contract.policy

    if not policy.required_ids and not policy.unsafe:
        issues.extend(_missing_required_evaluator_issue(project_id, suggested_templates))

    if not policy.requires_all and not policy.unsafe:
        issues.extend(_missing_promotion_gate_issue())

    missing_required_from_requires_all = [
        evaluator_id
        for evaluator_id in policy.required_ids
        if evaluator_id not in policy.requires_all
    ]
    if missing_required_from_requires_all:
        issues.extend(
            _required_evaluator_not_gated_issue(missing_required_from_requires_all)
        )

    evaluator_ids = {item["id"] for item in contract.evaluators}
    unknown_requires_all = [
        evaluator_id
        for evaluator_id in policy.requires_all
        if evaluator_id not in evaluator_ids
    ]
    if unknown_requires_all:
        issues.extend(_unknown_required_evaluator_issue(unknown_requires_all))

    missing_command_allow = [
        str(item.get("command", "")).strip()
        for item in contract.evaluators
        if str(item.get("command", "")).strip()
        and str(item.get("command", "")).strip() not in policy.commands_allow
    ]
    if missing_command_allow:
        issues.extend(_evaluator_command_not_allowlisted_issue(missing_command_allow))

    if not policy.paths_allow:
        issues.extend(_missing_path_allowlist_issue())
    elif any(
        pattern.strip() in {"*", "**", "./**"}
        for pattern in policy.paths_allow
        if isinstance(pattern, str)
    ):
        issues.extend(_broad_path_allowlist_issue())

    if not policy.paths_deny:
        issues.extend(_missing_path_denylist_issue())

    if policy.unsafe:
        issues.extend(_unsafe_autonomy_opt_in_issue())
    return issues


def doctor_program(path: str | Path | None, project_ref: str) -> dict[str, Any]:
    """Inspect a project's PROGRAM.md and return structured guidance."""
    root = Path(path or Path.cwd()).resolve()
    project = get_project(root, project_ref)
    program_path = project.program_path
    suggested_templates = evaluator_templates(root, project.directory)
    if not program_path.exists():
        return {
            "scope": "program",
            "project_id": project.id,
            "program_path": str(program_path),
            "status": "fail",
            "blocked_autonomous_promotion": True,
            "issues": [
                _issue(
                    IssueSpec(
                        code="missing_program",
                        severity="error",
                        message=(
                            "PROGRAM.md is missing. Hive cannot launch governed "
                            "autonomous runs safely."
                        ),
                        field="program",
                        blocking=True,
                        fixable=False,
                    )
                )
            ],
            "suggested_templates": suggested_templates,
        }

    try:
        metadata, body = _load_program_source(program_path)
    except (FileNotFoundError, ValueError) as exc:
        return {
            "scope": "program",
            "project_id": project.id,
            "program_path": str(program_path),
            "status": "fail",
            "blocked_autonomous_promotion": True,
            "issues": [
                _issue(
                    IssueSpec(
                        code="invalid_program_frontmatter",
                        severity="error",
                        message=f"PROGRAM.md could not be parsed: {exc}",
                        field="program",
                        blocking=True,
                        fixable=False,
                    )
                )
            ],
            "suggested_templates": suggested_templates,
        }

    program = ProgramRecord(path=program_path, body=body, metadata=dict(metadata))
    issues: list[dict[str, Any]] = []
    try:
        program.validate()
    except ValueError as exc:
        issues.append(
            _issue(
                IssueSpec(
                    code="program_validation_failed",
                    severity="error",
                    message=str(exc),
                    field="program",
                    blocking=True,
                    fixable=False,
                )
            )
        )

    contract = _program_contract(metadata)
    issues.extend(_program_issues(project.id, contract, suggested_templates))

    blocked = any(issue["blocking"] for issue in issues)
    status = "fail" if blocked else "warn" if issues else "pass"
    return {
        "scope": "program",
        "project_id": project.id,
        "project_slug": project.slug,
        "program_path": str(program_path),
        "status": status,
        "blocked_autonomous_promotion": blocked,
        "issues": issues,
        "suggested_templates": suggested_templates,
    }


def _require_list(metadata: dict[str, Any], key: str, context: str) -> list[Any]:
    value = metadata.setdefault(key, [])
    if not isinstance(value, list):
        raise ValueError(f"{context} must be a list before adding a template")
    return value


def _require_dict(metadata: dict[str, Any], key: str, context: str) -> dict[str, Any]:
    value = metadata.setdefault(key, {})
    if not isinstance(value, dict):
        raise ValueError(f"{context} must be a mapping before adding a template")
    return value


def _append_unique(values: list[Any], item: Any) -> None:
    if item not in values:
        values.append(item)


def _template_index(root: Path, project_dir: Path) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in evaluator_templates(root, project_dir)}


def _select_template(
    root: Path,
    project_dir: Path,
    template_id: str,
) -> dict[str, Any]:
    templates = _template_index(root, project_dir)
    template = templates.get(template_id)
    if template is None:
        available = ", ".join(sorted(templates)) or "none"
        raise ValueError(
            f"Unknown evaluator template {template_id!r}. Available templates: {available}"
        )
    return template


def _ensure_evaluator_absent(
    evaluators: list[Any],
    evaluator_id: str,
) -> None:
    if any(
        isinstance(item, dict) and str(item.get("id", "")).strip() == evaluator_id
        for item in evaluators
    ):
        raise ValueError(f"PROGRAM.md already defines evaluator {evaluator_id!r}")


def _apply_template_to_metadata(
    metadata: dict[str, Any],
    template: dict[str, Any],
) -> str:
    evaluator_id = _normalize_command_id(template["id"])
    evaluators = _require_list(metadata, "evaluators", "PROGRAM.md evaluators")
    _ensure_evaluator_absent(evaluators, evaluator_id)
    evaluators.append(
        {
            "id": evaluator_id,
            "command": template["command"],
            "required": bool(template.get("required", True)),
        }
    )

    commands = _require_dict(metadata, "commands", "PROGRAM.md commands")
    command_allow = commands.setdefault("allow", [])
    if not isinstance(command_allow, list):
        raise ValueError("PROGRAM.md commands.allow must be a list before adding a template")
    _append_unique(command_allow, template["command"])

    promotion = _require_dict(metadata, "promotion", "PROGRAM.md promotion")
    requires_all = promotion.setdefault("requires_all", [])
    if not isinstance(requires_all, list):
        raise ValueError(
            "PROGRAM.md promotion.requires_all must be a list before adding a template"
        )
    if bool(template.get("required", True)):
        _append_unique(requires_all, evaluator_id)
    return evaluator_id


def add_evaluator_template(
    path: str | Path | None,
    project_ref: str,
    template_id: str,
) -> dict[str, Any]:
    """Apply a suggested evaluator template to a project's PROGRAM.md."""
    root = Path(path or Path.cwd()).resolve()
    project = get_project(root, project_ref)
    program_path = project.program_path
    metadata, body = _load_program_source(program_path)
    template = _select_template(root, project.directory, template_id)
    _apply_template_to_metadata(metadata, template)

    program_path.write_text(safe_dump_agency_md(metadata, body), encoding="utf-8")
    diagnosis = doctor_program(root, project.id)
    diagnosis["applied_template"] = template
    return diagnosis

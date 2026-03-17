"""PROGRAM.md analysis and guided fixes for Hive 2.2."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from src.hive.models.program import ProgramRecord
from src.hive.store.projects import get_project
from src.security import safe_dump_agency_md, safe_load_agency_md


def _normalize_command_id(value: str) -> str:
    return (
        value.strip()
        .lower()
        .replace(" ", "-")
        .replace("_", "-")
        .replace(".", "-")
        .replace("/", "-")
    )


def _load_package_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _detected_stack(root: Path, project_dir: Path) -> dict[str, Any]:
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
    package_json = _load_package_json(package_json_path) if package_json_path else {}
    scripts = package_json.get("scripts", {}) if isinstance(package_json.get("scripts"), dict) else {}
    return {
        "python": any(path.exists() for path in py_candidates),
        "node": package_json_path is not None,
        "rust": any(path.exists() for path in rust_candidates),
        "go": any(path.exists() for path in go_candidates),
        "make": any(path.exists() for path in make_candidates),
        "scripts": scripts,
        "package_json_path": str(package_json_path) if package_json_path else None,
    }


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
    scripts = stack["scripts"]
    if stack["python"]:
        templates.append(
            _template(
                "pytest",
                "UV_PYTHON=3.11 uv run --extra dev pytest -q",
                label="Pytest suite",
                reason="Detected Python project files or test layout.",
            )
        )
    if stack["make"]:
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
    if stack["node"]:
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
    if stack["rust"]:
        templates.append(
            _template(
                "cargo-test",
                "cargo test",
                label="Cargo test",
                reason="Detected Cargo.toml.",
            )
        )
    if stack["go"]:
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
    return unique


def _issue(
    code: str,
    severity: str,
    message: str,
    *,
    field: str,
    blocking: bool,
    fixable: bool,
    suggested_command: str | None = None,
) -> dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "message": message,
        "field": field,
        "blocking": blocking,
        "fixable": fixable,
        "suggested_command": suggested_command,
    }


def _load_program_source(program_path: Path) -> tuple[dict[str, Any], str]:
    parsed = safe_load_agency_md(program_path)
    return dict(parsed.metadata), parsed.content


def doctor_program(path: str | Path | None, project_ref: str) -> dict[str, Any]:
    """Inspect a project's PROGRAM.md and return structured guidance."""
    root = Path(path or Path.cwd()).resolve()
    project = get_project(root, project_ref)
    program_path = project.program_path
    suggested_templates = evaluator_templates(root, project.directory)
    issues: list[dict[str, Any]] = []
    metadata: dict[str, Any] = {}
    body = ""

    if not program_path.exists():
        issues.append(
            _issue(
                "missing_program",
                "error",
                "PROGRAM.md is missing. Hive cannot launch governed autonomous runs safely.",
                field="program",
                blocking=True,
                fixable=False,
            )
        )
        return {
            "scope": "program",
            "project_id": project.id,
            "program_path": str(program_path),
            "status": "fail",
            "blocked_autonomous_promotion": True,
            "issues": issues,
            "suggested_templates": suggested_templates,
        }

    try:
        metadata, body = _load_program_source(program_path)
    except (FileNotFoundError, ValueError) as exc:
        issues.append(
            _issue(
                "invalid_program_frontmatter",
                "error",
                f"PROGRAM.md could not be parsed: {exc}",
                field="program",
                blocking=True,
                fixable=False,
            )
        )
        return {
            "scope": "program",
            "project_id": project.id,
            "program_path": str(program_path),
            "status": "fail",
            "blocked_autonomous_promotion": True,
            "issues": issues,
            "suggested_templates": suggested_templates,
        }

    program = ProgramRecord(path=program_path, body=body, metadata=dict(metadata))
    try:
        program.validate()
    except ValueError as exc:
        issues.append(
            _issue(
                "program_validation_failed",
                "error",
                str(exc),
                field="program",
                blocking=True,
                fixable=False,
            )
        )

    promotion = metadata.get("promotion", {}) if isinstance(metadata.get("promotion"), dict) else {}
    evaluators = metadata.get("evaluators", []) if isinstance(metadata.get("evaluators"), list) else []
    commands = metadata.get("commands", {}) if isinstance(metadata.get("commands"), dict) else {}
    paths = metadata.get("paths", {}) if isinstance(metadata.get("paths"), dict) else {}
    command_allow = list(commands.get("allow", [])) if isinstance(commands.get("allow"), list) else []
    path_allow = list(paths.get("allow", [])) if isinstance(paths.get("allow"), list) else []
    path_deny = list(paths.get("deny", [])) if isinstance(paths.get("deny"), list) else []
    evaluator_ids = [
        str(item.get("id", "")).strip() for item in evaluators if isinstance(item, dict)
    ]
    required_ids = [
        str(item.get("id", "")).strip()
        for item in evaluators
        if isinstance(item, dict) and item.get("required", True)
    ]
    required_ids = [value for value in required_ids if value]
    requires_all = [
        str(value).strip()
        for value in promotion.get("requires_all", [])
        if isinstance(value, str) and str(value).strip()
    ]
    unsafe = bool(promotion.get("allow_unsafe_without_evaluators", False))

    if not required_ids and not unsafe:
        command_hint = None
        if suggested_templates:
            command_hint = f"hive program add-evaluator {project.id} {suggested_templates[0]['id']}"
        issues.append(
            _issue(
                "missing_required_evaluator",
                "error",
                "Autonomous promotion is blocked because PROGRAM.md declares no required evaluator.",
                field="evaluators",
                blocking=True,
                fixable=bool(command_hint),
                suggested_command=command_hint,
            )
        )

    if not requires_all and not unsafe:
        issues.append(
            _issue(
                "missing_promotion_gate",
                "error",
                "promotion.requires_all is empty, so Hive has no explicit evaluator gate to enforce.",
                field="promotion.requires_all",
                blocking=True,
                fixable=False,
            )
        )

    missing_required_from_requires_all = [
        evaluator_id for evaluator_id in required_ids if evaluator_id not in requires_all
    ]
    if missing_required_from_requires_all:
        issues.append(
            _issue(
                "required_evaluator_not_gated",
                "error",
                "Some required evaluators are not listed in promotion.requires_all: "
                + ", ".join(missing_required_from_requires_all),
                field="promotion.requires_all",
                blocking=True,
                fixable=False,
            )
        )

    unknown_requires_all = [evaluator_id for evaluator_id in requires_all if evaluator_id not in evaluator_ids]
    if unknown_requires_all:
        issues.append(
            _issue(
                "unknown_required_evaluator",
                "error",
                "promotion.requires_all references unknown evaluator IDs: "
                + ", ".join(unknown_requires_all),
                field="promotion.requires_all",
                blocking=True,
                fixable=False,
            )
        )

    missing_command_allow = [
        str(item.get("command", "")).strip()
        for item in evaluators
        if isinstance(item, dict)
        and str(item.get("command", "")).strip()
        and str(item.get("command", "")).strip() not in command_allow
    ]
    if missing_command_allow:
        issues.append(
            _issue(
                "evaluator_command_not_allowlisted",
                "error",
                "Evaluator commands must be explicitly allow-listed in commands.allow: "
                + ", ".join(missing_command_allow),
                field="commands.allow",
                blocking=True,
                fixable=False,
            )
        )

    if not path_allow:
        issues.append(
            _issue(
                "missing_path_allowlist",
                "warning",
                "paths.allow is empty. Hive can still evaluate policy, but the contract does not "
                "clearly bound where autonomous changes are expected.",
                field="paths.allow",
                blocking=False,
                fixable=False,
            )
        )
    elif any(pattern.strip() in {"*", "**", "./**"} for pattern in path_allow if isinstance(pattern, str)):
        issues.append(
            _issue(
                "broad_path_allowlist",
                "warning",
                "paths.allow includes a broad wildcard, which weakens the safety story for "
                "autonomous promotion.",
                field="paths.allow",
                blocking=False,
                fixable=False,
            )
        )

    if not path_deny:
        issues.append(
            _issue(
                "missing_path_denylist",
                "warning",
                "paths.deny is empty. Consider explicitly denying secrets, deploy, or production paths.",
                field="paths.deny",
                blocking=False,
                fixable=False,
            )
        )

    if unsafe:
        issues.append(
            _issue(
                "unsafe_autonomy_opt_in",
                "warning",
                "PROGRAM.md explicitly opts into ungated autonomous promotion.",
                field="promotion.allow_unsafe_without_evaluators",
                blocking=False,
                fixable=False,
            )
        )

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


def add_evaluator_template(path: str | Path | None, project_ref: str, template_id: str) -> dict[str, Any]:
    """Apply a suggested evaluator template to a project's PROGRAM.md."""
    root = Path(path or Path.cwd()).resolve()
    project = get_project(root, project_ref)
    program_path = project.program_path
    metadata, body = _load_program_source(program_path)
    templates = {item["id"]: item for item in evaluator_templates(root, project.directory)}
    template = templates.get(template_id)
    if template is None:
        available = ", ".join(sorted(templates)) or "none"
        raise ValueError(
            f"Unknown evaluator template {template_id!r}. Available templates: {available}"
        )

    evaluators = metadata.setdefault("evaluators", [])
    if not isinstance(evaluators, list):
        raise ValueError("PROGRAM.md evaluators must be a list before adding a template")
    evaluator_id = _normalize_command_id(template["id"])
    if any(
        isinstance(item, dict) and str(item.get("id", "")).strip() == evaluator_id
        for item in evaluators
    ):
        raise ValueError(f"PROGRAM.md already defines evaluator {evaluator_id!r}")
    evaluators.append(
        {
            "id": evaluator_id,
            "command": template["command"],
            "required": bool(template.get("required", True)),
        }
    )

    commands = metadata.setdefault("commands", {})
    if not isinstance(commands, dict):
        raise ValueError("PROGRAM.md commands must be a mapping before adding a template")
    command_allow = commands.setdefault("allow", [])
    if not isinstance(command_allow, list):
        raise ValueError("PROGRAM.md commands.allow must be a list before adding a template")
    if template["command"] not in command_allow:
        command_allow.append(template["command"])

    promotion = metadata.setdefault("promotion", {})
    if not isinstance(promotion, dict):
        raise ValueError("PROGRAM.md promotion must be a mapping before adding a template")
    requires_all = promotion.setdefault("requires_all", [])
    if not isinstance(requires_all, list):
        raise ValueError("PROGRAM.md promotion.requires_all must be a list before adding a template")
    if bool(template.get("required", True)) and evaluator_id not in requires_all:
        requires_all.append(evaluator_id)

    program_path.write_text(safe_dump_agency_md(metadata, body), encoding="utf-8")
    diagnosis = doctor_program(root, project.id)
    diagnosis["applied_template"] = template
    return diagnosis

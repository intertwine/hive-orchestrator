#!/usr/bin/env python3
"""Bump the semantic version in a pyproject.toml file."""

from __future__ import annotations

import sys
from pathlib import Path


def parse_version(version_str: str) -> tuple[int, int, int]:
    """Parse a semantic version string into integer parts."""
    parts = version_str.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {version_str}. Expected major.minor.patch")
    try:
        return int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError as exc:
        raise ValueError(
            f"Invalid version format: {version_str}. All parts must be integers"
        ) from exc


def bump_version(version_str: str, bump_type: str) -> str:
    """Return a bumped semantic version string."""
    major, minor, patch = parse_version(version_str)
    if bump_type == "major":
        return f"{major + 1}.0.0"
    if bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    if bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"Invalid bump type: {bump_type}. Must be patch, minor, or major")


def update_pyproject_version(pyproject_path: Path, bump_type: str) -> tuple[str, str]:
    """Update the project version in place and return the old/new values."""
    if not pyproject_path.exists():
        raise FileNotFoundError(f"pyproject.toml not found at: {pyproject_path}")

    content = pyproject_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    old_version: str | None = None
    new_version: str | None = None
    updated_lines: list[str] = []
    in_project_section = False

    for line in lines:
        stripped = line.strip()
        if stripped == "[project]":
            in_project_section = True
        elif stripped.startswith("["):
            in_project_section = False

        if in_project_section and stripped.startswith("version = "):
            quote = '"' if 'version = "' in line else "'"
            start = line.index(quote) + 1
            end = line.index(quote, start)
            old_version = line[start:end]
            new_version = bump_version(old_version, bump_type)
            indent = line[: line.index("version")]
            updated_lines.append(f'{indent}version = "{new_version}"')
            continue
        updated_lines.append(line)

    if old_version is None or new_version is None:
        raise ValueError("No version field found in pyproject.toml")

    pyproject_path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
    return old_version, new_version


def main() -> int:
    """CLI entrypoint."""
    if len(sys.argv) != 3:
        print("Usage: python scripts/bump_version.py <pyproject_path> <patch|minor|major>")
        return 1

    pyproject_path = Path(sys.argv[1])
    bump_type = sys.argv[2].lower()
    if bump_type not in {"patch", "minor", "major"}:
        print(f"Invalid bump type: {bump_type}", file=sys.stderr)
        return 1

    old_version, new_version = update_pyproject_version(pyproject_path, bump_type)
    print(f"{old_version} -> {new_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

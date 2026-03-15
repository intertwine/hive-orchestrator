"""Git worktree helpers for Hive runs."""

from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path
import subprocess

STATE_PATTERNS = (
    ".hive/tasks/**",
    ".hive/events/**",
    "GLOBAL.md",
    "AGENTS.md",
    "projects/**/AGENCY.md",
    "projects/**/PROGRAM.md",
)
DIFF_EXCLUDES = (":(exclude).hive/cache", ":(exclude).hive/worktrees")


def _run_git(
    repo_root: Path,
    *args: str,
    cwd: Path | None = None,
    capture_output: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd or repo_root,
        text=True,
        capture_output=capture_output,
        check=False,
    )


def ensure_git_repo(path: str | Path | None) -> Path:
    """Return the Git toplevel for a workspace or raise when unavailable."""
    root = Path(path or Path.cwd()).resolve()
    result = _run_git(root, "rev-parse", "--show-toplevel")
    if result.returncode != 0:
        raise ValueError(f"Hive runs require a Git repository: {result.stderr.strip() or root}")
    return Path(result.stdout.strip()).resolve()


def _matches_any(path: str, patterns: tuple[str, ...]) -> bool:
    normalized = path.strip().strip('"')
    return any(fnmatch(normalized, pattern) for pattern in patterns)


def ensure_clean_repo(path: str | Path | None) -> None:
    """Require a clean repo outside of known Hive state files."""
    root = ensure_git_repo(path)
    result = _run_git(root, "status", "--porcelain")
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or "Unable to inspect Git status")

    dirty_paths: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        candidate = line[3:]
        if " -> " in candidate:
            candidate = candidate.split(" -> ", 1)[1]
        if _matches_any(candidate, STATE_PATTERNS):
            continue
        dirty_paths.append(candidate)

    if dirty_paths:
        details = ", ".join(sorted(dirty_paths)[:5])
        raise ValueError(
            "Hive runs require a clean repo outside of canonical Hive state files. "
            f"Dirty paths: {details}"
        )


def current_head(path: str | Path | None) -> str:
    """Return the current HEAD commit for the workspace."""
    root = ensure_git_repo(path)
    result = _run_git(root, "rev-parse", "HEAD")
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or "Unable to resolve HEAD")
    return result.stdout.strip()


def create_run_worktree(
    path: str | Path | None,
    *,
    branch_name: str,
    worktree_path: str | Path,
) -> Path:
    """Create a linked Git worktree for a run."""
    root = ensure_git_repo(path)
    ensure_clean_repo(root)
    target = Path(worktree_path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    result = _run_git(
        root,
        "worktree",
        "add",
        "--quiet",
        "-b",
        branch_name,
        str(target),
        "HEAD",
    )
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or f"Unable to create run worktree at {target}")
    return target


def capture_worktree_state(
    worktree_path: str | Path,
    *,
    patch_path: str | Path,
) -> dict[str, object]:
    """Capture the current worktree patch and touched paths."""
    worktree = Path(worktree_path).resolve()
    patch_target = Path(patch_path).resolve()
    _run_git(worktree, "add", "-N", "--all", ".", cwd=worktree)
    diff = _run_git(
        worktree,
        "diff",
        "--binary",
        "HEAD",
        "--",
        ".",
        *DIFF_EXCLUDES,
        cwd=worktree,
    )
    names = _run_git(
        worktree,
        "diff",
        "--name-only",
        "HEAD",
        "--",
        ".",
        *DIFF_EXCLUDES,
        cwd=worktree,
    )
    if diff.returncode != 0:
        raise ValueError(diff.stderr.strip() or "Unable to capture run patch")
    if names.returncode != 0:
        raise ValueError(names.stderr.strip() or "Unable to capture touched paths")

    touched_paths = [line.strip() for line in names.stdout.splitlines() if line.strip()]
    patch_target.write_text(diff.stdout, encoding="utf-8")
    return {
        "patch_path": str(patch_target),
        "touched_paths": touched_paths,
        "has_changes": bool(touched_paths),
    }


__all__ = [
    "capture_worktree_state",
    "create_run_worktree",
    "current_head",
    "ensure_clean_repo",
    "ensure_git_repo",
]

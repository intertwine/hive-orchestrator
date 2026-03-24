"""Git worktree helpers for Hive runs."""

from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path
import shutil
import subprocess

STATE_PATTERNS = (
    ".hive/tasks/**",
    ".hive/events/**",
    ".hive/runs/**",
    "GLOBAL.md",
    "AGENTS.md",
    "projects/**/AGENCY.md",
    "projects/**/PROGRAM.md",
)
IGNORED_PATTERNS = (".hive/cache/**", ".hive/worktrees/**")
DIFF_EXCLUDES = (":(exclude).hive/cache", ":(exclude).hive/worktrees")


def _status_path(line: str) -> str:
    candidate = line[3:]
    if " -> " in candidate:
        candidate = candidate.split(" -> ", 1)[1]
    return candidate.strip()


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
    # fnmatch treats ** as a single-segment wildcard, so fall back to prefix
    # matching for patterns like ".hive/cache/**" that need recursive depth.
    for pattern in patterns:
        if pattern.endswith("/**"):
            prefix = pattern[:-3]
            if normalized == prefix or normalized.startswith(prefix + "/"):
                return True
        elif fnmatch(normalized, pattern):
            return True
    return False


def _has_committed_head(root: Path) -> bool:
    result = _run_git(root, "rev-parse", "--verify", "HEAD")
    return result.returncode == 0


def _git_commit_error(result: subprocess.CompletedProcess[str]) -> str:
    detail = (result.stderr or result.stdout or "").strip()
    if "Please tell me who you are" in detail or "unable to auto-detect email address" in detail:
        return (
            "Git needs user.name and user.email before Hive can create commits. "
            "Set them with `git config user.name ...` and `git config user.email ...`, then retry."
        )
    return detail or "Unable to create Git commit"


def split_dirty_paths(path: str | Path | None) -> dict[str, list[str]]:
    """Return dirty canonical and noncanonical paths for the workspace."""
    root = ensure_git_repo(path)
    result = _run_git(root, "status", "--porcelain", "--untracked-files=all")
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or "Unable to inspect Git status")

    canonical: list[str] = []
    noncanonical: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        candidate = _status_path(line)
        if _matches_any(candidate, IGNORED_PATTERNS):
            continue
        if _matches_any(candidate, STATE_PATTERNS):
            canonical.append(candidate)
        else:
            noncanonical.append(candidate)
    return {
        "canonical": sorted(dict.fromkeys(canonical)),
        "noncanonical": sorted(dict.fromkeys(noncanonical)),
    }


def restore_derived_state(path: str | Path | None) -> list[str]:
    """Reset tracked derived-state paths so they do not leave the repo dirty."""
    root = ensure_git_repo(path)
    status = _run_git(root, "status", "--porcelain", "--", ".hive/cache", ".hive/worktrees")
    if status.returncode != 0:
        raise ValueError(status.stderr.strip() or "Unable to inspect derived Hive state")

    tracked_paths = []
    untracked_paths = []
    for line in status.stdout.splitlines():
        if not line.strip():
            continue
        candidate = _status_path(line)
        if not _matches_any(candidate, IGNORED_PATTERNS):
            continue
        # Lines starting with "?" are untracked files (need rm, not restore).
        if line.startswith("?"):
            untracked_paths.append(candidate)
        else:
            tracked_paths.append(candidate)

    tracked_paths = sorted(set(tracked_paths))
    untracked_paths = sorted(set(untracked_paths))

    if not tracked_paths and not untracked_paths:
        return []

    restored: list[str] = []
    if tracked_paths:
        restore = _run_git(root, "restore", "--staged", "--worktree", "--", *tracked_paths)
        if restore.returncode != 0:
            raise ValueError(restore.stderr.strip() or "Unable to restore derived Hive state")
        restored.extend(tracked_paths)
    if untracked_paths:
        for upath in untracked_paths:
            full = root / upath
            if full.is_file():
                full.unlink()
            elif full.is_dir():
                shutil.rmtree(full, ignore_errors=True)
        restored.extend(untracked_paths)
    return restored


def ensure_clean_repo(path: str | Path | None) -> None:
    """Require a clean repo outside of known Hive state files."""
    root = ensure_git_repo(path)
    if not _has_committed_head(root):
        raise ValueError(
            "Hive runs need an initial Git commit before the first run. "
            'Run `hive workspace checkpoint --message "Bootstrap workspace"` '
            "or commit the workspace manually, then retry `hive run start`."
        )
    dirty = split_dirty_paths(root)
    if dirty["noncanonical"]:
        details = ", ".join(dirty["noncanonical"][:5])
        raise ValueError(
            "Hive runs require a clean repo outside of canonical Hive state files. "
            f"Dirty paths: {details}"
        )


def current_head(path: str | Path | None) -> str:
    """Return the current HEAD commit for the workspace."""
    root = ensure_git_repo(path)
    if not _has_committed_head(root):
        raise ValueError(
            "Hive runs need an initial Git commit before the first run. "
            'Run `hive workspace checkpoint --message "Bootstrap workspace"` '
            "or commit the workspace manually, then retry `hive run start`."
        )
    result = _run_git(root, "rev-parse", "HEAD")
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or "Unable to resolve HEAD")
    return result.stdout.strip()


def current_branch(path: str | Path | None) -> str:
    """Return the current branch name, or HEAD when detached."""
    root = ensure_git_repo(path)
    result = _run_git(root, "branch", "--show-current")
    if result.returncode == 0:
        branch = result.stdout.strip()
        if branch:
            return branch
    fallback = _run_git(root, "rev-parse", "--abbrev-ref", "HEAD")
    if fallback.returncode != 0:
        raise ValueError(fallback.stderr.strip() or "Unable to resolve current branch")
    return fallback.stdout.strip() or "HEAD"


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


def create_checkpoint_commit(
    path: str | Path | None,
    *,
    message: str,
) -> dict[str, object]:
    """Stage all repo changes and create a checkpoint commit."""
    root = ensure_git_repo(path)
    add_result = _run_git(root, "add", "-A", ".")
    if add_result.returncode != 0:
        raise ValueError(add_result.stderr.strip() or "Unable to stage workspace changes")
    status_result = _run_git(root, "status", "--porcelain")
    if status_result.returncode != 0:
        raise ValueError(status_result.stderr.strip() or "Unable to inspect Git status")
    if not status_result.stdout.strip():
        return {"commit": None, "committed": False, "message": "Workspace already clean"}

    commit_result = _run_git(root, "commit", "-m", message)
    if commit_result.returncode != 0:
        raise ValueError(_git_commit_error(commit_result))
    return {"commit": current_head(root), "committed": True, "message": message}


def commit_paths(
    path: str | Path | None,
    *,
    paths: list[str],
    message: str,
) -> str | None:
    """Stage specific paths and commit them if they changed."""
    root = ensure_git_repo(path)
    if not paths:
        return None
    add_result = _run_git(root, "add", "-A", "--", *paths)
    if add_result.returncode != 0:
        raise ValueError(add_result.stderr.strip() or "Unable to stage canonical Hive state")
    cached = _run_git(root, "diff", "--cached", "--name-only", "--")
    if cached.returncode != 0:
        raise ValueError(cached.stderr.strip() or "Unable to inspect staged changes")
    if not cached.stdout.strip():
        return None
    commit_result = _run_git(root, "commit", "-m", message)
    if commit_result.returncode != 0:
        raise ValueError(_git_commit_error(commit_result))
    return current_head(root)


def is_branch_merged(path: str | Path | None, branch_name: str) -> bool:
    """Return whether a branch is already reachable from HEAD."""
    root = ensure_git_repo(path)
    result = _run_git(root, "merge-base", "--is-ancestor", branch_name, "HEAD")
    return result.returncode == 0


def merge_branch(
    path: str | Path | None,
    *,
    branch_name: str,
    message: str,
) -> dict[str, object]:
    """Merge a branch into the current workspace branch."""
    root = ensure_git_repo(path)
    if is_branch_merged(root, branch_name):
        return {
            "already_merged": True,
            "merged": False,
            "branch_name": branch_name,
            "commit": current_head(root),
        }
    result = _run_git(root, "merge", "--no-ff", branch_name, "-m", message)
    if result.returncode != 0:
        raise ValueError(
            result.stderr.strip() or result.stdout.strip() or "Unable to merge run branch"
        )
    return {
        "already_merged": False,
        "merged": True,
        "branch_name": branch_name,
        "commit": current_head(root),
    }


def delete_branch(path: str | Path | None, branch_name: str) -> dict[str, object]:
    """Delete a merged local branch when it still exists."""
    root = ensure_git_repo(path)
    exists = _run_git(root, "show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}")
    if exists.returncode != 0:
        return {"deleted": False, "already_missing": True, "branch_name": branch_name}

    result = _run_git(root, "branch", "-d", branch_name)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "Unable to delete local branch"
        return {
            "deleted": False,
            "already_missing": False,
            "branch_name": branch_name,
            "warning": detail,
        }

    return {"deleted": True, "already_missing": False, "branch_name": branch_name}


def remove_worktree(path: str | Path | None, worktree_path: str | Path) -> dict[str, object]:
    """Remove a linked Git worktree if it still exists."""
    root = ensure_git_repo(path)
    target = Path(worktree_path).resolve()
    if not target.exists():
        return {
            "removed": False,
            "already_missing": True,
            "manual_cleanup": False,
            "path": str(target),
            "warnings": [],
        }

    result = _run_git(root, "worktree", "remove", "--force", str(target))
    warnings: list[str] = []
    manual_cleanup = False
    if result.returncode != 0 and target.exists():
        manual_cleanup = True
        detail = (
            result.stderr.strip()
            or result.stdout.strip()
            or f"Unable to remove run worktree at {target}"
        )
        warnings.append(
            "Git could not remove the linked worktree cleanly. "
            f"Falling back to filesystem cleanup and prune: {detail}"
        )
        try:
            shutil.rmtree(target)
        except OSError as exc:
            raise ValueError(f"Unable to remove run worktree at {target}: {exc}") from exc

    prune_result = _run_git(root, "worktree", "prune")
    if prune_result.returncode != 0:
        warnings.append(prune_result.stderr.strip() or "Git worktree prune reported an error")
    if target.exists():
        manual_cleanup = True
        try:
            shutil.rmtree(target)
        except OSError as exc:
            raise ValueError(f"Unable to remove run worktree at {target}: {exc}") from exc
    return {
        "removed": not target.exists(),
        "already_missing": False,
        "manual_cleanup": manual_cleanup,
        "path": str(target),
        "warnings": warnings,
    }


def capture_worktree_state(
    worktree_path: str | Path,
    *,
    patch_path: str | Path,
    base_ref: str | None = None,
) -> dict[str, object]:
    """Capture the current worktree patch and touched paths."""
    worktree = Path(worktree_path).resolve()
    patch_target = Path(patch_path).resolve()
    _run_git(worktree, "add", "-N", "--all", ".", cwd=worktree)
    diff_base = base_ref or "HEAD"
    diff = _run_git(
        worktree,
        "diff",
        "--binary",
        diff_base,
        "--",
        ".",
        *DIFF_EXCLUDES,
        cwd=worktree,
    )
    names = _run_git(
        worktree,
        "diff",
        "--name-only",
        diff_base,
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
    "commit_paths",
    "capture_worktree_state",
    "current_branch",
    "create_checkpoint_commit",
    "create_run_worktree",
    "current_head",
    "delete_branch",
    "ensure_clean_repo",
    "ensure_git_repo",
    "is_branch_merged",
    "merge_branch",
    "remove_worktree",
    "split_dirty_paths",
]

"""Context compilation helpers for governed runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.hive.clock import utc_now_iso
from src.hive.retrieval_trace import classify_retrieval_intent, retrieval_provenance
from src.hive.search import search_workspace


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _estimate_tokens(content: str) -> int:
    words = len(content.split())
    return max(1, int(words * 1.35))


def _write_text(path: Path, content: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return str(path)


def _context_query(project, task) -> str:
    parts = [task.title, project.title]
    parts.extend(getattr(task, "labels", []) or [])
    parts.extend(getattr(task, "acceptance", []) or [])
    if getattr(task, "summary_md", None):
        parts.append(task.summary_md)
    if getattr(task, "notes_md", None):
        parts.append(task.notes_md)
    return " ".join(str(part).strip() for part in parts if str(part).strip())


def _skill_candidates(root: Path) -> list[Path]:
    candidates: list[Path] = []
    for relative in ((".agents", "skills"), ("skills",), (".codex", "skills")):
        skill_root = root.joinpath(*relative)
        if not skill_root.exists():
            continue
        candidates.extend(sorted(skill_root.glob("**/SKILL.md")))
    return candidates


def _score_skill(path: Path, query: str) -> int:
    lowered = path.read_text(encoding="utf-8").casefold()
    terms = {term.casefold() for term in query.split() if term.strip()}
    if not terms:
        return 0
    return sum(lowered.count(term) for term in terms)


def _selected_skills(root: Path, query: str, limit: int = 4) -> list[dict[str, str]]:
    scored: list[tuple[int, Path]] = []
    for candidate in _skill_candidates(root):
        score = _score_skill(candidate, query)
        if score <= 0:
            continue
        scored.append((score, candidate))
    scored.sort(key=lambda item: (-item[0], item[1].as_posix()))
    return [
        {
            "name": candidate.parent.name,
            "path": str(candidate.resolve()),
            "reason": "matched run brief and task keywords",
        }
        for _, candidate in scored[:limit]
    ]


def _selected_search_hits(
    candidates: list[dict[str, object]],
    *,
    query: str,
    limit: int = 4,
) -> list[dict[str, object]]:
    selected = list(candidates[:limit])
    if classify_retrieval_intent(query) != "policy":
        return selected
    if any(retrieval_provenance(hit) == "program_policy" for hit in selected):
        return selected
    for candidate in candidates:
        if retrieval_provenance(candidate) != "program_policy":
            continue
        if not selected:
            return [candidate]
        return [candidate, *selected[: max(0, limit - 1)]]
    return selected


def _manifest_entry(
    *,
    source_path: Path,
    source_type: str,
    required: bool,
    reason: str,
    truncated: bool = False,
) -> dict[str, Any]:
    content = _read_text(source_path)
    return {
        "id": source_path.as_posix(),
        "source_path": source_path.as_posix(),
        "source_type": source_type,
        "required": required,
        "tokens_estimate": _estimate_tokens(content),
        "reason": reason,
        "truncated": truncated,
    }


def compile_run_context(
    root: Path,
    *,
    run_id: str,
    project,
    task,
    run_directory: Path,
    driver: str,
    profile: str = "default",
) -> dict[str, Any]:
    """Compile the current workspace context into the normalized run artifact layout."""
    context_dir = run_directory / "context"
    compiled_dir = context_dir / "compiled"
    compiled_dir.mkdir(parents=True, exist_ok=True)

    run_brief_path = compiled_dir / "run-brief.md"
    agents_output_path = compiled_dir / "AGENTS.md"
    skills_manifest_path = compiled_dir / "skills-manifest.json"
    search_hits_path = compiled_dir / "search-hits.json"

    outputs: list[str] = []
    agency_document = _read_text(project.agency_path.resolve())
    program_document = _read_text(project.program_path.resolve())
    task_document = _read_text(Path(task.path).resolve())
    task_acceptance = (
        "\n".join(f"- {item}" for item in task.acceptance)
        if getattr(task, "acceptance", None)
        else ""
    )
    task_relevant_files = (
        "\n".join(f"- {item}" for item in task.relevant_files)
        if getattr(task, "relevant_files", None)
        else ""
    )
    run_brief = "\n".join(
        [
            "# Hive Run Brief",
            "",
            f"- Run: `{run_id}`",
            f"- Project: `{project.id}`",
            f"- Task: `{task.id}`",
            f"- Driver: `{driver}`",
            f"- Profile: `{profile}`",
            "",
            "## Task",
            task_document.strip(),
            "",
            "## Acceptance",
            task_acceptance or "- No explicit acceptance criteria recorded.",
            "",
            "## Relevant Files",
            task_relevant_files or "- No relevant files recorded yet.",
            "",
            "## Project Brief",
            agency_document.strip(),
            "",
            "## Program",
            program_document.strip(),
            "",
            "## Operator Notes",
            "Use the task file, PROGRAM.md, and this run directory as the source of truth.",
        ]
    ).strip()
    outputs.append(Path(_write_text(run_brief_path, run_brief + "\n")).name)

    agents_path = root / "AGENTS.md"
    if agents_path.exists():
        _write_text(agents_output_path, _read_text(agents_path))
        outputs.append(agents_output_path.name)

    query_text = _context_query(project, task)
    selected_skills = _selected_skills(root, query_text)
    retrieval_candidates = search_workspace(
        root,
        query_text,
        scopes=["workspace", "api", "examples", "project"],
        limit=8,
        project_id=project.id,
        task_id=task.id,
    )
    search_hits = _selected_search_hits(retrieval_candidates, query=query_text, limit=4)

    skills_manifest_path.write_text(
        json.dumps(
            {
                "driver": driver,
                "skills": selected_skills,
                "context_files": [
                    name for name in ("AGENTS.md", "CLAUDE.md") if (root / name).exists()
                ],
                "generated_at": utc_now_iso(),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    outputs.append(skills_manifest_path.name)
    search_hits_path.write_text(
        json.dumps(
            {
                "query": query_text,
                "results": search_hits,
                "generated_at": utc_now_iso(),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    outputs.append(search_hits_path.name)

    entries = [
        _manifest_entry(
            source_path=project.program_path.resolve(),
            source_type="program",
            required=True,
            reason="governing policy",
        ),
        _manifest_entry(
            source_path=project.agency_path.resolve(),
            source_type="agency",
            required=True,
            reason="project brief and operator notes",
        ),
        _manifest_entry(
            source_path=Path(task.path).resolve(),
            source_type="task",
            required=True,
            reason="canonical task contract",
        ),
    ]

    if agents_path.exists():
        entries.append(
            _manifest_entry(
                source_path=agents_path.resolve(),
                source_type="agents",
                required=False,
                reason="workspace operating instructions",
            )
        )

    for skill in selected_skills:
        skill_path = Path(skill["path"])
        if not skill_path.exists():
            continue
        entries.append(
            _manifest_entry(
                source_path=skill_path,
                source_type="skill",
                required=False,
                reason=skill["reason"],
            )
        )

    for hit in search_hits:
        hit_path = str(hit.get("path") or "").strip()
        if not hit_path or hit_path.startswith("package:"):
            continue
        candidate = Path(hit_path)
        if not candidate.exists():
            continue
        entries.append(
            _manifest_entry(
                source_path=candidate.resolve(),
                source_type="search-hit",
                required=False,
                reason="matched packaged docs or project graph context",
            )
        )

    memory_root = root / ".hive" / "memory" / "project" / project.id
    for candidate_name in ("profile.md", "active.md", "reflections.md", "observations.md"):
        candidate = memory_root / candidate_name
        if not candidate.exists():
            continue
        entries.append(
            _manifest_entry(
                source_path=candidate.resolve(),
                source_type="memory",
                required=False,
                reason=f"project memory: {candidate_name}",
            )
        )

    manifest = {
        "run_id": run_id,
        "generated_at": utc_now_iso(),
        "entries": entries,
        "outputs": outputs,
        "summary": {
            "driver": driver,
            "profile": profile,
            "project_id": project.id,
            "task_id": task.id,
        },
        "search_hits_path": str(search_hits_path),
        "skills_manifest_path": str(skills_manifest_path),
    }
    manifest_path = context_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "manifest": manifest,
        "manifest_path": manifest_path,
        "compiled_dir": compiled_dir,
        "run_brief_path": run_brief_path,
        "skills_manifest_path": skills_manifest_path,
        "query_text": query_text,
        "search_hits": search_hits,
        "retrieval_candidates": retrieval_candidates,
    }

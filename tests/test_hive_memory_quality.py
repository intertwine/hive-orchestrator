"""Focused tests for Hive 2.1 memory and scheduler quality."""

from __future__ import annotations

from pathlib import Path

from hive.cli.main import main as hive_main
from src.hive.memory import observe_project, reflect_project, search_memory, startup_context
from src.hive.scheduler.query import project_summary, ready_tasks
from src.hive.store.layout import ensure_layout, memory_project_dir
from src.hive.store.task_files import create_task, link_tasks


def test_project_scoped_memory_reflection_and_context(temp_hive_dir, temp_project):
    """Project memory should live under a project key and feed startup context."""
    ensure_layout(temp_hive_dir)
    hive_main(["--path", str(temp_hive_dir), "--json", "migrate", "v1-to-v2"])

    observe_project(
        temp_hive_dir,
        note="Need tighter launch messaging and a follow-up demo.",
        project_id="test-project",
    )
    observe_project(
        temp_hive_dir,
        note="Need tighter launch messaging and a follow-up demo.",
        project_id="test-project",
    )
    reflect_project(temp_hive_dir, project_id="test-project")

    project_memory = memory_project_dir(temp_hive_dir, project_id="test-project")
    assert (project_memory / "observations.md").exists()
    profile_text = (project_memory / "profile.md").read_text(encoding="utf-8")
    active_text = (project_memory / "active.md").read_text(encoding="utf-8")
    reflections_text = (project_memory / "reflections.md").read_text(encoding="utf-8")

    assert "## Changes" in profile_text
    assert "Need tighter launch messaging" in profile_text
    assert "Highest-Signal Notes" in reflections_text

    context = startup_context(temp_hive_dir, project_id="test-project", profile="default")
    section_names = [section["name"] for section in context["sections"]]
    assert "project-profile" in section_names
    assert "project-active" in section_names
    assert "Need tighter launch messaging" in context["content"]
    assert "Right Now" in active_text


def test_memory_search_prefers_project_local_docs_and_supports_legacy_fallback(temp_hive_dir, temp_project):
    """Search should include project-local memory and the legacy flat fallback."""
    ensure_layout(temp_hive_dir)
    hive_main(["--path", str(temp_hive_dir), "--json", "migrate", "v1-to-v2"])

    legacy_profile = memory_project_dir(temp_hive_dir) / "profile.md"
    legacy_profile.parent.mkdir(parents=True, exist_ok=True)
    legacy_profile.write_text("# Profile\n\n- Legacy launch context\n", encoding="utf-8")
    observe_project(
        temp_hive_dir,
        note="Agent-manager launch story with portfolio manager language.",
        project_id="test-project",
    )
    reflect_project(temp_hive_dir, project_id="test-project")

    results = search_memory(
        temp_hive_dir,
        "launch",
        scope="project",
        project_id="test-project",
        limit=8,
    )

    assert results
    assert results[0]["kind"] == "memory"
    assert results[0]["title"].startswith("test-project/")
    assert "::" in results[0]["title"]
    assert any("project-local" in hit["matches"] for hit in results)
    assert any(hit["title"].startswith("workspace/") for hit in results)


def test_ready_tasks_rank_by_score_and_project_summary_counts_true_ready(temp_hive_dir, temp_project):
    """Ready ranking should honor score and project summaries should exclude blocked work."""
    ensure_layout(temp_hive_dir)
    hive_main(["--path", str(temp_hive_dir), "--json", "migrate", "v1-to-v2"])

    blocker = create_task(
        temp_hive_dir,
        "test-project",
        "Foundational blocker",
        status="ready",
        priority=1,
        summary_md="Aging blocker task",
    )
    dependent = create_task(
        temp_hive_dir,
        "test-project",
        "Blocked follow-up",
        status="ready",
        priority=1,
        summary_md="Should not count as ready while blocked",
    )
    create_task(
        temp_hive_dir,
        "test-project",
        "Small polish",
        status="proposed",
        priority=3,
        summary_md="Lower-priority cleanup",
    )
    link_tasks(temp_hive_dir, blocker.id, "blocks", dependent.id)

    ranked = ready_tasks(temp_hive_dir, project_id="test-project", limit=None)
    ranked_ids = [item["id"] for item in ranked]
    assert dependent.id not in ranked_ids
    assert ranked[0]["id"] == blocker.id
    assert ranked[0]["score"] > ranked[-1]["score"]
    assert ranked[0]["reasons"]

    summary = next(item for item in project_summary(temp_hive_dir) if item["id"] == "test-project")
    assert summary["ready"] == len(ranked)
    assert summary["next_task_id"] == ranked[0]["id"]

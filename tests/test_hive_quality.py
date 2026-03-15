"""Focused tests for the Hive 2.1 quality pass."""

from __future__ import annotations

from pathlib import Path

from src.hive.memory import observe_project, reflect_project, search_memory, startup_context
from src.hive.migrate import migrate_v1_to_v2
from src.hive.search import search_workspace
from src.hive.scheduler.query import project_summary, ready_tasks
from src.hive.store.cache import rebuild_cache
from src.hive.store.task_files import create_task, get_task, link_tasks, list_tasks, save_task


class TestHiveSearchQuality:
    """Tests for cache-backed, explainable search."""

    def test_search_workspace_uses_fts_and_returns_explanations(self, temp_hive_dir, temp_project):
        """Canonical task hits should lead the result set with visible match reasons."""
        migrate_v1_to_v2(temp_hive_dir)
        task_id = ready_tasks(temp_hive_dir)[0]["id"]
        task = get_task(temp_hive_dir, task_id)
        task.title = "Amber kestrel launch slice"
        task.summary_md = "Amber kestrel delivery plan with rollout notes."
        save_task(temp_hive_dir, task)
        rebuild_cache(temp_hive_dir)

        results = search_workspace(temp_hive_dir, "amber kestrel", scopes=["workspace"], limit=6)

        assert results
        assert results[0]["kind"] == "task"
        assert "canonical task record" in results[0]["matches"]
        assert any("matched title terms" in reason for reason in results[0]["matches"])
        paths = [item.get("path") for item in results if item.get("path")]
        assert len(paths) == len(set(paths))

    def test_search_workspace_indexes_generic_docs_artifacts(self, temp_hive_dir, temp_project):
        """Workspace search should surface concrete docs artifacts beyond projections."""
        migrate_v1_to_v2(temp_hive_dir)
        docs_path = Path(temp_hive_dir) / "docs" / "opaline-flight-plan.md"
        session_context_path = Path(temp_hive_dir) / "SESSION_CONTEXT.md"
        docs_path.parent.mkdir(parents=True, exist_ok=True)
        docs_path.write_text(
            "# Opaline Flight Plan\n\nA crisp artifact for the launch runway.\n",
            encoding="utf-8",
        )
        session_context_path.write_text(
            "# Session Context\n\nOpaline runway notes that should not pollute generic search.\n",
            encoding="utf-8",
        )
        rebuild_cache(temp_hive_dir)

        results = search_workspace(temp_hive_dir, "opaline runway", scopes=["workspace"], limit=6)

        assert results
        assert results[0]["kind"] == "workspace_doc"
        assert Path(str(results[0]["path"])).resolve() == docs_path.resolve()
        assert "workspace document" in results[0]["matches"]
        assert all(Path(str(item["path"])).name != "SESSION_CONTEXT.md" for item in results)


class TestHiveMemoryQuality:
    """Tests for project-scoped synthesized memory."""

    def test_project_memory_is_scoped_to_the_selected_project(
        self, temp_hive_dir, temp_project, temp_blocked_project
    ):
        """Startup context and memory search should not leak another project's local memory."""
        migrate_v1_to_v2(temp_hive_dir)
        observe_project(temp_hive_dir, note="alpha-halo memory", project_id="test-project")
        observe_project(temp_hive_dir, note="beta-orbit memory", project_id="blocked-project")
        reflect_project(temp_hive_dir, project_id="test-project")
        reflect_project(temp_hive_dir, project_id="blocked-project")
        rebuild_cache(temp_hive_dir)

        context = startup_context(temp_hive_dir, project_id="test-project", query="alpha-halo")
        results = search_memory(
            temp_hive_dir,
            "memory",
            scope="project",
            project_id="test-project",
            limit=10,
        )

        assert "alpha-halo memory" in context["content"]
        assert "beta-orbit memory" not in context["content"]
        assert results
        assert any(item["kind"] == "memory" for item in results)
        assert all("blocked-project" not in str(item.get("path", "")) for item in results)

    def test_reflect_synthesizes_memory_with_provenance_and_change_sections(
        self, temp_hive_dir, temp_project
    ):
        """Reflection should synthesize repeated observations instead of stacking duplicates."""
        migrate_v1_to_v2(temp_hive_dir)
        observe_project(temp_hive_dir, note="Team prefers canonical task links.", project_id="test-project")
        observe_project(temp_hive_dir, note="Team prefers canonical task links.", project_id="test-project")
        observe_project(temp_hive_dir, note="Need a stronger reviewer loop.", project_id="test-project")

        paths = reflect_project(temp_hive_dir, project_id="test-project")
        profile_text = Path(paths["profile"]).read_text(encoding="utf-8")
        active_text = Path(paths["active"]).read_text(encoding="utf-8")

        assert "seen 2 times" in profile_text
        assert "## Changes" in profile_text
        assert "## Changes" in active_text
        assert profile_text.count("Team prefers canonical task links.") == 1


class TestHiveSchedulerQuality:
    """Tests for truthful and useful ready-task ranking."""

    def test_ready_tasks_uses_score_ordering_and_project_summary_matches_queue(
        self, temp_hive_dir, temp_project
    ):
        """Older ready tasks should outrank fresher peers, and project counts should stay truthful."""
        migrate_v1_to_v2(temp_hive_dir)
        older = create_task(temp_hive_dir, "test-project", "Older follow-up", priority=2)
        fresher = create_task(temp_hive_dir, "test-project", "Fresh follow-up", priority=2)
        blocked = create_task(temp_hive_dir, "test-project", "Blocked follow-up", priority=2)
        blocker = create_task(temp_hive_dir, "test-project", "Blocker", priority=1)
        link_tasks(temp_hive_dir, blocker.id, "blocks", blocked.id)

        older.created_at = "2024-01-01T00:00:00Z"
        older.updated_at = "2024-01-01T00:00:00Z"
        save_task(temp_hive_dir, older)
        fresher.created_at = "2026-03-15T00:00:00Z"
        fresher.updated_at = "2026-03-15T00:00:00Z"
        save_task(temp_hive_dir, fresher)

        queue = ready_tasks(temp_hive_dir, project_id="test-project", limit=None)
        queue_ids = [item["id"] for item in queue]
        summary = next(item for item in project_summary(temp_hive_dir) if item["id"] == "test-project")

        assert older.id in queue_ids
        assert fresher.id in queue_ids
        assert blocked.id not in queue_ids
        assert queue_ids.index(older.id) < queue_ids.index(fresher.id)
        assert summary["ready"] == len(queue)
        assert summary["next_task_id"] == queue[0]["id"]

    def test_dependency_cleared_blocked_task_reenters_ready_queue(self, temp_hive_dir):
        """Tasks blocked only by a completed dependency should become ready again."""
        agency_path = Path(temp_hive_dir) / "projects" / "dependency-unblock" / "AGENCY.md"
        agency_path.parent.mkdir(parents=True, exist_ok=True)
        agency_path.write_text(
            """---
project_id: dependency-unblock
status: active
priority: high
---
# Dependency Unblock Project

## Tasks
- [ ] Define the launch outline
- [ ] Publish landing page
  depends on Define the launch outline
""",
            encoding="utf-8",
        )

        migrate_v1_to_v2(temp_hive_dir)
        tasks = {
            task.title: task
            for task in list_tasks(temp_hive_dir)
            if task.project_id == "dependency-unblock"
        }
        outline = tasks["Define the launch outline"]
        publish = tasks["Publish landing page"]

        outline.status = "done"
        save_task(temp_hive_dir, outline)

        queue = ready_tasks(temp_hive_dir, project_id="dependency-unblock", limit=None)
        summary = next(
            item for item in project_summary(temp_hive_dir) if item["id"] == "dependency-unblock"
        )

        assert any(item["id"] == publish.id for item in queue)
        promoted = next(item for item in queue if item["id"] == publish.id)
        assert promoted["status"] == "ready"
        assert summary["ready"] == 1
        assert summary["next_task_id"] == publish.id
        assert summary["blocked"] == 0

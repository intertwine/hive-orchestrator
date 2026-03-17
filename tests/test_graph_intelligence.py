"""Tests for graph-aware project and task ranking."""

from __future__ import annotations

from src.hive.scheduler.query import dependency_summary, ready_tasks
from src.hive.store.projects import create_project, get_project, save_project
from src.hive.store.task_files import create_task, link_tasks


class TestGraphIntelligence:
    """Dependency summaries and ready ranking should use real graph structure."""

    def test_dependency_summary_reports_project_cycles(self, temp_hive_dir):
        create_project(temp_hive_dir, "alpha", title="Alpha")
        create_project(temp_hive_dir, "beta", title="Beta")
        create_project(temp_hive_dir, "gamma", title="Gamma")

        alpha = get_project(temp_hive_dir, "alpha")
        beta = get_project(temp_hive_dir, "beta")
        gamma = get_project(temp_hive_dir, "gamma")
        alpha.metadata["dependencies"] = {"blocked_by": ["beta"], "blocks": []}
        beta.metadata["dependencies"] = {"blocked_by": ["gamma"], "blocks": []}
        gamma.metadata["dependencies"] = {"blocked_by": ["alpha"], "blocks": []}
        save_project(alpha)
        save_project(beta)
        save_project(gamma)

        summary = dependency_summary(temp_hive_dir)
        project_map = {item["project_id"]: item for item in summary["projects"]}

        assert summary["has_cycles"] is True
        assert summary["cycles"]
        assert project_map["alpha"]["in_cycle"] is True
        assert "dependency cycle" in project_map["alpha"]["blocking_reasons"]
        assert project_map["beta"]["in_cycle"] is True
        assert project_map["gamma"]["in_cycle"] is True

    def test_ready_tasks_promote_work_that_unblocks_more_of_the_graph(self, temp_hive_dir):
        create_project(temp_hive_dir, "demo", title="Demo")
        chain_root = create_task(temp_hive_dir, "demo", "Unblock the chain", status="ready", priority=2)
        chain_mid = create_task(temp_hive_dir, "demo", "Second step", status="proposed", priority=2)
        chain_leaf = create_task(temp_hive_dir, "demo", "Third step", status="proposed", priority=2)
        leaf = create_task(temp_hive_dir, "demo", "Independent leaf", status="ready", priority=2)
        link_tasks(temp_hive_dir, chain_root.id, "blocks", chain_mid.id)
        link_tasks(temp_hive_dir, chain_mid.id, "blocks", chain_leaf.id)

        ranked = ready_tasks(temp_hive_dir, project_id="demo", limit=2)

        assert ranked[0]["id"] == chain_root.id
        assert ranked[0]["graph_rank"]["task_unblock_count"] >= 2
        assert any("unblock" in reason.lower() for reason in ranked[0]["reasons"])
        assert ranked[1]["id"] == leaf.id

"""
Regression tests for AgentDispatcher retry behavior.

The dispatcher should not retry the same failed task in a later iteration after
refreshing the ready queue.
"""

# pylint: disable=unused-argument,import-error,wrong-import-position

import os
import sys
from unittest.mock import patch

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agent_dispatcher import AgentDispatcher


class TestAgentDispatcherRetryBug:
    """Tests for the attempted-task filtering in AgentDispatcher.run()."""

    def test_does_not_retry_failed_tasks_after_successful_dispatch(self, temp_hive_dir):
        """Each ready task is attempted at most once even after queue refreshes."""
        task1 = {
            "id": "task_1",
            "project_id": "demo",
            "title": "Oldest",
            "priority": 1,
            "created_at": "2025-01-01T00:00:00Z",
        }
        task2 = {
            "id": "task_2",
            "project_id": "demo",
            "title": "Middle",
            "priority": 1,
            "created_at": "2025-01-02T00:00:00Z",
        }
        task3 = {
            "id": "task_3",
            "project_id": "demo",
            "title": "Newest",
            "priority": 1,
            "created_at": "2025-01-03T00:00:00Z",
        }

        claimed = set()
        dispatch_calls = []

        def mock_ready_work():
            ready = []
            if "task_1" not in claimed:
                ready.append(task1)
            if "task_2" not in claimed:
                ready.append(task2)
            if "task_3" not in claimed:
                ready.append(task3)
            return ready

        def mock_dispatch(task):
            task_id = task["id"]
            dispatch_calls.append(task_id)
            if task_id == "task_1":
                claimed.add("task_1")
                return True
            if task_id == "task_2":
                return False
            if task_id == "task_3":
                claimed.add("task_3")
                return True
            return False

        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=False)

        with patch.object(dispatcher, "ready_work", side_effect=mock_ready_work):
            with patch.object(dispatcher, "dispatch", side_effect=mock_dispatch):
                with patch.object(dispatcher, "validate_environment", return_value=True):
                    dispatcher.run(max_dispatches=3)

        assert dispatch_calls == ["task_1", "task_2", "task_3"]

    def test_respects_max_dispatches_with_mixed_success_failure(self, temp_hive_dir):
        """The dispatcher stops after the requested number of attempts."""
        tasks = [
            {
                "id": f"task_{index + 1}",
                "project_id": "demo",
                "title": f"Task {index + 1}",
                "priority": 1,
                "created_at": f"2025-01-0{index + 1}T00:00:00Z",
            }
            for index in range(5)
        ]

        claimed = set()
        dispatch_calls = []

        def mock_ready_work():
            return [task for task in tasks if task["id"] not in claimed]

        def mock_dispatch(task):
            task_id = task["id"]
            dispatch_calls.append(task_id)
            if task_id == "task_1":
                claimed.add("task_1")
                return True
            if task_id == "task_2":
                return False
            if task_id == "task_3":
                claimed.add("task_3")
                return True
            return True

        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=False)

        with patch.object(dispatcher, "ready_work", side_effect=mock_ready_work):
            with patch.object(dispatcher, "dispatch", side_effect=mock_dispatch):
                with patch.object(dispatcher, "validate_environment", return_value=True):
                    dispatcher.run(max_dispatches=3)

        assert dispatch_calls == ["task_1", "task_2", "task_3"]
        assert "task_4" not in dispatch_calls
        assert "task_5" not in dispatch_calls

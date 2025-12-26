"""
Test for AgentDispatcher retry bug fix.

Bug: When a successful dispatch is followed by failed dispatches, the manual
filtering of failed projects (lines 476-479 in agent_dispatcher.py) is lost
because ready_projects is refreshed from Cortex at the start of each iteration
when dispatched > 0.

This causes the dispatcher to waste iterations retrying projects that have
already failed, instead of moving on to the next available project.

Fix: Track attempted projects in a set and filter them out before selecting work.
"""

# pylint: disable=unused-argument,import-error,wrong-import-position

import sys
import os
from pathlib import Path
from unittest.mock import patch

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agent_dispatcher import AgentDispatcher


class TestAgentDispatcherRetryBug:
    """Tests for the retry bug fix in AgentDispatcher.run() method."""

    def test_does_not_retry_failed_projects_after_successful_dispatch(self, temp_hive_dir):
        """
        Test that failed projects are not retried after a successful dispatch.

        Scenario:
        - 3 ready projects: P1 (oldest), P2 (middle), P3 (newest)
        - max_dispatches = 3
        - P1: dispatch succeeds (claims it)
        - P2: dispatch fails (already assigned)
        - Iteration 3: should try P3, NOT retry P2

        Expected: dispatch called with ['p1', 'p2', 'p3']
        Buggy behavior: dispatch called with ['p1', 'p2', 'p2']
        """

        # Create mock projects with different timestamps for deterministic ordering
        project1 = {
            "path": str(Path(temp_hive_dir) / "p1" / "AGENCY.md"),
            "project_id": "p1",
            "metadata": {
                "owner": None,
                "project_id": "p1",
                "priority": "high",
                "last_updated": "2025-01-01T00:00:00Z",  # Oldest
            },
            "content": "# P1",
        }

        project2 = {
            "path": str(Path(temp_hive_dir) / "p2" / "AGENCY.md"),
            "project_id": "p2",
            "metadata": {
                "owner": "other-agent",  # Already assigned
                "project_id": "p2",
                "priority": "high",
                "last_updated": "2025-01-02T00:00:00Z",  # Middle
            },
            "content": "# P2",
        }

        project3 = {
            "path": str(Path(temp_hive_dir) / "p3" / "AGENCY.md"),
            "project_id": "p3",
            "metadata": {
                "owner": None,
                "project_id": "p3",
                "priority": "high",
                "last_updated": "2025-01-03T00:00:00Z",  # Newest
            },
            "content": "# P3",
        }

        # Track claimed projects to simulate realistic Cortex behavior
        claimed_projects = set()

        def mock_ready_work():
            """Returns projects that haven't been successfully claimed."""
            ready = []
            if "p1" not in claimed_projects:
                ready.append(project1)
            if "p2" not in claimed_projects:
                ready.append(project2)
            if "p3" not in claimed_projects:
                ready.append(project3)
            return ready

        # Track dispatch calls to verify behavior
        dispatch_calls = []

        def mock_dispatch(project):
            """Succeeds for P1 and P3, fails for P2."""
            project_id = project["project_id"]
            dispatch_calls.append(project_id)

            if project_id == "p1":
                claimed_projects.add("p1")
                return True
            elif project_id == "p2":
                # Simulates dispatch failure (e.g., already assigned check in dispatch method)
                return False
            elif project_id == "p3":
                claimed_projects.add("p3")
                return True
            return False

        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=False)

        with patch.object(dispatcher.cortex, "ready_work", side_effect=mock_ready_work):
            with patch.object(dispatcher, "dispatch", side_effect=mock_dispatch):
                with patch.object(dispatcher, "validate_environment", return_value=True):
                    dispatcher.run(max_dispatches=3)

        # Verify that each project was tried at most once
        p1_count = dispatch_calls.count("p1")
        p2_count = dispatch_calls.count("p2")
        p3_count = dispatch_calls.count("p3")

        # Assert each project tried at most once
        assert p1_count == 1, f"P1 should be tried once, but was tried {p1_count} times"
        assert p2_count == 1, f"P2 should be tried once, but was tried {p2_count} times"
        assert p3_count == 1, f"P3 should be tried once, but was tried {p3_count} times"

        # Assert correct ordering (oldest first)
        assert dispatch_calls == [
            "p1",
            "p2",
            "p3",
        ], f"Expected ['p1', 'p2', 'p3'], got {dispatch_calls}"

    def test_respects_max_dispatches_with_mixed_success_failure(self, temp_hive_dir):
        """
        Test that max_dispatches limit is respected even with failures.

        Scenario:
        - 5 ready projects
        - max_dispatches = 3
        - P1: success, P2: fail, P3: success, P4: not tried, P5: not tried

        Expected: Only 3 dispatch attempts total, no retries
        """
        projects = []
        for i in range(5):
            projects.append(
                {
                    "path": str(Path(temp_hive_dir) / f"p{i+1}" / "AGENCY.md"),
                    "project_id": f"p{i+1}",
                    "metadata": {
                        "owner": None,
                        "project_id": f"p{i+1}",
                        "priority": "high",
                        "last_updated": f"2025-01-{i+1:02d}T00:00:00Z",
                    },
                    "content": f"# P{i+1}",
                }
            )

        claimed_projects = set()
        dispatch_calls = []

        def mock_ready_work():
            """Returns projects not yet claimed."""
            return [p for p in projects if p["project_id"] not in claimed_projects]

        def mock_dispatch(project):
            """P1 succeeds, P2 fails, P3 succeeds."""
            project_id = project["project_id"]
            dispatch_calls.append(project_id)

            if project_id == "p1":
                claimed_projects.add("p1")
                return True
            elif project_id == "p2":
                # P2 always fails (already assigned by another process)
                return False
            elif project_id == "p3":
                claimed_projects.add("p3")
                return True
            # P4 and P5 should not be reached with max_dispatches=3
            return True

        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=False)

        with patch.object(dispatcher.cortex, "ready_work", side_effect=mock_ready_work):
            with patch.object(dispatcher, "dispatch", side_effect=mock_dispatch):
                with patch.object(dispatcher, "validate_environment", return_value=True):
                    dispatcher.run(max_dispatches=3)

        # Should have exactly 3 dispatch attempts
        assert len(dispatch_calls) == 3, f"Expected 3 dispatch attempts, got {len(dispatch_calls)}"

        # Should be P1, P2, P3 (no retries)
        assert dispatch_calls == [
            "p1",
            "p2",
            "p3",
        ], f"Expected ['p1', 'p2', 'p3'], got {dispatch_calls}"

        # P4 and P5 should not have been attempted
        assert "p4" not in dispatch_calls
        assert "p5" not in dispatch_calls

    def test_handles_all_failures_gracefully(self, temp_hive_dir):
        """
        Test that the dispatcher handles all failures gracefully.

        Scenario:
        - 3 ready projects
        - max_dispatches = 3
        - All dispatches fail

        Expected: Each project tried once, no retries
        """
        projects = []
        for i in range(3):
            projects.append(
                {
                    "path": str(Path(temp_hive_dir) / f"p{i+1}" / "AGENCY.md"),
                    "project_id": f"p{i+1}",
                    "metadata": {
                        "owner": None,
                        "project_id": f"p{i+1}",
                        "priority": "high",
                        "last_updated": f"2025-01-{i+1:02d}T00:00:00Z",
                    },
                    "content": f"# P{i+1}",
                }
            )

        dispatch_calls = []

        def mock_ready_work():
            """Returns all projects (none ever get claimed)."""
            return projects

        def mock_dispatch(project):
            """All dispatches fail."""
            dispatch_calls.append(project["project_id"])
            return False

        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=False)

        with patch.object(dispatcher.cortex, "ready_work", side_effect=mock_ready_work):
            with patch.object(dispatcher, "dispatch", side_effect=mock_dispatch):
                with patch.object(dispatcher, "validate_environment", return_value=True):
                    dispatcher.run(max_dispatches=3)

        # Should have exactly 3 dispatch attempts (one per project)
        assert len(dispatch_calls) == 3, f"Expected 3 dispatch attempts, got {len(dispatch_calls)}"

        # Each project should be tried exactly once
        assert dispatch_calls.count("p1") == 1, "P1 should be tried exactly once"
        assert dispatch_calls.count("p2") == 1, "P2 should be tried exactly once"
        assert dispatch_calls.count("p3") == 1, "P3 should be tried exactly once"

    def test_handles_all_successes(self, temp_hive_dir):
        """
        Test that the dispatcher handles all successes correctly.

        Scenario:
        - 3 ready projects
        - max_dispatches = 3
        - All dispatches succeed

        Expected: Each project tried once, all claimed
        """
        projects = []
        for i in range(3):
            projects.append(
                {
                    "path": str(Path(temp_hive_dir) / f"p{i+1}" / "AGENCY.md"),
                    "project_id": f"p{i+1}",
                    "metadata": {
                        "owner": None,
                        "project_id": f"p{i+1}",
                        "priority": "high",
                        "last_updated": f"2025-01-{i+1:02d}T00:00:00Z",
                    },
                    "content": f"# P{i+1}",
                }
            )

        claimed_projects = set()
        dispatch_calls = []

        def mock_ready_work():
            """Returns only unclaimed projects."""
            return [p for p in projects if p["project_id"] not in claimed_projects]

        def mock_dispatch(project):
            """All dispatches succeed."""
            project_id = project["project_id"]
            dispatch_calls.append(project_id)
            claimed_projects.add(project_id)
            return True

        dispatcher = AgentDispatcher(base_path=temp_hive_dir, dry_run=False)

        with patch.object(dispatcher.cortex, "ready_work", side_effect=mock_ready_work):
            with patch.object(dispatcher, "dispatch", side_effect=mock_dispatch):
                with patch.object(dispatcher, "validate_environment", return_value=True):
                    dispatcher.run(max_dispatches=3)

        # Should have exactly 3 dispatch attempts (one per project)
        assert len(dispatch_calls) == 3, f"Expected 3 dispatch attempts, got {len(dispatch_calls)}"

        # All projects should have been tried exactly once
        assert dispatch_calls == ["p1", "p2", "p3"]
        assert len(claimed_projects) == 3

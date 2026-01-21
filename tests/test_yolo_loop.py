"""Tests for the YOLO Loop module."""

import time
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from src.yolo_loop import (
    YoloLoop,
    LoopConfig,
    LoopStatus,
    LoopState,
    ExecutionBackend,
    LoomWeaver,
    YoloRunner,
)


class TestLoopConfig:
    """Test LoopConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = LoopConfig(prompt="Test prompt")

        assert config.prompt == "Test prompt"
        assert config.max_iterations == 50
        assert config.timeout_seconds == 3600
        assert config.backend == ExecutionBackend.SUBPROCESS
        assert config.circuit_breaker_threshold == 5
        assert config.rate_limit_per_hour == 100
        assert config.cooldown_seconds == 5
        assert "LOOP_COMPLETE" in config.completion_markers

    def test_custom_config(self):
        """Test custom configuration values."""
        config = LoopConfig(
            prompt="Custom prompt",
            max_iterations=20,
            timeout_seconds=1800,
            backend=ExecutionBackend.DOCKER,
            circuit_breaker_threshold=3,
        )

        assert config.prompt == "Custom prompt"
        assert config.max_iterations == 20
        assert config.timeout_seconds == 1800
        assert config.backend == ExecutionBackend.DOCKER
        assert config.circuit_breaker_threshold == 3


class TestLoopState:
    """Test LoopState dataclass."""

    def test_initial_state(self):
        """Test initial state values."""
        config = LoopConfig(prompt="Test")
        state = LoopState(loop_id="test-123", config=config)

        assert state.loop_id == "test-123"
        assert state.status == LoopStatus.PENDING
        assert state.current_iteration == 0
        assert state.consecutive_failures == 0
        assert state.start_time is None
        assert state.end_time is None
        assert state.last_output == ""
        assert len(state.error_log) == 0

    def test_to_dict(self):
        """Test state serialization."""
        config = LoopConfig(prompt="Test")
        state = LoopState(loop_id="test-123", config=config)
        state.status = LoopStatus.RUNNING
        state.current_iteration = 5
        state.start_time = time.time()

        state_dict = state.to_dict()

        assert state_dict["loop_id"] == "test-123"
        assert state_dict["status"] == "running"
        assert state_dict["current_iteration"] == 5
        assert state_dict["max_iterations"] == 50


class TestYoloLoop:
    """Test YoloLoop class."""

    def test_loop_id_generation(self):
        """Test that unique loop IDs are generated."""
        config = LoopConfig(prompt="Test prompt")
        loop1 = YoloLoop(config)
        loop2 = YoloLoop(config)

        assert loop1.loop_id != loop2.loop_id
        assert loop1.loop_id.startswith("yolo-")
        assert loop2.loop_id.startswith("yolo-")

    def test_rate_limit_check(self):
        """Test rate limiting logic."""
        config = LoopConfig(prompt="Test", rate_limit_per_hour=10)
        loop = YoloLoop(config)

        # Should be within limits initially
        assert loop._check_rate_limit() is True

        # Simulate hitting limit
        loop.state.api_calls_this_hour = 10
        assert loop._check_rate_limit() is False

    def test_circuit_breaker_check(self):
        """Test circuit breaker logic."""
        config = LoopConfig(prompt="Test", circuit_breaker_threshold=3)
        loop = YoloLoop(config)

        # Should be ok initially
        assert loop._check_circuit_breaker() is True

        # Simulate failures
        loop.state.consecutive_failures = 3
        assert loop._check_circuit_breaker() is False

    def test_completion_detection(self):
        """Test completion marker detection."""
        config = LoopConfig(prompt="Test")
        loop = YoloLoop(config)

        # Standard completion marker
        assert loop._check_completion("Task done. LOOP_COMPLETE") is True
        assert loop._check_completion("loop_complete in output") is True

        # Alternative markers
        assert loop._check_completion("ALL_TASKS_DONE") is True
        assert loop._check_completion("EXIT_SIGNAL received") is True

        # No marker
        assert loop._check_completion("Just some normal output") is False

    def test_iteration_prompt_building(self):
        """Test prompt construction for iterations."""
        config = LoopConfig(prompt="Fix all bugs")
        loop = YoloLoop(config)

        prompt = loop._build_iteration_prompt(5)

        assert "Fix all bugs" in prompt
        assert "Iteration: 5" in prompt
        assert "LOOP_COMPLETE" in prompt
        assert loop.loop_id in prompt

    @patch("src.yolo_loop.subprocess.run")
    def test_execute_subprocess_success(self, mock_run):
        """Test successful subprocess execution."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Task completed successfully",
            stderr="",
        )

        config = LoopConfig(prompt="Test", working_dir="/tmp")
        loop = YoloLoop(config)

        success, output = loop._execute_subprocess("Test prompt")

        assert success is True
        assert "Task completed successfully" in output
        mock_run.assert_called_once()

    @patch("src.yolo_loop.subprocess.run")
    def test_execute_subprocess_failure(self, mock_run):
        """Test failed subprocess execution."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error occurred",
        )

        config = LoopConfig(prompt="Test", working_dir="/tmp")
        loop = YoloLoop(config)

        success, output = loop._execute_subprocess("Test prompt")

        assert success is False
        assert "Error occurred" in output

    @patch("src.yolo_loop.subprocess.run")
    def test_execute_subprocess_timeout(self, mock_run):
        """Test subprocess timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=10)

        config = LoopConfig(prompt="Test", working_dir="/tmp")
        loop = YoloLoop(config)

        success, output = loop._execute_subprocess("Test prompt")

        assert success is False
        assert "timeout" in output.lower()

    @patch("src.yolo_loop.subprocess.run")
    def test_execute_subprocess_not_found(self, mock_run):
        """Test claude CLI not found."""
        mock_run.side_effect = FileNotFoundError("claude not found")

        config = LoopConfig(prompt="Test", working_dir="/tmp")
        loop = YoloLoop(config)

        success, output = loop._execute_subprocess("Test prompt")

        assert success is False
        assert "not found" in output.lower()

    def test_stop_request(self):
        """Test stop request handling."""
        config = LoopConfig(prompt="Test")
        loop = YoloLoop(config)

        assert loop._stop_requested is False

        loop.stop()

        assert loop._stop_requested is True

    @patch.object(YoloLoop, "_execute_iteration")
    def test_run_completion(self, mock_execute):
        """Test loop runs until completion marker."""
        mock_execute.side_effect = [
            (True, "Working on it..."),
            (True, "Still working..."),
            (True, "Done! LOOP_COMPLETE"),
        ]

        config = LoopConfig(prompt="Test", max_iterations=10, cooldown_seconds=0)
        loop = YoloLoop(config)

        state = loop.run()

        assert state.status == LoopStatus.COMPLETED
        assert state.current_iteration == 3
        assert mock_execute.call_count == 3

    @patch.object(YoloLoop, "_execute_iteration")
    def test_run_max_iterations(self, mock_execute):
        """Test loop stops at max iterations."""
        mock_execute.return_value = (True, "Working...")

        config = LoopConfig(prompt="Test", max_iterations=5, cooldown_seconds=0)
        loop = YoloLoop(config)

        state = loop.run()

        assert state.status == LoopStatus.FAILED
        assert state.current_iteration == 5

    @patch.object(YoloLoop, "_execute_iteration")
    def test_run_circuit_breaker(self, mock_execute):
        """Test circuit breaker triggers."""
        mock_execute.return_value = (False, "Error!")

        config = LoopConfig(
            prompt="Test",
            max_iterations=50,
            circuit_breaker_threshold=3,
            cooldown_seconds=0,
        )
        loop = YoloLoop(config)

        state = loop.run()

        assert state.status == LoopStatus.CIRCUIT_BREAK
        assert state.consecutive_failures >= 3


class TestLoomWeaver:
    """Test LoomWeaver class."""

    def test_initialization(self, temp_hive_dir):
        """Test LoomWeaver initialization."""
        weaver = LoomWeaver(
            base_path=temp_hive_dir,
            max_parallel_agents=5,
        )

        assert weaver.max_parallel_agents == 5
        assert weaver.backend == ExecutionBackend.SUBPROCESS

    def test_discover_ready_work(self, temp_hive_dir, temp_project):
        """Test discovering ready work."""
        weaver = LoomWeaver(base_path=temp_hive_dir)

        ready = weaver.discover_ready_work()

        # temp_project creates an active, unclaimed project
        assert len(ready) >= 1
        project_ids = [p["project_id"] for p in ready]
        assert "test-project" in project_ids

    def test_discover_ready_work_excludes_blocked(
        self, temp_hive_dir, temp_project, temp_blocked_project
    ):
        """Test that blocked projects are excluded."""
        weaver = LoomWeaver(base_path=temp_hive_dir)

        ready = weaver.discover_ready_work()

        project_ids = [p["project_id"] for p in ready]
        assert "test-project" in project_ids
        assert "blocked-project" not in project_ids

    def test_discover_ready_work_excludes_claimed(
        self, temp_hive_dir, temp_project, temp_claimed_project
    ):
        """Test that claimed projects are excluded."""
        weaver = LoomWeaver(base_path=temp_hive_dir)

        ready = weaver.discover_ready_work()

        project_ids = [p["project_id"] for p in ready]
        assert "test-project" in project_ids
        assert "claimed-project" not in project_ids

    def test_create_loop_for_project(self, temp_hive_dir, temp_project):
        """Test creating a loop for a project."""
        weaver = LoomWeaver(base_path=temp_hive_dir)
        projects = weaver.discover_ready_work()
        project = projects[0]

        loop = weaver.create_loop_for_project(project, max_iterations=25)

        assert loop.config.max_iterations == 25
        assert loop.config.project_id == project["project_id"]
        assert "test-project" in loop.config.prompt

    def test_claim_project(self, temp_hive_dir, temp_project):
        """Test claiming a project."""
        weaver = LoomWeaver(base_path=temp_hive_dir)
        projects = weaver.discover_ready_work()
        project = projects[0]

        success = weaver.claim_project(project, "test-loop-123")

        assert success is True

        # Verify the file was updated
        from src.security import safe_load_agency_md
        parsed = safe_load_agency_md(Path(project["path"]))
        assert parsed.metadata["owner"] == "yolo-loop:test-loop-123"
        assert "YOLO Loop" in parsed.content

    def test_claim_already_claimed(self, temp_hive_dir, temp_claimed_project):
        """Test claiming an already-claimed project fails."""
        weaver = LoomWeaver(base_path=temp_hive_dir)

        # Load the claimed project directly
        from src.security import safe_load_agency_md
        parsed = safe_load_agency_md(Path(temp_claimed_project))

        project = {
            "path": temp_claimed_project,
            "project_id": "claimed-project",
            "metadata": dict(parsed.metadata),
            "content": parsed.content,
        }

        success = weaver.claim_project(project, "test-loop-456")

        # Should fail because project is already owned
        assert success is False

    def test_release_project(self, temp_hive_dir, temp_project):
        """Test releasing a project."""
        weaver = LoomWeaver(base_path=temp_hive_dir)
        projects = weaver.discover_ready_work()
        project = projects[0]

        # First claim it
        weaver.claim_project(project, "test-loop-789")

        # Then release it
        success = weaver.release_project(project, "test-loop-789", LoopStatus.COMPLETED)

        assert success is True

        # Verify the file was updated
        from src.security import safe_load_agency_md
        parsed = safe_load_agency_md(Path(project["path"]))
        assert parsed.metadata["owner"] is None
        assert parsed.metadata["status"] == "completed"


class TestYoloRunner:
    """Test YoloRunner high-level interface."""

    @patch.object(YoloLoop, "run")
    def test_run_single(self, mock_run):
        """Test running a single loop."""
        mock_state = LoopState(
            loop_id="test-123",
            config=LoopConfig(prompt="Test"),
        )
        mock_state.status = LoopStatus.COMPLETED
        mock_state.current_iteration = 10
        mock_run.return_value = mock_state

        state = YoloRunner.run_single(
            prompt="Test prompt",
            max_iterations=20,
        )

        assert state.status == LoopStatus.COMPLETED
        mock_run.assert_called_once()

    @patch.object(LoomWeaver, "weave")
    def test_run_hive(self, mock_weave, temp_hive_dir):
        """Test running Loom mode."""
        mock_weave.return_value = {"loop-1": MagicMock(status=LoopStatus.COMPLETED)}

        results = YoloRunner.run_hive(
            base_path=temp_hive_dir,
            max_parallel=2,
        )

        assert "loop-1" in results
        mock_weave.assert_called_once()

    def test_run_project_claim_failure(self, temp_hive_dir, temp_claimed_project):
        """Test that run_project fails if project is already claimed."""
        with pytest.raises(RuntimeError, match="Could not claim project"):
            YoloRunner.run_project(
                project_path=temp_claimed_project,
                max_iterations=5,
            )


class TestExecutionBackend:
    """Test ExecutionBackend enum."""

    def test_backend_values(self):
        """Test backend enum values."""
        assert ExecutionBackend.SUBPROCESS.value == "subprocess"
        assert ExecutionBackend.DOCKER.value == "docker"
        assert ExecutionBackend.CLOUD_SANDBOX.value == "cloud_sandbox"

    def test_backend_from_string(self):
        """Test creating backend from string."""
        assert ExecutionBackend("subprocess") == ExecutionBackend.SUBPROCESS
        assert ExecutionBackend("docker") == ExecutionBackend.DOCKER


class TestLoopStatus:
    """Test LoopStatus enum."""

    def test_status_values(self):
        """Test status enum values."""
        assert LoopStatus.PENDING.value == "pending"
        assert LoopStatus.RUNNING.value == "running"
        assert LoopStatus.COMPLETED.value == "completed"
        assert LoopStatus.FAILED.value == "failed"
        assert LoopStatus.CANCELLED.value == "cancelled"
        assert LoopStatus.TIMEOUT.value == "timeout"
        assert LoopStatus.CIRCUIT_BREAK.value == "circuit_break"

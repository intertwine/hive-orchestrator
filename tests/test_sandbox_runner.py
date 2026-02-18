"""Tests for the Sandbox Runner module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from src.sandbox_runner import (
    SandboxConfig,
    SandboxProvider,
    DockerSandbox,
    SandboxRunner,
    generate_docker_compose,
)


class TestSandboxConfig:
    """Test SandboxConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = SandboxConfig()

        assert config.provider == SandboxProvider.DOCKER
        assert config.docker_image == "docker/sandbox-templates:claude-code"
        assert config.docker_network == "none"
        assert config.docker_memory_limit == "4g"
        assert config.docker_cpu_limit == 2.0
        assert config.state_dir == ".yolo-state"
        assert config.persist_sessions is True
        assert config.daemon_port == 8765
        assert config.poll_interval == 300

    def test_custom_config(self):
        """Test custom configuration values."""
        config = SandboxConfig(
            provider=SandboxProvider.LOCAL,
            docker_image="custom-image:latest",
            docker_memory_limit="8g",
            poll_interval=600,
        )

        assert config.provider == SandboxProvider.LOCAL
        assert config.docker_image == "custom-image:latest"
        assert config.docker_memory_limit == "8g"
        assert config.poll_interval == 600


class TestSandboxProvider:
    """Test SandboxProvider enum."""

    def test_provider_values(self):
        """Test provider enum values."""
        assert SandboxProvider.DOCKER.value == "docker"
        assert SandboxProvider.DOCKER_COMPOSE.value == "docker-compose"
        assert SandboxProvider.CLOUDFLARE.value == "cloudflare"
        assert SandboxProvider.MODAL.value == "modal"
        assert SandboxProvider.LOCAL.value == "local"


class TestDockerSandbox:
    """Test DockerSandbox class."""

    @patch("src.sandbox_runner.subprocess.run")
    def test_validate_docker_available(self, mock_run):
        """Test Docker validation when Docker is available."""
        mock_run.return_value = MagicMock(returncode=0)

        config = SandboxConfig()
        sandbox = DockerSandbox(config)  # Should not raise

        mock_run.assert_called_once()

    @patch("src.sandbox_runner.subprocess.run")
    def test_validate_docker_not_running(self, mock_run):
        """Test Docker validation when Docker is not running."""
        mock_run.return_value = MagicMock(returncode=1)

        config = SandboxConfig()

        with pytest.raises(RuntimeError, match="Docker is not running"):
            DockerSandbox(config)

    @patch("src.sandbox_runner.subprocess.run")
    def test_validate_docker_not_installed(self, mock_run):
        """Test Docker validation when Docker is not installed."""
        mock_run.side_effect = FileNotFoundError("docker not found")

        config = SandboxConfig()

        with pytest.raises(RuntimeError, match="Docker is not installed"):
            DockerSandbox(config)

    @patch("src.sandbox_runner.subprocess.run")
    def test_build_docker_command(self, mock_run):
        """Test Docker command construction."""
        mock_run.return_value = MagicMock(returncode=0)  # For validation

        config = SandboxConfig(
            docker_network="host",
            docker_memory_limit="2g",
            docker_cpu_limit=1.0,
        )
        sandbox = DockerSandbox(config)

        with tempfile.TemporaryDirectory() as temp_dir:
            cmd = sandbox._build_docker_command(
                prompt="Test prompt",
                working_dir=Path(temp_dir),
                model="claude-sonnet-4",
            )

        assert "docker" in cmd
        assert "run" in cmd
        assert "--rm" in cmd
        assert "--network=host" in cmd
        assert "--memory=2g" in cmd
        assert "--cpus=1.0" in cmd
        assert "-v" in cmd
        assert "claude" in cmd
        assert "--print" in cmd
        assert "--dangerously-skip-permissions" in cmd
        assert "Test prompt" in cmd
        assert "--model" in cmd
        assert "claude-sonnet-4" in cmd

    @patch("src.sandbox_runner.subprocess.run")
    def test_run_success(self, mock_run):
        """Test successful Docker run."""
        # First call for validation, second for run
        mock_run.side_effect = [
            MagicMock(returncode=0),  # Validation
            MagicMock(
                returncode=0,
                stdout="Task completed",
                stderr="",
            ),  # Run
        ]

        config = SandboxConfig()
        sandbox = DockerSandbox(config)

        with tempfile.TemporaryDirectory() as temp_dir:
            result = sandbox.run(
                prompt="Test prompt",
                working_dir=temp_dir,
            )

        assert result["success"] is True
        assert "Task completed" in result["output"]
        assert result["exit_code"] == 0
        assert result["elapsed_seconds"] > 0

    @patch("src.sandbox_runner.subprocess.run")
    def test_run_failure(self, mock_run):
        """Test failed Docker run."""
        mock_run.side_effect = [
            MagicMock(returncode=0),  # Validation
            MagicMock(
                returncode=1,
                stdout="",
                stderr="Error occurred",
            ),  # Run
        ]

        config = SandboxConfig()
        sandbox = DockerSandbox(config)

        with tempfile.TemporaryDirectory() as temp_dir:
            result = sandbox.run(
                prompt="Test prompt",
                working_dir=temp_dir,
            )

        assert result["success"] is False
        assert "Error occurred" in result["output"]
        assert result["exit_code"] == 1

    @patch("src.sandbox_runner.subprocess.run")
    def test_run_timeout(self, mock_run):
        """Test Docker run timeout."""
        import subprocess
        mock_run.side_effect = [
            MagicMock(returncode=0),  # Validation
            subprocess.TimeoutExpired(cmd="docker", timeout=10),  # Run
        ]

        config = SandboxConfig()
        sandbox = DockerSandbox(config)

        with tempfile.TemporaryDirectory() as temp_dir:
            result = sandbox.run(
                prompt="Test prompt",
                working_dir=temp_dir,
                timeout=10,
            )

        assert result["success"] is False
        assert "timeout" in result["output"].lower()

    @patch("src.sandbox_runner.subprocess.run")
    def test_run_nonexistent_dir(self, mock_run):
        """Test run with nonexistent working directory."""
        mock_run.return_value = MagicMock(returncode=0)  # Validation

        config = SandboxConfig()
        sandbox = DockerSandbox(config)

        result = sandbox.run(
            prompt="Test prompt",
            working_dir="/nonexistent/path",
        )

        assert result["success"] is False
        assert "does not exist" in result["output"]


class TestSandboxRunner:
    """Test SandboxRunner class."""

    def test_initialization(self):
        """Test SandboxRunner initialization."""
        runner = SandboxRunner()
        assert runner.config is not None
        assert runner.config.provider == SandboxProvider.DOCKER

    def test_initialization_with_config(self):
        """Test SandboxRunner initialization with custom config."""
        config = SandboxConfig(poll_interval=600)
        runner = SandboxRunner(config)
        assert runner.config.poll_interval == 600

    @patch.object(DockerSandbox, "run")
    @patch.object(DockerSandbox, "_validate_docker")
    def test_run_docker(self, mock_validate, mock_run):
        """Test running in Docker sandbox."""
        mock_run.return_value = {
            "success": True,
            "output": "Done",
            "exit_code": 0,
            "elapsed_seconds": 5.0,
        }

        runner = SandboxRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            result = runner.run_docker(
                prompt="Test prompt",
                working_dir=temp_dir,
            )

        assert result["success"] is True
        mock_run.assert_called_once()

    def test_daemon_status_no_daemon(self, temp_hive_dir):
        """Test daemon status when no daemon is running."""
        runner = SandboxRunner()

        status = runner.daemon_status(hive_path=temp_hive_dir)

        assert status["running"] is False
        assert status["pid"] is None


class TestGenerateDockerCompose:
    """Test docker-compose generation."""

    def test_generate_docker_compose(self):
        """Test generating docker-compose.yml."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = generate_docker_compose(
                hive_path=temp_dir,
            )

            assert Path(output_path).exists()

            content = Path(output_path).read_text()
            assert "version:" in content
            assert "yolo-daemon" in content
            assert "ANTHROPIC_API_KEY" in content
            assert "/workspace" in content

    def test_generate_docker_compose_custom_output(self):
        """Test generating docker-compose.yml to custom path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_output = Path(temp_dir) / "custom-compose.yml"

            output_path = generate_docker_compose(
                hive_path=temp_dir,
                output_path=str(custom_output),
            )

            assert output_path == str(custom_output)
            assert custom_output.exists()

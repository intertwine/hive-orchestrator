#!/usr/bin/env python3
"""
Agent Hive Sandbox Runner - Local/Cloud Execution Without GitHub Actions

This module provides infrastructure for running YOLO loops in isolated
sandboxes, completely independent of GitHub Actions.

Supports:
- Docker containers (local isolation)
- Cloud sandbox providers (Cloudflare Workers, Modal, etc.)
- Standalone daemon mode for continuous operation
- Session persistence and recovery
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import signal
import atexit
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
import threading
import http.server
import socketserver
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class SandboxProvider(Enum):
    """Supported sandbox providers."""
    DOCKER = "docker"
    DOCKER_COMPOSE = "docker-compose"
    CLOUDFLARE = "cloudflare"
    MODAL = "modal"
    LOCAL = "local"  # No sandboxing, run directly


@dataclass
class SandboxConfig:
    """Configuration for sandbox execution."""
    provider: SandboxProvider = SandboxProvider.DOCKER

    # Docker settings
    docker_image: str = "docker/sandbox-templates:claude-code"
    docker_network: str = "none"  # Isolated by default
    docker_volumes: List[str] = field(default_factory=list)
    docker_env: Dict[str, str] = field(default_factory=dict)
    docker_memory_limit: str = "4g"
    docker_cpu_limit: float = 2.0

    # Credentials
    anthropic_api_key: Optional[str] = None
    github_token: Optional[str] = None

    # Persistence
    state_dir: str = ".yolo-state"
    persist_sessions: bool = True

    # Daemon settings
    daemon_mode: bool = False
    daemon_port: int = 8765
    poll_interval: int = 300  # 5 minutes


@dataclass
class SandboxSession:
    """A running sandbox session."""
    session_id: str
    provider: SandboxProvider
    container_id: Optional[str] = None
    process: Optional[subprocess.Popen] = None
    start_time: float = field(default_factory=time.time)
    status: str = "running"
    output_log: str = ""


class DockerSandbox:
    """
    Docker-based sandbox for running Claude Code in isolation.

    Provides complete isolation from the host system while
    allowing controlled access to project files.
    """

    def __init__(self, config: SandboxConfig):
        """Initialize Docker sandbox."""
        self.config = config
        self._validate_docker()

    def _validate_docker(self):
        """Validate Docker is available."""
        try:
            result = subprocess.run(
                ["docker", "version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                raise RuntimeError("Docker is not running")
        except FileNotFoundError:
            raise RuntimeError("Docker is not installed")

    def _build_docker_command(
        self,
        prompt: str,
        working_dir: Path,
        model: str = None,
    ) -> List[str]:
        """Build the Docker run command."""
        cmd = [
            "docker", "run",
            "--rm",
            f"--network={self.config.docker_network}",
            f"--memory={self.config.docker_memory_limit}",
            f"--cpus={self.config.docker_cpu_limit}",
            "-v", f"{working_dir}:/workspace",
            "-w", "/workspace",
        ]

        # Add API key
        api_key = self.config.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            cmd.extend(["-e", f"ANTHROPIC_API_KEY={api_key}"])

        # Add GitHub token if available
        gh_token = self.config.github_token or os.getenv("GITHUB_TOKEN")
        if gh_token:
            cmd.extend(["-e", f"GITHUB_TOKEN={gh_token}"])

        # Add custom environment variables
        for key, value in self.config.docker_env.items():
            cmd.extend(["-e", f"{key}={value}"])

        # Add custom volumes
        for volume in self.config.docker_volumes:
            cmd.extend(["-v", volume])

        # Add the image and command
        cmd.append(self.config.docker_image)
        cmd.extend([
            "claude",
            "--print",
            "--dangerously-skip-permissions",
            "-p", prompt,
        ])

        if model:
            cmd.extend(["--model", model])

        return cmd

    def run(
        self,
        prompt: str,
        working_dir: str,
        model: str = None,
        timeout: int = 3600,
    ) -> Dict[str, Any]:
        """
        Run a prompt in the Docker sandbox.

        Returns a dict with:
        - success: bool
        - output: str
        - exit_code: int
        - elapsed_seconds: float
        """
        working_dir = Path(working_dir).resolve()

        if not working_dir.exists():
            return {
                "success": False,
                "output": f"Working directory does not exist: {working_dir}",
                "exit_code": 1,
                "elapsed_seconds": 0,
            }

        cmd = self._build_docker_command(prompt, working_dir, model)

        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            elapsed = time.time() - start_time
            output = result.stdout + result.stderr

            return {
                "success": result.returncode == 0,
                "output": output,
                "exit_code": result.returncode,
                "elapsed_seconds": elapsed,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": f"Timeout after {timeout} seconds",
                "exit_code": -1,
                "elapsed_seconds": timeout,
            }
        except Exception as e:
            return {
                "success": False,
                "output": f"Error: {str(e)}",
                "exit_code": -1,
                "elapsed_seconds": time.time() - start_time,
            }

    def run_interactive(
        self,
        working_dir: str,
        model: str = None,
    ) -> subprocess.Popen:
        """
        Start an interactive Docker sandbox session.

        Returns the Popen process for the container.
        """
        working_dir = Path(working_dir).resolve()

        cmd = [
            "docker", "run",
            "-it",  # Interactive with TTY
            "--rm",
            f"--network={self.config.docker_network}",
            f"--memory={self.config.docker_memory_limit}",
            f"--cpus={self.config.docker_cpu_limit}",
            "-v", f"{working_dir}:/workspace",
            "-w", "/workspace",
        ]

        # Add credentials
        api_key = self.config.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            cmd.extend(["-e", f"ANTHROPIC_API_KEY={api_key}"])

        gh_token = self.config.github_token or os.getenv("GITHUB_TOKEN")
        if gh_token:
            cmd.extend(["-e", f"GITHUB_TOKEN={gh_token}"])

        cmd.append(self.config.docker_image)
        cmd.extend(["claude", "--dangerously-skip-permissions"])

        if model:
            cmd.extend(["--model", model])

        return subprocess.Popen(cmd)


class YoloDaemon:
    """
    Daemon process for continuous YOLO loop execution.

    Runs in the background, periodically checking for work
    and executing loops without human intervention.
    """

    def __init__(
        self,
        config: SandboxConfig,
        hive_path: str = None,
    ):
        """Initialize the YOLO daemon."""
        self.config = config
        self.hive_path = Path(hive_path or os.getcwd())
        self.state_dir = self.hive_path / config.state_dir
        self.running = False
        self._stop_event = threading.Event()

        # Create state directory
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # PID file for daemon management
        self.pid_file = self.state_dir / "daemon.pid"

        # Import here to avoid circular imports
        from src.yolo_loop import LoomWeaver, ExecutionBackend

        self.weaver = LoomWeaver(
            base_path=str(self.hive_path),
            max_parallel_agents=3,
            backend=ExecutionBackend.DOCKER if config.provider == SandboxProvider.DOCKER else ExecutionBackend.SUBPROCESS,
        )

    def _write_pid(self):
        """Write PID file for daemon management."""
        self.pid_file.write_text(str(os.getpid()))

    def _remove_pid(self):
        """Remove PID file on shutdown."""
        if self.pid_file.exists():
            self.pid_file.unlink()

    def _save_state(self, state: Dict[str, Any]):
        """Save daemon state to disk."""
        state_file = self.state_dir / "daemon_state.json"
        state["last_updated"] = datetime.now(timezone.utc).isoformat()
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)

    def _load_state(self) -> Dict[str, Any]:
        """Load daemon state from disk."""
        state_file = self.state_dir / "daemon_state.json"
        if state_file.exists():
            with open(state_file) as f:
                return json.load(f)
        return {}

    def _handle_signal(self, signum, frame):
        """Handle shutdown signals."""
        print(f"\nReceived signal {signum}. Shutting down...")
        self.stop()

    def start(self):
        """Start the daemon."""
        if self.running:
            print("Daemon is already running")
            return

        # Check for existing daemon
        if self.pid_file.exists():
            existing_pid = int(self.pid_file.read_text().strip())
            try:
                os.kill(existing_pid, 0)  # Check if process exists
                print(f"Daemon already running with PID {existing_pid}")
                return
            except OSError:
                # Process doesn't exist, remove stale PID file
                self._remove_pid()

        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

        # Write PID and register cleanup
        self._write_pid()
        atexit.register(self._remove_pid)

        self.running = True
        self._stop_event.clear()

        print(f"\n{'='*60}")
        print("YOLO DAEMON STARTED")
        print(f"{'='*60}")
        print(f"PID: {os.getpid()}")
        print(f"Hive Path: {self.hive_path}")
        print(f"Poll Interval: {self.config.poll_interval}s")
        print(f"State Dir: {self.state_dir}")
        print()

        self._run_loop()

    def stop(self):
        """Stop the daemon."""
        self.running = False
        self._stop_event.set()

    def _run_loop(self):
        """Main daemon loop."""
        state = self._load_state()
        state["start_time"] = datetime.now(timezone.utc).isoformat()
        state["runs"] = state.get("runs", 0)

        while self.running:
            try:
                # Check for ready work
                ready_projects = self.weaver.discover_ready_work()

                if ready_projects:
                    print(f"\n[{datetime.now().isoformat()}] Found {len(ready_projects)} projects ready")

                    # Run the weaver
                    results = self.weaver.weave(
                        max_iterations_per_loop=50,
                        total_timeout_seconds=self.config.poll_interval - 30,  # Leave buffer
                    )

                    state["runs"] += 1
                    state["last_run"] = datetime.now(timezone.utc).isoformat()
                    state["last_results"] = {
                        loop_id: s.to_dict() for loop_id, s in results.items()
                    }
                    self._save_state(state)

                else:
                    print(f"[{datetime.now().isoformat()}] No work available")

            except Exception as e:
                print(f"Error in daemon loop: {e}")
                state["last_error"] = str(e)
                self._save_state(state)

            # Wait for next poll interval or stop signal
            if self._stop_event.wait(timeout=self.config.poll_interval):
                break

        print("\nDaemon stopped")
        self._remove_pid()


class SandboxRunner:
    """
    High-level interface for sandbox execution.

    Provides easy-to-use methods for running YOLO loops
    in various sandbox environments.
    """

    def __init__(self, config: SandboxConfig = None):
        """Initialize the sandbox runner."""
        self.config = config or SandboxConfig()

    def run_docker(
        self,
        prompt: str,
        working_dir: str,
        model: str = None,
        timeout: int = 3600,
    ) -> Dict[str, Any]:
        """Run a prompt in Docker sandbox."""
        sandbox = DockerSandbox(self.config)
        return sandbox.run(prompt, working_dir, model, timeout)

    def run_interactive_docker(
        self,
        working_dir: str,
        model: str = None,
    ):
        """Start an interactive Docker sandbox session."""
        sandbox = DockerSandbox(self.config)
        process = sandbox.run_interactive(working_dir, model)
        process.wait()

    def start_daemon(self, hive_path: str = None):
        """Start the YOLO daemon for continuous operation."""
        daemon = YoloDaemon(self.config, hive_path)
        daemon.start()

    def stop_daemon(self, hive_path: str = None):
        """Stop a running YOLO daemon."""
        state_dir = Path(hive_path or os.getcwd()) / self.config.state_dir
        pid_file = state_dir / "daemon.pid"

        if not pid_file.exists():
            print("No daemon running (PID file not found)")
            return False

        pid = int(pid_file.read_text().strip())
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"Sent SIGTERM to daemon (PID {pid})")

            # Wait for process to exit
            for _ in range(10):
                time.sleep(1)
                try:
                    os.kill(pid, 0)
                except OSError:
                    print("Daemon stopped")
                    return True

            # Force kill if still running
            os.kill(pid, signal.SIGKILL)
            print("Daemon force killed")
            return True

        except OSError as e:
            print(f"Error stopping daemon: {e}")
            # Clean up stale PID file
            if pid_file.exists():
                pid_file.unlink()
            return False

    def daemon_status(self, hive_path: str = None) -> Dict[str, Any]:
        """Get status of the YOLO daemon."""
        state_dir = Path(hive_path or os.getcwd()) / self.config.state_dir
        pid_file = state_dir / "daemon.pid"
        state_file = state_dir / "daemon_state.json"

        status = {
            "running": False,
            "pid": None,
            "state": None,
        }

        if pid_file.exists():
            pid = int(pid_file.read_text().strip())
            try:
                os.kill(pid, 0)
                status["running"] = True
                status["pid"] = pid
            except OSError:
                pass

        if state_file.exists():
            with open(state_file) as f:
                status["state"] = json.load(f)

        return status


def generate_docker_compose(
    hive_path: str,
    output_path: str = None,
) -> str:
    """
    Generate a docker-compose.yml for running YOLO loops.

    This can be used to run loops on any machine with Docker Compose,
    including cloud VMs.
    """
    hive_path = Path(hive_path).resolve()
    output_path = Path(output_path or hive_path / "docker-compose.yolo.yml")

    compose_content = f"""version: '3.8'

# Agent Hive YOLO Loop Docker Compose Configuration
# Generated: {datetime.now(timezone.utc).isoformat()}
#
# Usage:
#   docker-compose -f docker-compose.yolo.yml up -d
#
# This runs YOLO loops on your Agent Hive projects in isolated containers.

services:
  yolo-daemon:
    image: docker/sandbox-templates:claude-code
    container_name: agent-hive-yolo
    restart: unless-stopped
    environment:
      - ANTHROPIC_API_KEY=${{ANTHROPIC_API_KEY}}
      - GITHUB_TOKEN=${{GITHUB_TOKEN:-}}
      - OPENROUTER_API_KEY=${{OPENROUTER_API_KEY:-}}
    volumes:
      - {hive_path}:/workspace
      - yolo-state:/workspace/.yolo-state
    working_dir: /workspace
    command: >
      sh -c "
        pip install -e . &&
        python -m src.sandbox_runner daemon --poll-interval 300
      "
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
    networks:
      - yolo-net

networks:
  yolo-net:
    driver: bridge

volumes:
  yolo-state:
    driver: local
"""

    output_path.write_text(compose_content)
    return str(output_path)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Agent Hive Sandbox Runner - Local/Cloud Execution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run a prompt in Docker sandbox
  uv run python -m src.sandbox_runner run --prompt "Fix all bugs"

  # Start interactive Docker session
  uv run python -m src.sandbox_runner interactive

  # Start the YOLO daemon for continuous operation
  uv run python -m src.sandbox_runner daemon

  # Check daemon status
  uv run python -m src.sandbox_runner status

  # Stop the daemon
  uv run python -m src.sandbox_runner stop

  # Generate docker-compose.yml for deployment
  uv run python -m src.sandbox_runner compose --output ./docker-compose.yolo.yml
        """,
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Run command
    run_parser = subparsers.add_parser("run", help="Run a prompt in sandbox")
    run_parser.add_argument("--prompt", "-p", required=True, help="Prompt to run")
    run_parser.add_argument("--path", default=".", help="Working directory")
    run_parser.add_argument("--model", "-m", help="Model to use")
    run_parser.add_argument("--timeout", "-t", type=int, default=3600, help="Timeout in seconds")
    run_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Interactive command
    interactive_parser = subparsers.add_parser("interactive", help="Start interactive sandbox")
    interactive_parser.add_argument("--path", default=".", help="Working directory")
    interactive_parser.add_argument("--model", "-m", help="Model to use")

    # Daemon command
    daemon_parser = subparsers.add_parser("daemon", help="Start YOLO daemon")
    daemon_parser.add_argument("--path", default=".", help="Hive path")
    daemon_parser.add_argument("--poll-interval", type=int, default=300, help="Poll interval in seconds")

    # Status command
    status_parser = subparsers.add_parser("status", help="Check daemon status")
    status_parser.add_argument("--path", default=".", help="Hive path")
    status_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop daemon")
    stop_parser.add_argument("--path", default=".", help="Hive path")

    # Compose command
    compose_parser = subparsers.add_parser("compose", help="Generate docker-compose.yml")
    compose_parser.add_argument("--path", default=".", help="Hive path")
    compose_parser.add_argument("--output", "-o", help="Output file path")

    return parser.parse_args()


def main():
    """CLI entry point for Sandbox Runner."""
    args = parse_args()

    config = SandboxConfig()
    runner = SandboxRunner(config)

    if args.command == "run":
        result = runner.run_docker(
            prompt=args.prompt,
            working_dir=args.path,
            model=args.model,
            timeout=args.timeout,
        )

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Success: {result['success']}")
            print(f"Exit Code: {result['exit_code']}")
            print(f"Elapsed: {result['elapsed_seconds']:.1f}s")
            print(f"\nOutput:\n{result['output']}")

    elif args.command == "interactive":
        runner.run_interactive_docker(
            working_dir=args.path,
            model=args.model,
        )

    elif args.command == "daemon":
        config.poll_interval = args.poll_interval
        runner.start_daemon(hive_path=args.path)

    elif args.command == "status":
        status = runner.daemon_status(hive_path=args.path)

        if args.json:
            print(json.dumps(status, indent=2))
        else:
            if status["running"]:
                print(f"Daemon is RUNNING (PID: {status['pid']})")
            else:
                print("Daemon is NOT RUNNING")

            if status["state"]:
                state = status["state"]
                print(f"\nLast updated: {state.get('last_updated', 'N/A')}")
                print(f"Total runs: {state.get('runs', 0)}")
                print(f"Last run: {state.get('last_run', 'N/A')}")

    elif args.command == "stop":
        runner.stop_daemon(hive_path=args.path)

    elif args.command == "compose":
        output_path = generate_docker_compose(
            hive_path=args.path,
            output_path=args.output,
        )
        print(f"Generated docker-compose file: {output_path}")
        print("\nTo run:")
        print(f"  docker-compose -f {output_path} up -d")


if __name__ == "__main__":
    main()

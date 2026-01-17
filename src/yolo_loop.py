#!/usr/bin/env python3
"""
Agent Hive YOLO Loop - Autonomous Agent Loop Orchestration

This module implements Ralph Wiggum-style infinite agentic loops
and Loom-style parallel agent weaving for Agent Hive.

Inspired by:
- Ralph Wiggum technique (Geoffrey Huntley): Persistent iteration loops
- Loom pattern: Parallel agent orchestration with weaving
- Claude Code YOLO mode: Unattended autonomous execution

Key Features:
- Multiple execution backends (subprocess, Docker sandbox, cloud)
- Safety mechanisms (max iterations, timeouts, circuit breakers)
- Parallel agent weaving (Loom-style)
- Integration with Agent Hive Cortex for work discovery
- State persistence via AGENCY.md files
"""

import argparse
import json
import os
import subprocess
import sys
import signal
import time
import threading
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from dotenv import load_dotenv

from src.cortex import Cortex
from src.security import (
    safe_load_agency_md,
    safe_dump_agency_md,
    validate_path_within_base,
)

# Load environment variables
load_dotenv()


class LoopStatus(Enum):
    """Status of a YOLO loop."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    CIRCUIT_BREAK = "circuit_break"


class ExecutionBackend(Enum):
    """Execution backends for running agents."""
    SUBPROCESS = "subprocess"  # Local subprocess with Claude Code CLI
    DOCKER = "docker"  # Docker sandbox isolation
    CLOUD_SANDBOX = "cloud_sandbox"  # Cloud provider sandbox (future)


@dataclass
class LoopConfig:
    """Configuration for a YOLO loop."""
    # Core settings
    prompt: str
    max_iterations: int = 50
    timeout_seconds: int = 3600  # 1 hour default

    # Agent settings
    model: str = "claude-sonnet-4-20250514"
    backend: ExecutionBackend = ExecutionBackend.SUBPROCESS

    # Safety settings
    circuit_breaker_threshold: int = 5  # Consecutive failures before break
    rate_limit_per_hour: int = 100  # Max API calls per hour
    cooldown_seconds: int = 5  # Pause between iterations

    # Completion detection
    completion_markers: List[str] = field(default_factory=lambda: [
        "LOOP_COMPLETE",
        "ALL_TASKS_DONE",
        "EXIT_SIGNAL",
    ])

    # Working directory
    working_dir: Optional[str] = None

    # Docker settings (if using Docker backend)
    docker_image: str = "docker/sandbox-templates:claude-code"
    docker_network: str = "none"  # Isolated by default

    # Hive integration
    project_id: Optional[str] = None  # If running for a specific project
    auto_claim: bool = True  # Auto-claim projects from Cortex


@dataclass
class LoopState:
    """State tracking for a running loop."""
    loop_id: str
    config: LoopConfig
    status: LoopStatus = LoopStatus.PENDING
    current_iteration: int = 0
    consecutive_failures: int = 0
    api_calls_this_hour: int = 0
    hour_started: float = field(default_factory=time.time)
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    last_output: str = ""
    error_log: List[str] = field(default_factory=list)
    iteration_history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for serialization."""
        return {
            "loop_id": self.loop_id,
            "status": self.status.value,
            "current_iteration": self.current_iteration,
            "max_iterations": self.config.max_iterations,
            "consecutive_failures": self.consecutive_failures,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "elapsed_seconds": (
                (self.end_time or time.time()) - self.start_time
                if self.start_time else 0
            ),
            "last_output_preview": self.last_output[:500] if self.last_output else "",
            "error_count": len(self.error_log),
        }


class YoloLoop:
    """
    YOLO Loop - Ralph Wiggum style autonomous agent loop.

    Implements persistent iteration where an agent works on a task
    until completion or safety limits are reached.
    """

    def __init__(self, config: LoopConfig):
        """Initialize a YOLO loop with configuration."""
        self.config = config
        self.loop_id = self._generate_loop_id()
        self.state = LoopState(loop_id=self.loop_id, config=config)
        self._stop_requested = False
        self._lock = threading.Lock()

        # Set up working directory
        self.working_dir = Path(config.working_dir or os.getcwd())

        # Cortex integration for Hive projects
        self.cortex = Cortex(str(self.working_dir))

    def _generate_loop_id(self) -> str:
        """Generate a unique loop ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        hash_input = f"{timestamp}-{self.config.prompt[:50]}"
        short_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:8]
        return f"yolo-{timestamp}-{short_hash}"

    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        current_time = time.time()

        # Reset hourly counter if hour has passed
        if current_time - self.state.hour_started > 3600:
            self.state.api_calls_this_hour = 0
            self.state.hour_started = current_time

        if self.state.api_calls_this_hour >= self.config.rate_limit_per_hour:
            wait_time = 3600 - (current_time - self.state.hour_started)
            print(f"Rate limit reached. Waiting {wait_time:.0f}s until next hour.")
            return False

        return True

    def _check_circuit_breaker(self) -> bool:
        """Check if circuit breaker is triggered."""
        if self.state.consecutive_failures >= self.config.circuit_breaker_threshold:
            print(f"Circuit breaker triggered after {self.state.consecutive_failures} consecutive failures.")
            return False
        return True

    def _check_completion(self, output: str) -> bool:
        """Check if output indicates task completion."""
        output_upper = output.upper()
        for marker in self.config.completion_markers:
            if marker.upper() in output_upper:
                print(f"Completion marker detected: {marker}")
                return True
        return False

    def _build_iteration_prompt(self, iteration: int) -> str:
        """Build the prompt for a single iteration."""
        base_prompt = self.config.prompt

        # Add iteration context
        iteration_context = f"""
## YOLO Loop Context
- Loop ID: {self.loop_id}
- Iteration: {iteration} of {self.config.max_iterations}
- Status: Running autonomously

## Important Instructions
- Work on the task below until complete
- If you finish ALL tasks, output: LOOP_COMPLETE
- If you get stuck and need human help, output: BLOCKED
- State persists between iterations via files

## Task
{base_prompt}
"""
        return iteration_context

    def _execute_subprocess(self, prompt: str) -> Tuple[bool, str]:
        """Execute an iteration using subprocess (Claude Code CLI)."""
        try:
            # Build Claude Code command
            cmd = [
                "claude",
                "--print",  # Non-interactive mode
                "--dangerously-skip-permissions",  # YOLO mode
                "-p", prompt,
            ]

            # Add model if specified
            if self.config.model:
                cmd.extend(["--model", self.config.model])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.timeout_seconds,
                cwd=str(self.working_dir),
            )

            output = result.stdout + result.stderr
            success = result.returncode == 0

            return success, output

        except subprocess.TimeoutExpired:
            return False, "ERROR: Iteration timeout exceeded"
        except FileNotFoundError:
            return False, "ERROR: claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code"
        except Exception as e:
            return False, f"ERROR: {str(e)}"

    def _execute_docker(self, prompt: str) -> Tuple[bool, str]:
        """Execute an iteration using Docker sandbox."""
        try:
            # Create a temporary prompt file
            prompt_file = self.working_dir / f".yolo-prompt-{self.loop_id}.txt"
            prompt_file.write_text(prompt)

            # Build Docker command
            cmd = [
                "docker", "run",
                "--rm",
                f"--network={self.config.docker_network}",
                "-v", f"{self.working_dir}:/workspace",
                "-w", "/workspace",
                "-e", f"ANTHROPIC_API_KEY={os.getenv('ANTHROPIC_API_KEY', '')}",
                self.config.docker_image,
                "claude",
                "--print",
                "--dangerously-skip-permissions",
                "-p", prompt,
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.timeout_seconds,
            )

            # Clean up prompt file
            if prompt_file.exists():
                prompt_file.unlink()

            output = result.stdout + result.stderr
            success = result.returncode == 0

            return success, output

        except subprocess.TimeoutExpired:
            return False, "ERROR: Docker container timeout exceeded"
        except Exception as e:
            return False, f"ERROR: {str(e)}"

    def _execute_iteration(self, prompt: str) -> Tuple[bool, str]:
        """Execute a single iteration using the configured backend."""
        backend = self.config.backend

        if backend == ExecutionBackend.SUBPROCESS:
            return self._execute_subprocess(prompt)
        elif backend == ExecutionBackend.DOCKER:
            return self._execute_docker(prompt)
        elif backend == ExecutionBackend.CLOUD_SANDBOX:
            # Future: implement cloud sandbox
            return False, "ERROR: Cloud sandbox not yet implemented"
        else:
            return False, f"ERROR: Unknown backend: {backend}"

    def stop(self):
        """Request the loop to stop gracefully."""
        with self._lock:
            self._stop_requested = True
            print(f"Stop requested for loop {self.loop_id}")

    def run(self) -> LoopState:
        """
        Run the YOLO loop until completion or limits reached.

        Returns the final loop state.
        """
        self.state.status = LoopStatus.RUNNING
        self.state.start_time = time.time()

        print(f"\n{'='*60}")
        print(f"YOLO LOOP STARTED: {self.loop_id}")
        print(f"{'='*60}")
        print(f"Max iterations: {self.config.max_iterations}")
        print(f"Timeout: {self.config.timeout_seconds}s")
        print(f"Backend: {self.config.backend.value}")
        print(f"Working dir: {self.working_dir}")
        print()

        try:
            for iteration in range(1, self.config.max_iterations + 1):
                # Check for stop request
                with self._lock:
                    if self._stop_requested:
                        self.state.status = LoopStatus.CANCELLED
                        print("Loop cancelled by user request.")
                        break

                # Check safety limits
                if not self._check_rate_limit():
                    time.sleep(60)  # Wait a minute and retry
                    continue

                if not self._check_circuit_breaker():
                    self.state.status = LoopStatus.CIRCUIT_BREAK
                    break

                # Check timeout
                elapsed = time.time() - self.state.start_time
                if elapsed > self.config.timeout_seconds:
                    self.state.status = LoopStatus.TIMEOUT
                    print(f"Loop timeout after {elapsed:.0f}s")
                    break

                self.state.current_iteration = iteration
                print(f"\n--- Iteration {iteration}/{self.config.max_iterations} ---")

                # Build and execute iteration
                prompt = self._build_iteration_prompt(iteration)
                success, output = self._execute_iteration(prompt)

                self.state.api_calls_this_hour += 1
                self.state.last_output = output

                # Record iteration history
                self.state.iteration_history.append({
                    "iteration": iteration,
                    "success": success,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "output_preview": output[:500] if output else "",
                })

                if success:
                    self.state.consecutive_failures = 0
                    print(f"Iteration {iteration} succeeded.")

                    # Check for completion
                    if self._check_completion(output):
                        self.state.status = LoopStatus.COMPLETED
                        print("Task completed successfully!")
                        break
                else:
                    self.state.consecutive_failures += 1
                    self.state.error_log.append(f"Iteration {iteration}: {output[:200]}")
                    print(f"Iteration {iteration} failed. Consecutive failures: {self.state.consecutive_failures}")

                # Cooldown between iterations
                if iteration < self.config.max_iterations:
                    time.sleep(self.config.cooldown_seconds)

            else:
                # Reached max iterations without completion
                if self.state.status == LoopStatus.RUNNING:
                    self.state.status = LoopStatus.FAILED
                    print(f"Max iterations ({self.config.max_iterations}) reached without completion.")

        except KeyboardInterrupt:
            self.state.status = LoopStatus.CANCELLED
            print("\nLoop interrupted by user (Ctrl+C)")

        except Exception as e:
            self.state.status = LoopStatus.FAILED
            self.state.error_log.append(f"Fatal error: {str(e)}")
            print(f"Fatal error: {e}")

        finally:
            self.state.end_time = time.time()
            elapsed = self.state.end_time - self.state.start_time

            print(f"\n{'='*60}")
            print(f"YOLO LOOP ENDED: {self.loop_id}")
            print(f"{'='*60}")
            print(f"Status: {self.state.status.value}")
            print(f"Iterations: {self.state.current_iteration}")
            print(f"Elapsed: {elapsed:.1f}s")
            print()

        return self.state


class LoomWeaver:
    """
    Loom-style parallel agent orchestration.

    Weaves multiple YOLO loops together, running them in parallel
    with coordination through shared state (AGENCY.md files).
    """

    def __init__(
        self,
        base_path: str = None,
        max_parallel_agents: int = 3,
        backend: ExecutionBackend = ExecutionBackend.SUBPROCESS,
    ):
        """Initialize the Loom Weaver."""
        self.base_path = Path(base_path or os.getcwd())
        self.max_parallel_agents = max_parallel_agents
        self.backend = backend
        self.cortex = Cortex(str(self.base_path))
        self.active_loops: Dict[str, YoloLoop] = {}
        self._lock = threading.Lock()

    def discover_ready_work(self) -> List[Dict[str, Any]]:
        """Discover projects ready for work using Cortex."""
        return self.cortex.ready_work()

    def create_loop_for_project(
        self,
        project: Dict[str, Any],
        max_iterations: int = 50,
    ) -> YoloLoop:
        """Create a YOLO loop for a specific project."""
        metadata = project.get("metadata", {})
        project_id = metadata.get("project_id", "unknown")
        content = project.get("content", "")

        # Build prompt from project content
        prompt = f"""
# Project: {project_id}

## Priority: {metadata.get('priority', 'medium')}
## Tags: {', '.join(metadata.get('tags', []))}

## Project Content
{content}

## Instructions
1. Read the AGENCY.md file at: {project['path']}
2. Work on the incomplete tasks
3. Update the AGENCY.md file with your progress
4. Add notes to the Agent Notes section
5. When ALL tasks are complete, output: LOOP_COMPLETE
"""

        config = LoopConfig(
            prompt=prompt,
            max_iterations=max_iterations,
            backend=self.backend,
            project_id=project_id,
            working_dir=str(self.base_path),
        )

        return YoloLoop(config)

    def claim_project(self, project: Dict[str, Any], loop_id: str) -> bool:
        """Claim a project by setting owner in AGENCY.md."""
        try:
            project_path = Path(project["path"])
            parsed = safe_load_agency_md(project_path)

            # Check if already claimed
            if parsed.metadata.get("owner"):
                return False

            # Claim it
            parsed.metadata["owner"] = f"yolo-loop:{loop_id}"
            parsed.metadata["last_updated"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            # Add agent note
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
            note = f"\n- **{timestamp} - YOLO Loop**: Started autonomous loop {loop_id}"

            content = parsed.content
            if "## Agent Notes" in content:
                content = content.replace("## Agent Notes", f"## Agent Notes{note}", 1)
            else:
                content += f"\n\n## Agent Notes{note}"

            with open(project_path, "w", encoding="utf-8") as f:
                f.write(safe_dump_agency_md(parsed.metadata, content))

            return True

        except Exception as e:
            print(f"Error claiming project: {e}")
            return False

    def release_project(self, project: Dict[str, Any], loop_id: str, status: LoopStatus) -> bool:
        """Release a project after loop completion."""
        try:
            project_path = Path(project["path"])
            parsed = safe_load_agency_md(project_path)

            # Release ownership
            parsed.metadata["owner"] = None
            parsed.metadata["last_updated"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            # Update status if completed
            if status == LoopStatus.COMPLETED:
                parsed.metadata["status"] = "completed"
            elif status in (LoopStatus.FAILED, LoopStatus.CIRCUIT_BREAK):
                parsed.metadata["blocked"] = True
                parsed.metadata["blocking_reason"] = f"YOLO loop {loop_id} ended with status: {status.value}"

            # Add agent note
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
            note = f"\n- **{timestamp} - YOLO Loop**: Loop {loop_id} ended with status: {status.value}"

            content = parsed.content
            if "## Agent Notes" in content:
                content = content.replace("## Agent Notes", f"## Agent Notes{note}", 1)
            else:
                content += f"\n\n## Agent Notes{note}"

            with open(project_path, "w", encoding="utf-8") as f:
                f.write(safe_dump_agency_md(parsed.metadata, content))

            return True

        except Exception as e:
            print(f"Error releasing project: {e}")
            return False

    def weave(
        self,
        max_iterations_per_loop: int = 50,
        total_timeout_seconds: int = 14400,  # 4 hours
    ) -> Dict[str, LoopState]:
        """
        Weave multiple YOLO loops in parallel.

        Discovers ready work, claims projects, runs loops in parallel,
        and coordinates through AGENCY.md state.

        Returns a dictionary of loop_id -> final state.
        """
        print(f"\n{'='*60}")
        print("LOOM WEAVER STARTING")
        print(f"{'='*60}")
        print(f"Max parallel agents: {self.max_parallel_agents}")
        print(f"Backend: {self.backend.value}")
        print()

        start_time = time.time()
        results: Dict[str, LoopState] = {}

        # Discover initial work
        ready_projects = self.discover_ready_work()
        print(f"Found {len(ready_projects)} projects ready for work")

        if not ready_projects:
            print("No work available. Exiting.")
            return results

        def run_loop(project: Dict[str, Any]) -> Optional[Tuple[str, LoopState]]:
            """Run a single loop for a project."""
            loop = self.create_loop_for_project(project, max_iterations_per_loop)

            # Claim the project
            if not self.claim_project(project, loop.loop_id):
                print(f"Could not claim project {project.get('project_id')}. Skipping.")
                return None

            with self._lock:
                self.active_loops[loop.loop_id] = loop

            try:
                state = loop.run()
                return (loop.loop_id, state)
            finally:
                with self._lock:
                    if loop.loop_id in self.active_loops:
                        del self.active_loops[loop.loop_id]

                # Release the project
                self.release_project(project, loop.loop_id, state.status if state else LoopStatus.FAILED)

        # Run loops in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=self.max_parallel_agents) as executor:
            # Submit initial batch of work
            futures = {}
            for project in ready_projects[:self.max_parallel_agents]:
                future = executor.submit(run_loop, project)
                futures[future] = project

            project_queue = list(ready_projects[self.max_parallel_agents:])

            while futures:
                # Check total timeout
                if time.time() - start_time > total_timeout_seconds:
                    print(f"Total timeout ({total_timeout_seconds}s) reached. Stopping all loops.")
                    # Cancel remaining work
                    for loop in self.active_loops.values():
                        loop.stop()
                    break

                # Wait for any loop to complete
                done_futures = []
                for future in list(futures.keys()):
                    if future.done():
                        done_futures.append(future)

                for future in done_futures:
                    project = futures.pop(future)
                    try:
                        result = future.result()
                        if result:
                            loop_id, state = result
                            results[loop_id] = state
                    except Exception as e:
                        print(f"Loop failed with error: {e}")

                    # Submit next project if available
                    if project_queue:
                        next_project = project_queue.pop(0)
                        new_future = executor.submit(run_loop, next_project)
                        futures[new_future] = next_project

                if futures:
                    time.sleep(1)  # Brief pause before checking again

        elapsed = time.time() - start_time

        print(f"\n{'='*60}")
        print("LOOM WEAVER COMPLETED")
        print(f"{'='*60}")
        print(f"Total loops run: {len(results)}")
        print(f"Elapsed: {elapsed:.1f}s")

        # Summary
        status_counts = {}
        for state in results.values():
            status = state.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        print("Status summary:")
        for status, count in status_counts.items():
            print(f"  {status}: {count}")

        return results


class YoloRunner:
    """
    High-level runner for YOLO loops.

    Provides a simple interface for running YOLO loops
    from CLI or programmatically.
    """

    @staticmethod
    def run_single(
        prompt: str,
        max_iterations: int = 50,
        timeout_seconds: int = 3600,
        backend: str = "subprocess",
        model: str = None,
        working_dir: str = None,
    ) -> LoopState:
        """Run a single YOLO loop."""
        config = LoopConfig(
            prompt=prompt,
            max_iterations=max_iterations,
            timeout_seconds=timeout_seconds,
            backend=ExecutionBackend(backend),
            model=model or "claude-sonnet-4-20250514",
            working_dir=working_dir,
        )

        loop = YoloLoop(config)
        return loop.run()

    @staticmethod
    def run_hive(
        base_path: str = None,
        max_parallel: int = 3,
        max_iterations_per_loop: int = 50,
        total_timeout: int = 14400,
        backend: str = "subprocess",
    ) -> Dict[str, LoopState]:
        """Run YOLO loops on all ready Hive projects."""
        weaver = LoomWeaver(
            base_path=base_path,
            max_parallel_agents=max_parallel,
            backend=ExecutionBackend(backend),
        )

        return weaver.weave(
            max_iterations_per_loop=max_iterations_per_loop,
            total_timeout_seconds=total_timeout,
        )

    @staticmethod
    def run_project(
        project_path: str,
        max_iterations: int = 50,
        timeout_seconds: int = 3600,
        backend: str = "subprocess",
    ) -> LoopState:
        """Run a YOLO loop on a specific project."""
        project_path = Path(project_path)

        if not project_path.exists():
            raise FileNotFoundError(f"Project not found: {project_path}")

        # Load the project
        parsed = safe_load_agency_md(project_path)

        project = {
            "path": str(project_path),
            "project_id": parsed.metadata.get("project_id", "unknown"),
            "metadata": parsed.metadata,
            "content": parsed.content,
        }

        base_path = project_path.parent.parent  # Assume projects/<name>/AGENCY.md

        weaver = LoomWeaver(
            base_path=str(base_path),
            max_parallel_agents=1,
            backend=ExecutionBackend(backend),
        )

        loop = weaver.create_loop_for_project(project, max_iterations)
        loop.config.timeout_seconds = timeout_seconds

        # Claim, run, release
        weaver.claim_project(project, loop.loop_id)
        try:
            state = loop.run()
        finally:
            weaver.release_project(project, loop.loop_id, state.status if state else LoopStatus.FAILED)

        return state


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Agent Hive YOLO Loop - Autonomous Agent Loop Orchestration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run a single YOLO loop with a prompt
  uv run python -m src.yolo_loop --prompt "Fix all TypeScript errors in src/"

  # Run on all ready Hive projects (Loom mode)
  uv run python -m src.yolo_loop --hive

  # Run on a specific project
  uv run python -m src.yolo_loop --project projects/my-project/AGENCY.md

  # Use Docker sandbox for isolation
  uv run python -m src.yolo_loop --prompt "Build feature X" --backend docker

  # Limit iterations and run in parallel
  uv run python -m src.yolo_loop --hive --max-iterations 20 --parallel 5
        """,
    )

    # Mode selection
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--prompt", "-p",
        type=str,
        help="Run a single YOLO loop with the given prompt",
    )
    mode_group.add_argument(
        "--hive",
        action="store_true",
        help="Run YOLO loops on all ready Hive projects (Loom mode)",
    )
    mode_group.add_argument(
        "--project",
        type=str,
        help="Run a YOLO loop on a specific project AGENCY.md file",
    )

    # Common options
    parser.add_argument(
        "--max-iterations", "-i",
        type=int,
        default=50,
        help="Maximum iterations per loop (default: 50)",
    )
    parser.add_argument(
        "--timeout", "-t",
        type=int,
        default=3600,
        help="Timeout per loop in seconds (default: 3600 = 1 hour)",
    )
    parser.add_argument(
        "--backend", "-b",
        type=str,
        choices=["subprocess", "docker"],
        default="subprocess",
        help="Execution backend (default: subprocess)",
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        default=None,
        help="Model to use (default: claude-sonnet-4-20250514)",
    )

    # Loom/parallel options
    parser.add_argument(
        "--parallel",
        type=int,
        default=3,
        help="Max parallel agents for --hive mode (default: 3)",
    )
    parser.add_argument(
        "--total-timeout",
        type=int,
        default=14400,
        help="Total timeout for --hive mode in seconds (default: 14400 = 4 hours)",
    )

    # Path options
    parser.add_argument(
        "--path",
        type=str,
        default=None,
        help="Base path for hive operations (default: current directory)",
    )

    # Output options
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    return parser.parse_args()


def main():
    """CLI entry point for YOLO Loop."""
    args = parse_args()

    try:
        if args.prompt:
            # Single loop mode
            state = YoloRunner.run_single(
                prompt=args.prompt,
                max_iterations=args.max_iterations,
                timeout_seconds=args.timeout,
                backend=args.backend,
                model=args.model,
                working_dir=args.path,
            )

            if args.json:
                print(json.dumps(state.to_dict(), indent=2))
            else:
                print(f"\nFinal Status: {state.status.value}")
                print(f"Iterations: {state.current_iteration}")

        elif args.hive:
            # Loom mode - all ready projects
            results = YoloRunner.run_hive(
                base_path=args.path,
                max_parallel=args.parallel,
                max_iterations_per_loop=args.max_iterations,
                total_timeout=args.total_timeout,
                backend=args.backend,
            )

            if args.json:
                output = {loop_id: state.to_dict() for loop_id, state in results.items()}
                print(json.dumps(output, indent=2))
            else:
                print(f"\nTotal loops: {len(results)}")

        elif args.project:
            # Single project mode
            state = YoloRunner.run_project(
                project_path=args.project,
                max_iterations=args.max_iterations,
                timeout_seconds=args.timeout,
                backend=args.backend,
            )

            if args.json:
                print(json.dumps(state.to_dict(), indent=2))
            else:
                print(f"\nFinal Status: {state.status.value}")
                print(f"Iterations: {state.current_iteration}")

        sys.exit(0)

    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

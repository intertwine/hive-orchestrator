"""Pi worker-session integration scaffolding for the v2.4 release line."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator

from src.hive.clock import utc_now_iso
from src.hive.drivers.types import RunLaunchRequest, SteeringRequest
from src.hive.ids import new_id
from src.hive.integrations.base import WorkerSessionAdapter
from src.hive.integrations.models import (
    AdapterFamily,
    GovernanceMode,
    IntegrationInfo,
    IntegrationLevel,
    SessionHandle,
)
from src.hive.integrations.pi_managed import build_pi_runner_command
from src.hive.runtime.capabilities import CapabilitySnapshot, capability_surface
from src.hive.trajectory.schema import trajectory_event
from src.hive.trajectory.writer import append_trajectory_event, trajectory_file

_ENV_PACKAGE_PATH = "HIVE_PI_PACKAGE_PATH"
_SOURCE_ROOT = Path(__file__).resolve().parents[3]


def _run_text_command(command: list[str]) -> str | None:
    """Run a tiny local command and return trimmed stdout on success."""
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=2,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    stdout = completed.stdout.strip()
    return stdout or None


def _read_package_manifest(package_dir: Path) -> dict[str, Any]:
    """Read a local package manifest, returning an empty dict on failure."""
    manifest_path = package_dir / "package.json"
    if not manifest_path.exists():
        return {}
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _find_global_npm_package(npm_path: str | None) -> Path | None:
    """Return the global npm package directory when it exists locally."""
    if npm_path is None:
        return None
    global_root = _run_text_command([npm_path, "root", "-g"])
    if not global_root:
        return None
    candidate = Path(global_root) / "@mellona" / "pi-hive"
    return candidate if (candidate / "package.json").exists() else None


@dataclass
class PiEnvironment:
    """Observed local Pi companion environment for doctor/setup flows."""

    workspace_root: Path
    node_path: str | None = None
    npm_path: str | None = None
    node_version: str | None = None
    npm_version: str | None = None
    package_dir: Path | None = None
    package_version: str | None = None
    cli_path: Path | None = None
    runner_path: Path | None = None
    configuration_problems: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)

    @property
    def install_path(self) -> str | None:
        return str(self.package_dir) if self.package_dir is not None else None

    @property
    def supported_levels(self) -> list[IntegrationLevel]:
        levels = [IntegrationLevel.PACK]
        if self.package_dir is not None and self.cli_path is not None:
            levels.extend([IntegrationLevel.COMPANION, IntegrationLevel.ATTACH])
        if self.runner_path is not None:
            levels.append(IntegrationLevel.MANAGED)
        return levels

    @property
    def supported_governance_modes(self) -> list[GovernanceMode]:
        modes: list[GovernanceMode] = []
        if IntegrationLevel.ATTACH in self.supported_levels:
            modes.append(GovernanceMode.ADVISORY)
        if IntegrationLevel.MANAGED in self.supported_levels:
            modes.append(GovernanceMode.GOVERNED)
        return modes

    @property
    def effective_level(self) -> IntegrationLevel:
        levels = self.supported_levels
        return levels[-1] if levels else IntegrationLevel.PACK

    @property
    def effective_governance(self) -> GovernanceMode:
        modes = self.supported_governance_modes
        return modes[-1] if modes else GovernanceMode.ADVISORY

    @property
    def available(self) -> bool:
        return (
            self.node_path is not None
            and self.npm_path is not None
            and self.package_dir is not None
            and self.cli_path is not None
        )

    def ensure_defaults(self) -> PiEnvironment:
        """Populate configuration problems and next steps from the observed state."""
        if self.node_path is None:
            message = "Node.js is not installed or not on PATH."
            if message not in self.configuration_problems:
                self.configuration_problems.append(message)
        if self.npm_path is None:
            message = "npm is not installed or not on PATH."
            if message not in self.configuration_problems:
                self.configuration_problems.append(message)
        if self.package_dir is None:
            message = "The @mellona/pi-hive companion package is not installed or vendored here."
            if message not in self.configuration_problems:
                self.configuration_problems.append(message)
        if self.package_dir is not None and self.cli_path is None:
            message = "The Pi companion package is missing the pi-hive CLI entrypoint."
            if message not in self.configuration_problems:
                self.configuration_problems.append(message)
        if self.package_dir is not None and self.runner_path is None:
            message = "The Pi companion package is missing the pi-hive-runner entrypoint."
            if message not in self.configuration_problems:
                self.configuration_problems.append(message)

        if not self.next_steps:
            if self.node_path is None or self.npm_path is None:
                self.next_steps.append("Install Node.js 20+ with npm on this machine.")
            if self.package_dir is None:
                self.next_steps.append(
                    "Install the companion with `npm install -g @mellona/pi-hive`, or use the vendored package in `packages/pi-hive/`."
                )
            elif self.runner_path is None:
                self.next_steps.append(
                    "Update the Pi companion package to a build that includes `pi-hive-runner`."
                )
            else:
                self.next_steps.extend(
                    [
                        "Run `hive integrate pi` in the workspace to verify setup and supported levels.",
                        "Use `pi-hive connect` from Pi to confirm the workspace handshake before live attach.",
                    ]
                )
        return self


def detect_pi_environment(workspace_root: Path | None = None) -> PiEnvironment:
    """Inspect the local machine and checkout for Pi companion availability."""
    root = Path(workspace_root or Path.cwd()).resolve()
    node_path = shutil.which("node")
    npm_path = shutil.which("npm")
    node_version = _run_text_command([node_path, "--version"]) if node_path else None
    npm_version = _run_text_command([npm_path, "--version"]) if npm_path else None

    package_dir: Path | None = None
    override = os.environ.get(_ENV_PACKAGE_PATH)
    candidates = [
        Path(override).expanduser() if override else None,
        root / "packages" / "pi-hive",
        _SOURCE_ROOT / "packages" / "pi-hive",
        _find_global_npm_package(npm_path),
    ]
    for candidate in candidates:
        if candidate is None:
            continue
        if (candidate / "package.json").exists():
            package_dir = candidate.resolve()
            break

    manifest = _read_package_manifest(package_dir) if package_dir else {}
    cli_path = package_dir / "bin" / "pi-hive.js" if package_dir else None
    if cli_path is not None and not cli_path.exists():
        cli_path = None
    runner_path = package_dir / "bin" / "pi-hive-runner.js" if package_dir else None
    if runner_path is not None and not runner_path.exists():
        runner_path = None

    environment = PiEnvironment(
        workspace_root=root,
        node_path=node_path,
        npm_path=npm_path,
        node_version=node_version,
        npm_version=npm_version,
        package_dir=package_dir,
        package_version=str(manifest.get("version", "0.0.0")),
        cli_path=cli_path,
        runner_path=runner_path,
    )

    return environment.ensure_defaults()


class PiWorkerAdapter(WorkerSessionAdapter):
    """Bundled Pi integration with truthful doctor/setup scaffolding."""

    name = "pi"
    adapter_family = AdapterFamily.WORKER_SESSION

    def __init__(
        self,
        workspace_root: Path | None = None,
        detector: Callable[[Path | None], PiEnvironment] | None = None,
    ) -> None:
        self.workspace_root = Path(workspace_root).resolve() if workspace_root else None
        self._detector = detector or detect_pi_environment
        self._sessions: dict[str, SessionHandle] = {}
        self._steers: list[dict[str, Any]] = []
        self._events: dict[str, list[dict[str, Any]]] = {}
        self._streamed_sessions: set[str] = set()

    def _environment(self, workspace_root: Path | None = None) -> PiEnvironment:
        return self._detector(workspace_root or self.workspace_root).ensure_defaults()

    def probe(self) -> IntegrationInfo:
        env = self._environment()
        notes = []
        if env.install_path:
            notes.append(f"Pi companion detected at {env.install_path}.")
        else:
            notes.append("Pi companion package not detected yet.")

        version = env.package_version or "0.0.0"
        snapshot = CapabilitySnapshot(
            driver=self.name,
            driver_version=version,
            declared=capability_surface(
                launch_mode="sdk",
                session_persistence="session",
                event_stream="structured_deltas",
                attach_supported=True,
                managed_supported=True,
                steering="queued",
                approvals=["hive-mediated"],
                artifacts=["trajectory", "session-history", "logs"],
                native_sandbox="pi",
                context_projection="filesystem",
                outer_sandbox_owned_by_hive=False,
            ),
            probed={
                "node_path": env.node_path,
                "node_version": env.node_version,
                "npm_path": env.npm_path,
                "npm_version": env.npm_version,
                "install_path": env.install_path,
                "cli_path": str(env.cli_path) if env.cli_path is not None else None,
                "runner_path": str(env.runner_path) if env.runner_path is not None else None,
                "workspace_root": str(env.workspace_root),
                "supported_levels": [str(level) for level in env.supported_levels],
            },
            effective=capability_surface(
                launch_mode="sdk" if env.package_dir is not None else "none",
                session_persistence="session" if env.package_dir is not None else "none",
                event_stream="structured_deltas" if env.package_dir is not None else "none",
                attach_supported=IntegrationLevel.ATTACH in env.supported_levels,
                managed_supported=IntegrationLevel.MANAGED in env.supported_levels,
                steering="queued" if env.package_dir is not None else "none",
                approvals=["hive-mediated"] if env.runner_path is not None else [],
                artifacts=["trajectory", "session-history", "logs"]
                if env.package_dir is not None
                else [],
                native_sandbox="pi" if env.package_dir is not None else "none",
                context_projection="filesystem" if env.package_dir is not None else "none",
                outer_sandbox_owned_by_hive=env.runner_path is not None,
            ),
            confidence={
                "install_path": "high" if env.install_path else "none",
                "managed_runner": "high" if env.runner_path else "none",
            },
            evidence={
                "install_path": env.install_path or "missing",
                "runner_path": str(env.runner_path) if env.runner_path is not None else "missing",
            },
            governance_mode=str(env.effective_governance),
            integration_level=str(env.effective_level),
            adapter_family=str(self.adapter_family),
        )
        return IntegrationInfo(
            adapter=self.name,
            adapter_family=self.adapter_family,
            governance_mode=env.effective_governance,
            integration_level=env.effective_level,
            version=version,
            available=env.available,
            capability_snapshot=snapshot,
            supported_levels=env.supported_levels,
            supported_governance_modes=env.supported_governance_modes,
            install_path=env.install_path,
            configuration_problems=env.configuration_problems,
            next_steps=env.next_steps,
            notes=notes,
        )

    def prepare(self, run_id: str, config: dict[str, Any]) -> dict[str, Any]:
        env = self._environment(config.get("workspace_root"))
        return {
            "ok": True,
            "run_id": run_id,
            "workspace_root": str(env.workspace_root),
            "install_path": env.install_path,
            "supported_levels": [str(level) for level in env.supported_levels],
        }

    def open_session(self, request: RunLaunchRequest) -> SessionHandle:
        env = self._environment(Path(request.workspace.repo_root))
        if env.node_path is None or env.runner_path is None:
            raise FileNotFoundError(
                "Pi managed mode requires Node.js and a pi-hive-runner entrypoint."
            )
        runner_command = build_pi_runner_command(
            request,
            node_path=env.node_path,
            runner_path=env.runner_path,
        )
        session = SessionHandle(
            session_id=new_id("sess"),
            adapter_name=self.name,
            adapter_family=self.adapter_family,
            native_session_ref=f"pi-managed:{request.run_id}",
            governance_mode=GovernanceMode.GOVERNED,
            integration_level=IntegrationLevel.MANAGED,
            run_id=request.run_id,
            project_id=request.project_id,
            task_id=request.task_id,
            status="active",
            metadata={
                "workspace_root": request.workspace.repo_root,
                "worktree_path": request.workspace.worktree_path,
                "compiled_context_path": request.compiled_context_path,
                "artifacts_path": request.artifacts_path,
                "package_path": env.install_path,
                "runner_path": str(env.runner_path),
                "runner_command": runner_command,
                "link_transport": "stdio",
            },
        )
        self._sessions[session.session_id] = session
        self._events[session.session_id] = [
            trajectory_event(
                seq=0,
                kind="session_start",
                harness="pi",
                adapter_family=str(self.adapter_family),
                native_session_ref=session.native_session_ref,
                run_id=session.run_id,
                project_id=session.project_id,
                task_id=session.task_id,
                payload={"mode": "managed"},
            ).to_dict(),
            trajectory_event(
                seq=1,
                kind="assistant_delta",
                harness="pi",
                adapter_family=str(self.adapter_family),
                native_session_ref=session.native_session_ref,
                run_id=session.run_id,
                project_id=session.project_id,
                task_id=session.task_id,
                payload={"text": "Pi managed runner scaffold prepared."},
            ).to_dict(),
            trajectory_event(
                seq=2,
                kind="artifact_written",
                harness="pi",
                adapter_family=str(self.adapter_family),
                native_session_ref=session.native_session_ref,
                run_id=session.run_id,
                project_id=session.project_id,
                task_id=session.task_id,
                payload={"path": request.artifacts_path, "kind": "runner-plan"},
            ).to_dict(),
        ]
        return session

    def attach_session(
        self,
        native_session_ref: str,
        governance: GovernanceMode,
        run_id: str | None = None,
    ) -> SessionHandle:
        env = self._environment()
        if env.package_dir is None or env.cli_path is None:
            raise FileNotFoundError("Pi attach mode requires the pi-hive companion package.")
        session = SessionHandle(
            session_id=new_id("sess"),
            adapter_name=self.name,
            adapter_family=self.adapter_family,
            native_session_ref=native_session_ref,
            governance_mode=governance,
            integration_level=IntegrationLevel.ATTACH,
            run_id=run_id,
            status="active",
            metadata={
                "workspace_root": str(env.workspace_root),
                "package_path": env.install_path,
                "link_transport": "stdio",
            },
        )
        self._sessions[session.session_id] = session
        self._events[session.session_id] = [
            trajectory_event(
                seq=0,
                kind="session_start",
                harness="pi",
                adapter_family=str(self.adapter_family),
                native_session_ref=session.native_session_ref,
                run_id=session.run_id,
                payload={"mode": "attach", "governance_mode": str(governance)},
            ).to_dict(),
            trajectory_event(
                seq=1,
                kind="assistant_delta",
                harness="pi",
                adapter_family=str(self.adapter_family),
                native_session_ref=session.native_session_ref,
                run_id=session.run_id,
                payload={"text": "Attached live Pi session to Hive scaffolding."},
            ).to_dict(),
        ]
        return session

    def stream_events(self, session: SessionHandle) -> Iterator[dict[str, Any]]:
        events = list(self._events.get(session.session_id, []))
        if session.session_id not in self._streamed_sessions:
            self._streamed_sessions.add(session.session_id)
            workspace_root = session.metadata.get("workspace_root")
            if workspace_root and session.run_id:
                for event in events:
                    append_trajectory_event(Path(workspace_root), trajectory_event(**event))
        yield from events

    def send_steer(
        self, session: SessionHandle, request: SteeringRequest
    ) -> dict[str, Any]:
        record = {
            "session_id": session.session_id,
            "action": request.action,
            "reason": request.reason,
            "note": request.note,
            "ts": utc_now_iso(),
        }
        self._steers.append(record)
        workspace_root = session.metadata.get("workspace_root")
        if workspace_root and session.run_id:
            append_trajectory_event(
                Path(workspace_root),
                trajectory_event(
                    seq=len(self._events.get(session.session_id, [])) + len(self._steers) - 1,
                    kind="steering_received",
                    harness="pi",
                    adapter_family=str(self.adapter_family),
                    native_session_ref=session.native_session_ref,
                    run_id=session.run_id,
                    payload={
                        "action": request.action,
                        "reason": request.reason,
                        "note": request.note,
                    },
                ),
            )
        return {"ok": True, **record}

    def collect_artifacts(self, session: SessionHandle) -> dict[str, Any]:
        trajectory_path = None
        workspace_root = session.metadata.get("workspace_root")
        if workspace_root and session.run_id:
            trajectory_path = str(trajectory_file(Path(workspace_root), run_id=session.run_id))
        return {
            "adapter": self.name,
            "session_id": session.session_id,
            "trajectory_path": trajectory_path,
            "runner_command": session.metadata.get("runner_command"),
            "artifacts": [],
        }

    def close_session(self, session: SessionHandle, reason: str) -> dict[str, Any]:
        session.status = "closed"
        return {"ok": True, "session_id": session.session_id, "reason": reason}


__all__ = ["PiEnvironment", "PiWorkerAdapter", "detect_pi_environment"]

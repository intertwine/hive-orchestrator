"""Pi worker-session integration scaffolding for the v2.4 release line."""

from __future__ import annotations

import json
import os
import signal
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
                        "Run `pi-hive open <task-id>` inside a Hive workspace to launch managed Pi mode.",
                        "Run `pi-hive attach <native-session-ref> --task-id <task-id>` to bind a live Pi session as advisory.",
                        "Use `hive run status <run-id>` or `pi-hive status <run-id>` to inspect the live session state.",
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


def _safe_native_session_ref(native_session_ref: str) -> str:
    return "".join(
        character if character.isalnum() or character in {"-", "_", "."} else "_"
        for character in native_session_ref
    )


def _native_sessions_dir(workspace_root: Path) -> Path:
    return workspace_root / ".hive" / "pi-native" / "sessions"


def _native_session_dir(workspace_root: Path, native_session_ref: str) -> Path:
    return _native_sessions_dir(workspace_root) / _safe_native_session_ref(native_session_ref)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _jsonl_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


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

    def _environment(self, workspace_root: Path | None = None) -> PiEnvironment:
        return self._detector(workspace_root or self.workspace_root).ensure_defaults()

    def _session_snapshot(
        self,
        env: PiEnvironment,
        *,
        governance: GovernanceMode,
        integration_level: IntegrationLevel,
    ) -> CapabilitySnapshot:
        launch_mode = "sdk" if integration_level == IntegrationLevel.MANAGED else "session"
        return CapabilitySnapshot(
            driver=self.name,
            driver_version=env.package_version or "0.0.0",
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
                "workspace_root": str(env.workspace_root),
                "install_path": env.install_path,
                "cli_path": str(env.cli_path) if env.cli_path is not None else None,
                "runner_path": str(env.runner_path) if env.runner_path is not None else None,
            },
            effective=capability_surface(
                launch_mode=launch_mode,
                session_persistence="session",
                event_stream="structured_deltas",
                attach_supported=True,
                managed_supported=integration_level == IntegrationLevel.MANAGED,
                steering="queued",
                approvals=["hive-mediated"] if governance == GovernanceMode.GOVERNED else [],
                artifacts=["trajectory", "session-history", "logs"],
                native_sandbox="pi",
                context_projection="filesystem",
                outer_sandbox_owned_by_hive=governance == GovernanceMode.GOVERNED,
            ),
            confidence={
                "install_path": "high" if env.install_path else "none",
                "runner_path": "high" if env.runner_path else "none",
            },
            evidence={
                "install_path": env.install_path or "missing",
                "runner_path": str(env.runner_path) if env.runner_path is not None else "missing",
            },
            governance_mode=str(governance),
            integration_level=str(integration_level),
            adapter_family=str(self.adapter_family),
        )

    def _append_run_event(
        self,
        workspace_root: Path,
        *,
        run_id: str,
        native_session_ref: str,
        project_id: str | None,
        task_id: str | None,
        kind: str,
        payload: dict[str, Any],
        raw_ref: str | None = None,
    ) -> None:
        path = trajectory_file(workspace_root, run_id=run_id)
        append_trajectory_event(
            workspace_root,
            trajectory_event(
                seq=_jsonl_count(path),
                kind=kind,
                harness="pi",
                adapter_family=str(self.adapter_family),
                native_session_ref=native_session_ref,
                run_id=run_id,
                project_id=project_id,
                task_id=task_id,
                payload=payload,
                raw_ref=raw_ref,
            ),
        )

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
        run_root = trajectory_file(env.workspace_root, run_id=request.run_id).parent
        logs_dir = run_root / "logs"
        artifacts_dir = run_root / "artifacts"
        state_path = run_root / "pi-session-state.json"
        steering_path = run_root / "steering.ndjson"
        runner_manifest_path = run_root / "pi-runner-manifest.json"
        stdout_path = logs_dir / "pi-runner.stdout.txt"
        stderr_path = logs_dir / "pi-runner.stderr.txt"
        last_message_path = artifacts_dir / "pi-last-message.txt"
        for directory in (logs_dir, artifacts_dir):
            directory.mkdir(parents=True, exist_ok=True)
        steering_path.touch(exist_ok=True)
        snapshot = self._session_snapshot(
            env,
            governance=GovernanceMode.GOVERNED,
            integration_level=IntegrationLevel.MANAGED,
        )
        native_session_ref = f"pi-managed:{request.run_id}"
        _write_json(
            state_path,
            {
                "state": "running",
                "health": "healthy",
                "message": "Launching Pi managed session.",
                "updated_at": utc_now_iso(),
            },
        )
        self._append_run_event(
            env.workspace_root,
            run_id=request.run_id,
            native_session_ref=native_session_ref,
            project_id=request.project_id,
            task_id=request.task_id,
            kind="session_start",
            payload={"mode": "managed"},
        )
        self._append_run_event(
            env.workspace_root,
            run_id=request.run_id,
            native_session_ref=native_session_ref,
            project_id=request.project_id,
            task_id=request.task_id,
            kind="assistant_delta",
            payload={"text": "Pi managed session connected to the Hive run."},
        )
        self._append_run_event(
            env.workspace_root,
            run_id=request.run_id,
            native_session_ref=native_session_ref,
            project_id=request.project_id,
            task_id=request.task_id,
            kind="artifact_written",
            payload={"path": request.compiled_context_path, "kind": "compiled-context"},
        )
        runner_command = build_pi_runner_command(
            request,
            node_path=env.node_path,
            runner_path=env.runner_path,
            state_path=state_path,
            steering_path=steering_path,
            trajectory_path=trajectory_file(env.workspace_root, run_id=request.run_id),
            last_message_path=last_message_path,
            native_session_ref=native_session_ref,
        )
        pid = None
        with open(stdout_path, "a", encoding="utf-8") as stdout_handle, open(
            stderr_path, "a", encoding="utf-8"
        ) as stderr_handle:
            process = subprocess.Popen(
                runner_command,
                cwd=(
                    request.workspace.worktree_path
                    if Path(request.workspace.worktree_path).exists()
                    else str(env.workspace_root)
                ),
                stdout=stdout_handle,
                stderr=stderr_handle,
            )
        pid = process.pid
        session = SessionHandle(
            session_id=new_id("sess"),
            adapter_name=self.name,
            adapter_family=self.adapter_family,
            native_session_ref=native_session_ref,
            governance_mode=GovernanceMode.GOVERNED,
            integration_level=IntegrationLevel.MANAGED,
            run_id=request.run_id,
            project_id=request.project_id,
            task_id=request.task_id,
            status="active",
            metadata={
                "workspace_root": str(env.workspace_root),
                "worktree_path": request.workspace.worktree_path,
                "compiled_context_path": request.compiled_context_path,
                "artifacts_path": request.artifacts_path,
                "package_path": env.install_path,
                "runner_path": str(env.runner_path),
                "runner_command": runner_command,
                "link_transport": "stdio",
                "state_path": str(state_path),
                "steering_path": str(steering_path),
                "trajectory_path": str(trajectory_file(env.workspace_root, run_id=request.run_id)),
                "runner_manifest_path": str(runner_manifest_path),
                "stdout_path": str(stdout_path),
                "stderr_path": str(stderr_path),
                "last_message_path": str(last_message_path),
                "capability_snapshot": snapshot.to_dict(),
                "pid": pid,
            },
        )
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
        native_session_root = _native_session_dir(env.workspace_root, native_session_ref)
        native_manifest_path = native_session_root / "manifest.json"
        native_state_path = native_session_root / "state.json"
        native_transcript_path = native_session_root / "transcript.jsonl"
        native_steering_path = native_session_root / "steering.ndjson"
        if not native_manifest_path.exists():
            raise FileNotFoundError(
                f"Pi native session not found: {native_session_ref}. "
                "Start a live Pi session before attaching it to Hive."
            )
        run_root = trajectory_file(env.workspace_root, run_id=run_id).parent if run_id else None
        state_path = run_root / "pi-session-state.json" if run_root else native_state_path
        steering_path = run_root / "steering.ndjson" if run_root else native_steering_path
        last_message_path = run_root / "artifacts" / "pi-last-message.txt" if run_root else None
        if run_root:
            (run_root / "artifacts").mkdir(parents=True, exist_ok=True)
            steering_path.touch(exist_ok=True)
        snapshot = self._session_snapshot(
            env,
            governance=governance,
            integration_level=IntegrationLevel.ATTACH,
        )
        _write_json(
            state_path,
            {
                "state": "running",
                "health": "healthy",
                "message": "Attached live Pi session to Hive.",
                "updated_at": utc_now_iso(),
                "native_session_root": str(native_session_root),
            },
        )
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
                "state_path": str(state_path),
                "steering_path": str(steering_path),
                "trajectory_path": str(trajectory_file(env.workspace_root, run_id=run_id))
                if run_id
                else None,
                "last_message_path": str(last_message_path) if last_message_path else None,
                "native_session_root": str(native_session_root),
                "native_manifest_path": str(native_manifest_path),
                "native_state_path": str(native_state_path),
                "native_transcript_path": str(native_transcript_path),
                "native_steering_path": str(native_steering_path),
                "capability_snapshot": snapshot.to_dict(),
            },
        )
        if run_id:
            self._append_run_event(
                env.workspace_root,
                run_id=run_id,
                native_session_ref=native_session_ref,
                project_id=session.project_id,
                task_id=session.task_id,
                kind="session_start",
                payload={"mode": "attach", "governance_mode": str(governance)},
                raw_ref=str(native_transcript_path),
            )
            self._append_run_event(
                env.workspace_root,
                run_id=run_id,
                native_session_ref=native_session_ref,
                project_id=session.project_id,
                task_id=session.task_id,
                kind="assistant_delta",
                payload={"text": "Attached live Pi session to Hive."},
                raw_ref=str(native_transcript_path),
            )
        return session

    def stream_events(self, session: SessionHandle) -> Iterator[dict[str, Any]]:
        trajectory_path = str(session.metadata.get("trajectory_path") or "")
        if trajectory_path:
            path = Path(trajectory_path)
        else:
            path = Path(str(session.metadata.get("native_transcript_path") or ""))
        if not path.exists():
            return
        for line in path.read_text(encoding="utf-8").splitlines():
            raw = line.strip()
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                yield payload

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
        steering_path_value = str(session.metadata.get("steering_path") or "")
        if steering_path_value:
            _append_jsonl(Path(steering_path_value), record)
        native_steering_path_value = str(session.metadata.get("native_steering_path") or "")
        if native_steering_path_value:
            _append_jsonl(Path(native_steering_path_value), record)
        workspace_root = str(session.metadata.get("workspace_root") or "")
        if workspace_root and session.run_id:
            self._append_run_event(
                Path(workspace_root),
                run_id=session.run_id,
                native_session_ref=session.native_session_ref,
                project_id=session.project_id,
                task_id=session.task_id,
                kind="steering_received",
                payload={
                    "action": request.action,
                    "reason": request.reason,
                    "note": request.note,
                },
                raw_ref=native_steering_path_value or None,
            )
        return {"ok": True, **record}

    def collect_artifacts(self, session: SessionHandle) -> dict[str, Any]:
        artifacts = []
        for key in (
            "trajectory_path",
            "steering_path",
            "state_path",
            "runner_manifest_path",
            "stdout_path",
            "stderr_path",
            "native_manifest_path",
            "native_state_path",
            "native_transcript_path",
            "native_steering_path",
        ):
            path_value = str(session.metadata.get(key) or "").strip()
            if path_value and Path(path_value).exists():
                artifacts.append({"name": key, "path": path_value})
        return {
            "adapter": self.name,
            "session_id": session.session_id,
            "trajectory_path": session.metadata.get("trajectory_path"),
            "steering_path": session.metadata.get("steering_path"),
            "runner_command": session.metadata.get("runner_command"),
            "artifacts": artifacts,
        }

    def close_session(self, session: SessionHandle, reason: str) -> dict[str, Any]:
        session.status = "closed"
        state_path_value = str(session.metadata.get("state_path") or "")
        if state_path_value:
            _write_json(
                Path(state_path_value),
                {
                    "state": "cancelled" if reason == "cancel" else "completed_candidate",
                    "health": "cancelled" if reason == "cancel" else "healthy",
                    "message": reason,
                    "updated_at": utc_now_iso(),
                    "finished_at": utc_now_iso(),
                },
            )
        if session.run_id and session.metadata.get("workspace_root"):
            self._append_run_event(
                Path(str(session.metadata["workspace_root"])),
                run_id=session.run_id,
                native_session_ref=session.native_session_ref,
                project_id=session.project_id,
                task_id=session.task_id,
                kind="session_end",
                payload={"reason": reason},
            )
        pid = session.metadata.get("pid")
        if session.governance_mode == GovernanceMode.GOVERNED and pid:
            try:
                os.kill(int(pid), signal.SIGTERM)
            except (OSError, ValueError):
                pass
        return {"ok": True, "session_id": session.session_id, "reason": reason}


__all__ = ["PiEnvironment", "PiWorkerAdapter", "detect_pi_environment"]

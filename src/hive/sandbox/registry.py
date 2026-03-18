"""Static sandbox backend registry for v2.3 doctor scaffolding."""

from __future__ import annotations

from abc import ABC, abstractmethod
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Iterable

from src.hive.sandbox.base import SandboxProbe


class SandboxBackend(ABC):
    """Probe-only backend skeleton until full runtime integration lands."""

    name: str
    isolation_class: str
    binaries: tuple[str, ...] = ()
    experimental: bool = False
    supported_profiles: tuple[str, ...] = ()

    @abstractmethod
    def probe(self) -> SandboxProbe:
        """Return truthful probe data for the backend."""


class BinarySandboxBackend(SandboxBackend):
    """Generic probe that checks binary presence or availability hints."""

    note_when_missing: str = "Backend binary was not detected on PATH."

    def _find_binary(self) -> str | None:
        for candidate in self.binaries:
            location = shutil.which(candidate)
            if location:
                return str(Path(location).resolve())
        return None

    def _command_output(self, *args: str) -> str | None:
        binary = self._find_binary()
        if binary is None:
            return None
        try:
            completed = subprocess.run(
                [binary, *args],
                text=True,
                capture_output=True,
                check=False,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if completed.returncode != 0:
            return None
        return completed.stdout.strip() or None

    def probe(self) -> SandboxProbe:
        binary = self._find_binary()
        notes = []
        evidence = {}
        blockers = []
        if binary:
            notes.append(f"Detected backend binary at {binary}.")
            evidence["binary"] = binary
            version = self._command_output("--version")
            if version:
                evidence["version"] = version
        else:
            blockers.append(self.note_when_missing)
        return SandboxProbe(
            backend=self.name,
            available=bool(binary),
            isolation_class=self.isolation_class,
            configured=bool(binary),
            supported_profiles=list(self.supported_profiles),
            experimental=self.experimental,
            blockers=blockers,
            notes=notes,
            evidence=evidence,
        )


class CredentialAwareSandboxBackend(BinarySandboxBackend):
    """Probe remote backends that need non-interactive auth or target config."""

    auth_env_groups: tuple[tuple[str, ...], ...] = ()
    required_env: tuple[str, ...] = ()
    auth_warning = (
        "Hive could not verify non-interactive credentials from environment variables; "
        "interactive CLI login may still be configured."
    )
    required_env_note = ""

    def probe(self) -> SandboxProbe:
        probe = super().probe()
        if not probe.available:
            probe.configured = False
            return probe
        env_names = {
            name
            for group in self.auth_env_groups
            for name in group
        } | set(self.required_env)
        env_state = {name: bool(os.getenv(name)) for name in sorted(env_names)}
        if env_state:
            probe.evidence["env"] = env_state
        matched_group = next(
            (
                group
                for group in self.auth_env_groups
                if group and all(os.getenv(name) for name in group)
            ),
            None,
        )
        if matched_group:
            probe.notes.append(
                "Detected non-interactive configuration via "
                + ", ".join(matched_group)
                + "."
            )
            probe.evidence["auth_source"] = list(matched_group)
        elif self.auth_env_groups:
            probe.warnings.append(self.auth_warning)
        missing_required = [name for name in self.required_env if not os.getenv(name)]
        if missing_required:
            note = self.required_env_note or (
                "Missing required configuration: " + ", ".join(missing_required) + "."
            )
            probe.blockers.append(note)
        probe.configured = matched_group is not None and not missing_required
        return probe


class PodmanBackend(BinarySandboxBackend):
    name = "podman"
    isolation_class = "container"
    binaries = ("podman",)
    supported_profiles = ("local-safe",)

    def probe(self) -> SandboxProbe:
        probe = super().probe()
        if not probe.available:
            return probe
        info_text = self._command_output("info", "--format", "json")
        if not info_text:
            probe.notes.append("Podman info was unavailable; assuming local-safe support from CLI.")
            return probe
        try:
            payload = json.loads(info_text)
        except json.JSONDecodeError:
            probe.notes.append("Podman info returned non-JSON output; rootless status unverified.")
            return probe
        rootless = bool(((payload.get("host") or {}).get("security") or {}).get("rootless", True))
        probe.evidence["rootless"] = rootless
        if not rootless:
            probe.available = False
            probe.configured = False
            probe.notes.append("Podman is installed but is not running rootless.")
        else:
            probe.notes.append("Podman rootless mode is available for local-safe sandboxing.")
        return probe


class DockerRootlessBackend(BinarySandboxBackend):
    name = "docker-rootless"
    isolation_class = "container"
    binaries = ("docker",)
    supported_profiles = ("local-safe",)
    note_when_missing = "Docker CLI was not detected on PATH."

    def probe(self) -> SandboxProbe:
        probe = super().probe()
        if not probe.available:
            return probe
        security_options = self._command_output("info", "--format", "{{json .SecurityOptions}}")
        rootless = bool(security_options and "rootless" in security_options.casefold())
        probe.evidence["rootless"] = rootless
        if rootless:
            probe.notes.append("Docker daemon advertises rootless security mode.")
            return probe
        probe.available = False
        probe.configured = False
        probe.notes.append(
            "Docker CLI is present, but the daemon is not advertising rootless mode."
        )
        return probe


class AsrtBackend(BinarySandboxBackend):
    name = "asrt"
    isolation_class = "process-wrapper"
    binaries = ("srt", "asandbox", "anthropic-sandbox")
    supported_profiles = ("local-fast",)
    note_when_missing = "Anthropic Sandbox Runtime (`srt`) was not detected on PATH."


class E2BBackend(CredentialAwareSandboxBackend):
    name = "e2b"
    isolation_class = "managed-sandbox"
    binaries = ("e2b",)
    supported_profiles = ("hosted-managed",)
    auth_env_groups = (("E2B_API_KEY",), ("E2B_ACCESS_TOKEN",))
    auth_warning = (
        "E2B CLI is present, but Hive did not detect `E2B_API_KEY` or `E2B_ACCESS_TOKEN`; "
        "interactive `e2b auth login` may still work, but automation readiness is unverified."
    )

    @staticmethod
    def _sdk_available() -> bool:
        return importlib.util.find_spec("e2b") is not None

    def probe(self) -> SandboxProbe:
        probe = super().probe()
        has_sdk = self._sdk_available()
        probe.evidence["python_sdk"] = has_sdk
        env_names = {
            name
            for group in self.auth_env_groups
            for name in group
        }
        matched_group = next(
            (
                group
                for group in self.auth_env_groups
                if group and all(os.getenv(name) for name in group)
            ),
            None,
        )
        if env_names:
            probe.evidence["env"] = {name: bool(os.getenv(name)) for name in sorted(env_names)}
        if has_sdk:
            probe.notes.append("Detected Python E2B SDK for hosted-managed execution.")
            if not probe.available:
                probe.available = True
                probe.notes.append("Python E2B SDK is available even though the CLI is missing.")
                probe.blockers = [
                    blocker for blocker in probe.blockers if blocker != self.note_when_missing
                ]
            if matched_group:
                probe.evidence["auth_source"] = list(matched_group)
                if not any(
                    "Detected non-interactive configuration via" in note for note in probe.notes
                ):
                    probe.notes.append(
                        "Detected non-interactive configuration via "
                        + ", ".join(matched_group)
                        + "."
                    )
            elif self.auth_env_groups and self.auth_warning not in probe.warnings:
                probe.warnings.append(self.auth_warning)
        else:
            probe.blockers.append(
                "Install `mellona-hive[sandbox-e2b]` or `pip install e2b` "
                "for hosted-managed execution."
            )
        probe.configured = bool(matched_group and has_sdk)
        return probe


class DaytonaBackend(CredentialAwareSandboxBackend):
    name = "daytona"
    isolation_class = "remote-sandbox"
    binaries = ("daytona",)
    supported_profiles = ("team-self-hosted",)
    auth_env_groups = (("DAYTONA_API_KEY",), ("DAYTONA_JWT_TOKEN", "DAYTONA_ORGANIZATION_ID"))
    required_env = ("DAYTONA_API_URL",)
    auth_warning = (
        "Daytona CLI is present, but Hive did not detect `DAYTONA_API_KEY` or the "
        "`DAYTONA_JWT_TOKEN` + `DAYTONA_ORGANIZATION_ID` pair."
    )
    required_env_note = (
        "Missing `DAYTONA_API_URL`, so Hive cannot verify a team-self-hosted Daytona "
        "control plane target."
    )

    @staticmethod
    def _sdk_available() -> bool:
        return importlib.util.find_spec("daytona") is not None

    def probe(self) -> SandboxProbe:
        probe = super().probe()
        has_sdk = self._sdk_available()
        probe.evidence["python_sdk"] = has_sdk
        env_names = {
            name
            for group in self.auth_env_groups
            for name in group
        } | set(self.required_env)
        matched_group = next(
            (
                group
                for group in self.auth_env_groups
                if group and all(os.getenv(name) for name in group)
            ),
            None,
        )
        if env_names:
            probe.evidence["env"] = {name: bool(os.getenv(name)) for name in sorted(env_names)}
        if has_sdk:
            probe.notes.append("Detected Python Daytona SDK for team-self-hosted execution.")
            if not probe.available:
                probe.available = True
                probe.notes.append("Python Daytona SDK is available even though the CLI is missing.")
                probe.blockers = [
                    blocker for blocker in probe.blockers if blocker != self.note_when_missing
                ]
            if matched_group:
                probe.evidence["auth_source"] = list(matched_group)
                if not any(
                    "Detected non-interactive configuration via" in note for note in probe.notes
                ):
                    probe.notes.append(
                        "Detected non-interactive configuration via "
                        + ", ".join(matched_group)
                        + "."
                    )
            elif self.auth_env_groups and self.auth_warning not in probe.warnings:
                probe.warnings.append(self.auth_warning)
        else:
            probe.blockers.append(
                "Install `mellona-hive[sandbox-daytona]` or `pip install daytona` "
                "for team-self-hosted execution."
            )
        missing_required = [name for name in self.required_env if not os.getenv(name)]
        probe.configured = bool(matched_group and has_sdk and not missing_required)
        return probe


class CloudflareBackend(CredentialAwareSandboxBackend):
    name = "cloudflare"
    isolation_class = "remote-sandbox"
    binaries = ("wrangler",)
    experimental = True
    supported_profiles = ("experimental",)
    note_when_missing = "Wrangler was not detected on PATH for Cloudflare sandbox experiments."
    auth_env_groups = (("CLOUDFLARE_API_TOKEN",), ("CLOUDFLARE_API_KEY", "CLOUDFLARE_EMAIL"))
    auth_warning = (
        "Wrangler is present, but Hive did not detect Cloudflare API credentials; "
        "interactive `wrangler login` may still work, but automation readiness is unverified."
    )


_BACKENDS = {
    "podman": PodmanBackend(),
    "docker-rootless": DockerRootlessBackend(),
    "asrt": AsrtBackend(),
    "e2b": E2BBackend(),
    "daytona": DaytonaBackend(),
    "cloudflare": CloudflareBackend(),
}


def list_backends() -> list[SandboxBackend]:
    """Return registered backends in stable order."""
    order = ("podman", "docker-rootless", "asrt", "e2b", "daytona", "cloudflare")
    return [_BACKENDS[name] for name in order]


def get_backend(name: str) -> SandboxBackend:
    """Return one backend by normalized name."""
    normalized = name.strip().lower()
    try:
        return _BACKENDS[normalized]
    except KeyError as exc:
        supported = ", ".join(sorted(_BACKENDS))
        raise ValueError(
            f"Unsupported sandbox backend: {name}. Supported backends: {supported}"
        ) from exc


def iter_backend_probes(names: Iterable[str] | None = None) -> list[SandboxProbe]:
    """Probe all or a subset of backends."""
    if names is None:
        return [backend.probe() for backend in list_backends()]
    return [get_backend(name).probe() for name in names]


__all__ = ["SandboxBackend", "get_backend", "iter_backend_probes", "list_backends"]

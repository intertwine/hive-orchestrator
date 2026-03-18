"""Static sandbox backend registry for v2.3 doctor scaffolding."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
import shutil
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

    def probe(self) -> SandboxProbe:
        binary = self._find_binary()
        notes = []
        evidence = {}
        if binary:
            notes.append(f"Detected backend binary at {binary}.")
            evidence["binary"] = binary
        else:
            notes.append(self.note_when_missing)
        return SandboxProbe(
            backend=self.name,
            available=bool(binary),
            isolation_class=self.isolation_class,
            supported_profiles=list(self.supported_profiles),
            experimental=self.experimental,
            notes=notes,
            evidence=evidence,
        )


class PodmanBackend(BinarySandboxBackend):
    name = "podman"
    isolation_class = "container"
    binaries = ("podman",)
    supported_profiles = ("local-safe",)


class DockerRootlessBackend(BinarySandboxBackend):
    name = "docker-rootless"
    isolation_class = "container"
    binaries = ("docker",)
    supported_profiles = ("local-safe",)
    note_when_missing = "Docker CLI was not detected on PATH."


class AsrtBackend(BinarySandboxBackend):
    name = "asrt"
    isolation_class = "process-wrapper"
    binaries = ("sandbox-exec", "asandbox", "anthropic-sandbox")
    supported_profiles = ("local-fast",)
    note_when_missing = "Anthropic sandbox runtime was not detected on PATH."


class E2BBackend(BinarySandboxBackend):
    name = "e2b"
    isolation_class = "managed-sandbox"
    binaries = ("e2b",)
    supported_profiles = ("hosted-managed",)


class DaytonaBackend(BinarySandboxBackend):
    name = "daytona"
    isolation_class = "remote-sandbox"
    binaries = ("daytona",)
    supported_profiles = ("team-self-hosted",)


class CloudflareBackend(BinarySandboxBackend):
    name = "cloudflare"
    isolation_class = "remote-sandbox"
    binaries = ("wrangler",)
    experimental = True
    supported_profiles = ("experimental",)
    note_when_missing = "Wrangler was not detected on PATH for Cloudflare sandbox experiments."


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

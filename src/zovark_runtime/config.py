"""Deterministic local runtime configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LocalRuntimeConfig:
    """Local-only config for the Phase 1 monolith skeleton.

    This config intentionally has no network, database, credential, connector,
    control-plane, or live system settings.
    """

    tenant_id: str = "tenant-local-dev"
    data_dir: Path = Path(".tmp/zovark-runtime")

    def as_dict(self) -> dict[str, str]:
        """Return a deterministic JSON-serializable representation."""

        return {
            "tenant_id": self.tenant_id,
            "data_dir": self.data_dir.as_posix(),
        }


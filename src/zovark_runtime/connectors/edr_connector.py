"""EDR connector: normalize a provider alert into the deterministic input shape.

- `normalize_provider_alert` is a pure, offline, deterministic mapping (no network).
- `RecordedEdrConnector` reads a recorded provider response from disk (no network) — used
  in CI and tests so the deterministic path runs fully offline.
- `LiveEdrConnector` is the ONLY component that may perform network I/O, and only when its
  `fetch()` is explicitly called with endpoint + token supplied via config/env. Missing
  credentials fail closed at the connector boundary. The deterministic proof-package
  pipeline and replay/verify never import or call this.

No secrets or hardcoded provider IDs: credentials come from config/env only; the repo
ships placeholders.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# Map provider detection "kind" -> deterministic event-array key consumed by
# proof_package.ingest._EVENT_COLLECTIONS.
_KIND_TO_ARRAY = {
    "process": "process_events",
    "network": "network_events",
    "network_flow": "network_flows",
    "credential_access": "credential_access_events",
    "lateral_movement": "lateral_movement_events",
}


class ConnectorError(Exception):
    """Raised when a connector cannot produce a deterministic input (fail closed)."""


def normalize_provider_alert(provider: dict[str, Any]) -> dict[str, Any]:
    """Map a provider EDR alert envelope to the deterministic input shape.

    Deterministic and offline. Fails closed on a malformed provider payload.
    Provider shape (bounded): {alert_id, severity, host, timestamp, description,
    detections: [{kind, ...event fields...}]}.
    """
    if not isinstance(provider, dict):
        raise ConnectorError("provider alert must be a JSON object")
    try:
        deterministic: dict[str, Any] = {
            "alert_id": str(provider["alert_id"]),
            "alert_type": "edr_alert",
            "description": str(provider.get("description", "EDR alert")),
            "host": str(provider["host"]),
            "severity": str(provider.get("severity", "high")),
            "timestamp": str(provider["timestamp"]),
        }
    except (KeyError, TypeError) as exc:
        raise ConnectorError(f"provider alert missing required field: {exc}") from exc

    detections = provider.get("detections", [])
    if not isinstance(detections, list):
        raise ConnectorError("provider detections must be a list")
    for index, det in enumerate(detections):
        if not isinstance(det, dict):
            raise ConnectorError(f"detection[{index}] must be an object")
        kind = det.get("kind")
        array_key = _KIND_TO_ARRAY.get(kind)
        if array_key is None:
            raise ConnectorError(f"detection[{index}] has unsupported kind: {kind!r}")
        event = {k: v for k, v in det.items() if k != "kind"}
        deterministic.setdefault(array_key, []).append(event)
    return deterministic


class RecordedEdrConnector:
    """Offline connector: reads a recorded provider response from disk (no network)."""

    def __init__(self, recorded_path: str | Path) -> None:
        self._path = Path(recorded_path)

    def fetch(self) -> dict[str, Any]:
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConnectorError(f"cannot read recorded provider response: {exc}") from exc

    def normalize(self) -> dict[str, Any]:
        return normalize_provider_alert(self.fetch())


class LiveEdrConnector:
    """Live connector boundary. The only place network I/O may occur.

    Credentials are supplied via config/env only (placeholders in the repo). `fetch()`
    fails closed if endpoint or token is missing. This class is never imported or called
    by the deterministic proof-package pipeline or the replay/verify paths.
    """

    def __init__(self, endpoint: str | None = None, token: str | None = None) -> None:
        self.endpoint = endpoint or os.environ.get("ZOVARK_EDR_ENDPOINT")
        self.token = token or os.environ.get("ZOVARK_EDR_TOKEN")

    def fetch(self) -> dict[str, Any]:
        if not self.endpoint or not self.token:
            raise ConnectorError(
                "live EDR connector requires endpoint + token (config/env); none provided"
            )
        if not self.endpoint.startswith("https://"):
            raise ConnectorError("live EDR endpoint must be https:// (no file/other schemes)")
        # Network call lives ONLY here, behind explicit invocation. Imported lazily so the
        # module carries no network import on the deterministic path.
        import urllib.request  # noqa: PLC0415

        request = urllib.request.Request(
            self.endpoint, headers={"Authorization": f"Bearer {self.token}"}
        )
        with urllib.request.urlopen(request) as response:  # pragma: no cover - live only
            return json.loads(response.read().decode("utf-8"))

    def normalize(self) -> dict[str, Any]:
        return normalize_provider_alert(self.fetch())

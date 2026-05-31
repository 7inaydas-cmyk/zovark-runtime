"""Connector ingest boundary (Slice 6).

Connectors fetch/normalize a provider alert into the deterministic input shape that
`proof_package.ingest` consumes. The deterministic proof-package pipeline and replay/
verify paths NEVER perform network I/O; any live fetch exists only behind an explicit
connector and is never invoked by the deterministic path.
"""

from .edr_connector import (
    ConnectorError,
    LiveEdrConnector,
    RecordedEdrConnector,
    normalize_provider_alert,
)

__all__ = [
    "ConnectorError",
    "LiveEdrConnector",
    "RecordedEdrConnector",
    "normalize_provider_alert",
]

"""Slice 6 — EDR connector ingest boundary (staging).

The connector normalizes a provider alert into the deterministic input shape. The
deterministic proof-package pipeline and the replay/verify paths must remain network-free;
network may occur only behind the explicit LiveEdrConnector boundary. Missing credentials
fail closed. Recorded fixtures run fully offline.
"""

from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest

from zovark_runtime.connectors import (
    ConnectorError,
    LiveEdrConnector,
    RecordedEdrConnector,
    normalize_provider_alert,
)
from zovark_runtime.proof_package.pipeline import run_proof_package
from zovark_runtime.proof_package.verify import verify_proof_package_strict

ROOT = Path(__file__).resolve().parents[1]
PROVIDER = ROOT / "tests" / "fixtures" / "edr-provider-001.json"


def _block_network(monkeypatch):
    def _boom(*a, **k):
        raise AssertionError("network access attempted on a network-free path")
    monkeypatch.setattr(socket, "socket", _boom)
    monkeypatch.setattr(socket, "create_connection", _boom, raising=False)


def test_normalize_to_deterministic_shape():
    deterministic = RecordedEdrConnector(PROVIDER).normalize()
    assert deterministic["alert_id"] == "provider-alert-001"
    assert deterministic["alert_type"] == "edr_alert"
    assert deterministic["host"] == "workstation-60.corp.example"
    # detections mapped to deterministic event arrays
    assert len(deterministic["process_events"]) == 1
    assert len(deterministic["network_events"]) == 1
    assert "kind" not in deterministic["process_events"][0]


def test_proof_package_from_connector_verifies_offline(tmp_path, monkeypatch):
    deterministic = RecordedEdrConnector(PROVIDER).normalize()
    input_path = tmp_path / "input.json"
    input_path.write_text(json.dumps(deterministic), encoding="utf-8")
    out = tmp_path / "pkg"
    _block_network(monkeypatch)  # deterministic pipeline must not touch network
    result = run_proof_package(input_path, out, tenant_id="tenant-001")
    assert result["verdict"] == "confirmed_malicious"
    summary = verify_proof_package_strict(out)  # verify must not touch network
    assert summary["status"] == "verified"


def test_replay_verify_network_free(tmp_path, monkeypatch):
    deterministic = RecordedEdrConnector(PROVIDER).normalize()
    inp = tmp_path / "in.json"
    inp.write_text(json.dumps(deterministic), encoding="utf-8")
    out = tmp_path / "pkg"
    run_proof_package(inp, out, tenant_id="tenant-001")
    _block_network(monkeypatch)
    # verify (which re-derives + re-runs offline replay) must not touch network
    assert verify_proof_package_strict(out)["status"] == "verified"


def test_recorded_connector_is_offline(tmp_path, monkeypatch):
    _block_network(monkeypatch)
    deterministic = RecordedEdrConnector(PROVIDER).normalize()  # reads disk only
    assert deterministic["alert_id"] == "provider-alert-001"


def test_live_connector_fails_closed_without_credentials(monkeypatch):
    monkeypatch.delenv("ZOVARK_EDR_ENDPOINT", raising=False)
    monkeypatch.delenv("ZOVARK_EDR_TOKEN", raising=False)
    with pytest.raises(ConnectorError):
        LiveEdrConnector().fetch()


def test_normalize_fails_closed_on_malformed_provider():
    with pytest.raises(ConnectorError):
        normalize_provider_alert({"host": "h"})  # missing alert_id/timestamp
    with pytest.raises(ConnectorError):
        normalize_provider_alert({"alert_id": "a", "host": "h", "timestamp": "t",
                                  "detections": [{"kind": "unknown_kind"}]})


def test_no_network_import_on_deterministic_path():
    # The deterministic proof_package package must not import network modules.
    import zovark_runtime.proof_package.pipeline as pipeline
    import zovark_runtime.proof_package.verify as verify
    for mod in (pipeline, verify):
        src = Path(mod.__file__).read_text(encoding="utf-8")
        for bad in ("import socket", "import urllib", "import http", "requests"):
            assert bad not in src, f"{mod.__name__} references {bad}"


def test_live_connector_rejects_non_https_endpoint(monkeypatch):
    c = LiveEdrConnector(endpoint="file:///etc/passwd", token="x")
    with pytest.raises(ConnectorError):
        c.fetch()

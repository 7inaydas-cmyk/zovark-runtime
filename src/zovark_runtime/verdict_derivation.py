"""Deterministic verdict proof transform for canonical fixture inputs."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    """Return stable compact UTF-8 JSON bytes for canonical proof comparison."""

    return json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    return value


def _hash_hex(label: str, payload: Mapping[str, Any]) -> str:
    digest = hashlib.sha256()
    digest.update(label.encode("ascii"))
    digest.update(b"\0")
    digest.update(canonical_json_bytes(payload))
    return digest.hexdigest()


def _short_hash(label: str, payload: Mapping[str, Any], length: int = 16) -> str:
    return _hash_hex(label, payload)[:length]


def _uuid_from_hash(hex_digest: str) -> str:
    raw = bytearray(bytes.fromhex(hex_digest[:32]))
    raw[6] = (raw[6] & 0x0F) | 0x50
    raw[8] = (raw[8] & 0x3F) | 0x80
    text = raw.hex()
    return f"{text[:8]}-{text[8:12]}-{text[12:16]}-{text[16:20]}-{text[20:32]}"


def _deterministic_uuid(label: str, payload: Mapping[str, Any]) -> str:
    return _uuid_from_hash(_hash_hex(label, payload))


def _source_event_uids(alert_envelope: Mapping[str, Any], raw_finding: Mapping[str, Any]) -> list[str]:
    source_event_uid = raw_finding.get("source_event_uid") or alert_envelope["envelope_id"]
    return sorted([str(source_event_uid)])


def _derive_evidence(verdict_input: Mapping[str, Any]) -> list[dict[str, Any]]:
    alert_envelope = _mapping(verdict_input["alert_envelope"], "alert_envelope")
    raw_finding = _mapping(alert_envelope.get("raw_finding", {}), "alert_envelope.raw_finding")
    normalized_finding = _mapping(
        alert_envelope.get("normalized_finding", {}),
        "alert_envelope.normalized_finding",
    )
    source_event_uids = _source_event_uids(alert_envelope, raw_finding)
    finding_seed = {
        "investigation_id": str(verdict_input["investigation_id"]),
        "source_event_uids": source_event_uids,
        "tenant_id": str(verdict_input["tenant_id"]),
    }
    finding = {
        "finding_id": _deterministic_uuid("finding_id", finding_seed),
        "tenant_id": str(verdict_input["tenant_id"]),
        "ocsf_class_uid": 2004,
        "ocsf_category_uid": 2,
        "severity_id": int(normalized_finding.get("severity_id", 1)),
        "occurred_at_ns": int(raw_finding.get("observed_at_ns", alert_envelope["received_at_ns"])),
        "source_event_uids": source_event_uids,
    }
    return sorted(
        [finding],
        key=lambda item: (
            item["finding_id"],
            item["occurred_at_ns"],
            tuple(item["source_event_uids"]),
        ),
    )


def derive_verdict(verdict_input: Mapping[str, Any]) -> dict[str, Any]:
    """Derive a minimal deterministic VerdictEnvelope for proof fixtures only."""

    tenant_config = _mapping(verdict_input["tenant_config"], "tenant_config")
    threshold_seed = {
        "model_version": str(verdict_input["model_version"]),
        "prompt_hash": str(verdict_input["prompt_hash"]),
        "tool_catalog_version": str(verdict_input["tool_catalog_version"]),
    }
    return {
        "verdict_id": _deterministic_uuid("verdict_id", verdict_input),
        "tenant_id": str(verdict_input["tenant_id"]),
        "investigation_id": str(verdict_input["investigation_id"]),
        "confidence_basis_points": 0,
        "verdict_class": "indeterminate",
        "recommended_actions": [],
        "threshold_version": f"proof-thresholds-{_short_hash('threshold_version', threshold_seed, 12)}",
        "policy_snapshot_version": str(tenant_config["policy_snapshot_version"]),
        "evidence": _derive_evidence(verdict_input),
    }

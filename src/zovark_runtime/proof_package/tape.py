"""Investigation tape creation for Slice 001."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from zovark_runtime.proof_package import ZovarkValidationError
from zovark_runtime.proof_package.hashing import sha256_of_string


SCHEMA_VERSION = "tape/1.0"
DEFAULT_TENANT_ID = "tenant-001"
_REQUIRED_EVIDENCE_FIELDS = {
    "evidence_id",
    "source_type",
    "hash",
    "raw_content",
    "ingested_at",
}
_TIMESTAMP_KEYS = (
    "ingested_at",
    "observed_at",
    "event_time",
    "timestamp",
    "created_at",
)


def create_tape(
    raw_input: dict[str, Any],
    evidence_entries: list[dict[str, Any]],
    *,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """Create an initial recording investigation tape from normalized evidence."""
    if not isinstance(raw_input, dict):
        raise ZovarkValidationError("raw input must be a JSON object")

    _validate_evidence_entries(evidence_entries)

    resolved_tenant_id = _tenant_id(raw_input, override=tenant_id)
    source_alert_ref = _source_alert_ref(raw_input)
    created_at = _deterministic_timestamp(raw_input)
    tape_id = "tape-" + sha256_of_string(
        f"{resolved_tenant_id}:{source_alert_ref}"
    )[:16]

    return {
        "tape_id": tape_id,
        "tenant_id": resolved_tenant_id,
        "schema_version": SCHEMA_VERSION,
        "source_alert_ref": source_alert_ref,
        "state": "recording",
        "created_at": created_at,
        "raw_evidence": deepcopy(evidence_entries),
        "timeline": [],
        "findings": [],
        "verdict": None,
        "audit_ref": None,
    }


def _validate_evidence_entries(evidence_entries: list[dict[str, Any]]) -> None:
    if not isinstance(evidence_entries, list):
        raise ZovarkValidationError("evidence_entries must be a list")
    if not evidence_entries:
        raise ZovarkValidationError("evidence_entries must not be empty")

    for index, entry in enumerate(evidence_entries):
        if not isinstance(entry, dict):
            raise ZovarkValidationError(f"evidence_entries[{index}] must be an object")
        if set(entry) != _REQUIRED_EVIDENCE_FIELDS:
            raise ZovarkValidationError(
                f"evidence_entries[{index}] does not match the Slice 001 evidence shape"
            )
        for key in ("evidence_id", "source_type", "hash", "ingested_at"):
            if not isinstance(entry[key], str) or not entry[key]:
                raise ZovarkValidationError(
                    f"evidence_entries[{index}].{key} must be a non-empty string"
                )
        if not isinstance(entry["raw_content"], dict):
            raise ZovarkValidationError(
                f"evidence_entries[{index}].raw_content must be an object"
            )


def _tenant_id(raw_input: dict[str, Any], *, override: str | None) -> str:
    if override is not None:
        if not isinstance(override, str) or not override:
            raise ZovarkValidationError("tenant_id must be a non-empty string")
        return override

    if "tenant_id" not in raw_input:
        return DEFAULT_TENANT_ID

    value = raw_input["tenant_id"]
    if not isinstance(value, str) or not value:
        raise ZovarkValidationError("tenant_id must be a non-empty string")
    return value


def _source_alert_ref(raw_input: dict[str, Any]) -> str:
    for key in ("source_alert_ref", "alert_id", "id"):
        if key not in raw_input:
            continue
        value = raw_input[key]
        if not isinstance(value, str) or not value:
            raise ZovarkValidationError(f"{key} must be a non-empty string")
        return value
    raise ZovarkValidationError("raw input is missing a deterministic alert reference")


def _deterministic_timestamp(raw_input: dict[str, Any]) -> str:
    for key in _TIMESTAMP_KEYS:
        if key not in raw_input:
            continue
        value = raw_input[key]
        if not isinstance(value, str) or not value:
            raise ZovarkValidationError(f"{key} must be a non-empty string")
        return value
    raise ZovarkValidationError("raw input is missing a deterministic timestamp")

"""Minimal replay validation proof helpers."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from zovark_runtime.verdict_derivation import canonical_json_bytes


EXPECTED_REPLAY_SCHEMA_VERSION = "1.0.0"
EXPECTED_RECORD_FORMAT_VERSION = "1.0.0"
EXPECTED_REPLAY_COMPATIBILITY_CONTRACT = "architecture/replay-compatibility.yaml"
EXPECTED_FAILURE_POLICY = "fail_closed"

OK = "REPLAY_VALIDATION_OK"
SCHEMA_INCOMPATIBLE = "REPLAY_SCHEMA_INCOMPATIBLE"
FAILURE_POLICY_INCOMPATIBLE = "REPLAY_FAILURE_POLICY_INCOMPATIBLE"
VERDICT_INPUT_MISMATCH = "REPLAY_VERDICT_INPUT_MISMATCH"
VERDICT_INPUT_HASH_MISMATCH = "REPLAY_VERDICT_INPUT_HASH_MISMATCH"
VERDICT_ENVELOPE_HASH_MISMATCH = "REPLAY_VERDICT_ENVELOPE_HASH_MISMATCH"
TOOL_CATALOG_VERSION_MISMATCH = "REPLAY_TOOL_CATALOG_VERSION_MISMATCH"
MODEL_VERSION_MISMATCH = "REPLAY_MODEL_VERSION_MISMATCH"
PROMPT_HASH_MISMATCH = "REPLAY_PROMPT_HASH_MISMATCH"
TENANT_INVESTIGATION_MISMATCH = "REPLAY_TENANT_INVESTIGATION_MISMATCH"


@dataclass(frozen=True)
class ReplayValidationResult:
    """Result for the minimal replay proof validation boundary."""

    ok: bool
    code: str
    detail: str


def canonical_sha256_hex(payload: Mapping[str, Any]) -> str:
    """Return the SHA-256 digest of stable canonical JSON bytes."""

    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _success() -> ReplayValidationResult:
    return ReplayValidationResult(ok=True, code=OK, detail="replay record matches expected canonical inputs")


def _failure(code: str, detail: str) -> ReplayValidationResult:
    return ReplayValidationResult(ok=False, code=code, detail=detail)


def _mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    return value


def _sequence(value: Any, field_name: str) -> Sequence[Any]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise TypeError(f"{field_name} must be a non-string sequence")
    return value


def validate_replay_record(
    replay_record: Mapping[str, Any],
    expected_verdict_input: Mapping[str, Any],
    expected_verdict_envelope: Mapping[str, Any],
) -> ReplayValidationResult:
    """Validate one recorded replay proof against already-loaded expected artifacts."""

    try:
        recorded_verdict_input = _mapping(replay_record.get("verdict_input"), "verdict_input")
    except TypeError as exc:
        return _failure(SCHEMA_INCOMPATIBLE, str(exc))

    if "prompt_hashes" not in replay_record:
        return _failure(PROMPT_HASH_MISMATCH, "prompt hashes are missing")
    try:
        prompt_hashes = _sequence(replay_record.get("prompt_hashes"), "prompt_hashes")
    except TypeError as exc:
        return _failure(PROMPT_HASH_MISMATCH, str(exc))

    if replay_record.get("schema_version") != EXPECTED_REPLAY_SCHEMA_VERSION:
        return _failure(SCHEMA_INCOMPATIBLE, "replay schema_version is incompatible")
    if replay_record.get("record_format_version") != EXPECTED_RECORD_FORMAT_VERSION:
        return _failure(SCHEMA_INCOMPATIBLE, "replay record_format_version is incompatible")
    if replay_record.get("replay_compatibility_contract") != EXPECTED_REPLAY_COMPATIBILITY_CONTRACT:
        return _failure(SCHEMA_INCOMPATIBLE, "replay compatibility contract is incompatible")
    if replay_record.get("failure_policy") != EXPECTED_FAILURE_POLICY:
        return _failure(FAILURE_POLICY_INCOMPATIBLE, "replay record does not fail closed")

    if canonical_json_bytes(recorded_verdict_input) != canonical_json_bytes(expected_verdict_input):
        return _failure(VERDICT_INPUT_MISMATCH, "recorded verdict_input differs from expected verdict input")

    verdict_input_hash = canonical_sha256_hex(expected_verdict_input)
    if replay_record.get("verdict_input_hash") != verdict_input_hash:
        return _failure(VERDICT_INPUT_HASH_MISMATCH, "verdict_input_hash does not match canonical input")

    verdict_envelope_hash = canonical_sha256_hex(expected_verdict_envelope)
    if replay_record.get("verdict_envelope_hash") != verdict_envelope_hash:
        return _failure(
            VERDICT_ENVELOPE_HASH_MISMATCH,
            "verdict_envelope_hash does not match canonical envelope",
        )

    if replay_record.get("tool_catalog_version") != expected_verdict_input.get("tool_catalog_version"):
        return _failure(TOOL_CATALOG_VERSION_MISMATCH, "tool catalog version differs from verdict input")
    if replay_record.get("model_version") != expected_verdict_input.get("model_version"):
        return _failure(MODEL_VERSION_MISMATCH, "model version differs from verdict input")
    if replay_record.get("decoding_params") != expected_verdict_input.get("decoding_params"):
        return _failure(MODEL_VERSION_MISMATCH, "decoding parameters differ from verdict input")
    if list(prompt_hashes) != [expected_verdict_input.get("prompt_hash")]:
        return _failure(PROMPT_HASH_MISMATCH, "prompt hashes do not match verdict input prompt hash")

    for field_name in ("tenant_id", "investigation_id"):
        if replay_record.get(field_name) != expected_verdict_input.get(field_name):
            return _failure(TENANT_INVESTIGATION_MISMATCH, f"{field_name} differs from verdict input")
        if replay_record.get(field_name) != expected_verdict_envelope.get(field_name):
            return _failure(TENANT_INVESTIGATION_MISMATCH, f"{field_name} differs from verdict envelope")

    return _success()

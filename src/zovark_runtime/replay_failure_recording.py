"""Canonical replay failure-record emission helpers for local replay proof results."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from zovark_runtime.replay_failure_mapping import (
    REPLAY_DECODING_PARAMS_MISMATCH,
    REPLAY_PROMPT_HASH_MISSING,
    REPLAY_RECORD_FORMAT_INCOMPATIBLE,
    REPLAY_TOOL_CATALOG_MISMATCH,
    REPLAY_TOOL_RETIRED,
    canonical_replay_failure_code,
)
from zovark_runtime.replay_validation import (
    EXPECTED_RECORD_FORMAT_VERSION,
    EXPECTED_REPLAY_COMPATIBILITY_CONTRACT,
    EXPECTED_REPLAY_SCHEMA_VERSION,
    MODEL_VERSION_MISMATCH,
    PROMPT_HASH_MISMATCH,
    SCHEMA_INCOMPATIBLE,
    VERDICT_ENVELOPE_HASH_MISMATCH,
    VERDICT_INPUT_HASH_MISMATCH,
    ReplayValidationResult,
    canonical_sha256_hex,
)


FAILURE_RECORD_SCHEMA_VERSION = "1.0.0"

REPLAY_FAILURE_RECORD_METADATA_BY_CODE = {
    SCHEMA_INCOMPATIBLE: {
        "failure_category": "schema_compatibility",
        "component": "record_schema",
        "field_path": "schema_version",
        "expected_version": EXPECTED_REPLAY_SCHEMA_VERSION,
        "observed_version_field": "schema_version",
        "fail_closed_reason": "Replay record schema version is incompatible with the runtime proof boundary.",
    },
    REPLAY_RECORD_FORMAT_INCOMPATIBLE: {
        "failure_category": "schema_compatibility",
        "component": "record_format",
        "field_path": "record_format_version",
        "expected_version": EXPECTED_RECORD_FORMAT_VERSION,
        "observed_version_field": "record_format_version",
        "fail_closed_reason": "Replay record format version is incompatible with the runtime proof boundary.",
    },
    VERDICT_INPUT_HASH_MISMATCH: {
        "failure_category": "hash_integrity",
        "component": "verdict_input",
        "field_path": "verdict_input_hash",
        "observed_hash_field": "verdict_input_hash",
        "fail_closed_reason": "Replay verdict input hash does not match the expected canonical input.",
    },
    VERDICT_ENVELOPE_HASH_MISMATCH: {
        "failure_category": "hash_integrity",
        "component": "verdict_envelope",
        "field_path": "verdict_envelope_hash",
        "observed_hash_field": "verdict_envelope_hash",
        "fail_closed_reason": "Replay verdict envelope hash does not match the expected canonical envelope.",
    },
    REPLAY_TOOL_CATALOG_MISMATCH: {
        "failure_category": "catalog_compatibility",
        "component": "tool_catalog",
        "field_path": "tool_catalog_version",
        "observed_version_field": "tool_catalog_version",
        "fail_closed_reason": "Replay tool catalog version differs from the canonical verdict input.",
    },
    REPLAY_TOOL_RETIRED: {
        "failure_category": "tool_compatibility",
        "component": "tool_catalog_entry",
        "field_path": "tool_io",
        "fail_closed_reason": "Replay tool identity is retired under the current catalog authority.",
    },
    MODEL_VERSION_MISMATCH: {
        "failure_category": "model_compatibility",
        "component": "model_artifacts",
        "field_path": "model_version",
        "observed_version_field": "model_version",
        "fail_closed_reason": "Replay model version differs from the canonical verdict input.",
    },
    REPLAY_DECODING_PARAMS_MISMATCH: {
        "failure_category": "model_compatibility",
        "component": "decoding_params",
        "field_path": "decoding_params",
        "fail_closed_reason": "Replay decoding parameters differ from the canonical verdict input.",
    },
    PROMPT_HASH_MISMATCH: {
        "failure_category": "prompt_integrity",
        "component": "prompt_hashes",
        "field_path": "prompt_hashes",
        "fail_closed_reason": "Replay prompt hashes do not match the canonical verdict input prompt hash.",
    },
    REPLAY_PROMPT_HASH_MISSING: {
        "failure_category": "prompt_integrity",
        "component": "prompt_hashes",
        "field_path": "prompt_hashes",
        "fail_closed_reason": "Replay prompt hashes are missing from the replay record.",
    },
}


def canonical_replay_failure_record(
    result: ReplayValidationResult,
    replay_record: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Build a bounded canonical replay failure record for a mapped local result."""

    failure_code = canonical_replay_failure_code(result)
    if failure_code is None:
        return None

    metadata = REPLAY_FAILURE_RECORD_METADATA_BY_CODE.get(failure_code)
    if metadata is None:
        return None

    tenant_id = replay_record.get("tenant_id")
    investigation_id = replay_record.get("investigation_id")
    if not isinstance(tenant_id, str) or not isinstance(investigation_id, str):
        return None

    failure_record: dict[str, Any] = {
        "schema_version": FAILURE_RECORD_SCHEMA_VERSION,
        "failure_code": failure_code,
        "failure_category": metadata["failure_category"],
        "tenant_id": tenant_id,
        "investigation_id": investigation_id,
        "replay_compatibility_contract": EXPECTED_REPLAY_COMPATIBILITY_CONTRACT,
        "replay_record_hash": canonical_sha256_hex(replay_record),
        "component": metadata["component"],
        "field_path": metadata["field_path"],
        "fail_closed_reason": metadata["fail_closed_reason"],
    }

    observed_hash_field = metadata.get("observed_hash_field")
    if isinstance(observed_hash_field, str):
        observed_hash = replay_record.get(observed_hash_field)
        if isinstance(observed_hash, str):
            failure_record["observed_hash"] = observed_hash

    expected_version = metadata.get("expected_version")
    if isinstance(expected_version, str):
        failure_record["expected_version"] = expected_version

    observed_version_field = metadata.get("observed_version_field")
    if isinstance(observed_version_field, str):
        observed_version = replay_record.get(observed_version_field)
        if isinstance(observed_version, str):
            failure_record["observed_version"] = observed_version

    return failure_record

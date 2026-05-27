"""Canonical replay failure-code mapping for local replay validation results."""

from __future__ import annotations

from zovark_runtime.replay_validation import (
    MODEL_VERSION_MISMATCH,
    PROMPT_HASH_MISMATCH,
    SCHEMA_INCOMPATIBLE,
    TOOL_CATALOG_VERSION_MISMATCH,
    TOOL_RETIRED,
    TOOL_RETIRED_DETAIL,
    VERDICT_ENVELOPE_HASH_MISMATCH,
    VERDICT_INPUT_HASH_MISMATCH,
    ReplayValidationResult,
)


REPLAY_RECORD_FORMAT_INCOMPATIBLE = "REPLAY_RECORD_FORMAT_INCOMPATIBLE"
REPLAY_TOOL_CATALOG_MISMATCH = "REPLAY_TOOL_CATALOG_MISMATCH"
REPLAY_PROMPT_HASH_MISSING = "REPLAY_PROMPT_HASH_MISSING"
REPLAY_DECODING_PARAMS_MISMATCH = "REPLAY_DECODING_PARAMS_MISMATCH"
REPLAY_TOOL_RETIRED = TOOL_RETIRED

CANONICAL_REPLAY_FAILURE_CODES_BY_LOCAL_RESULT = {
    (SCHEMA_INCOMPATIBLE, "replay schema_version is incompatible"): SCHEMA_INCOMPATIBLE,
    (SCHEMA_INCOMPATIBLE, "replay record_format_version is incompatible"): REPLAY_RECORD_FORMAT_INCOMPATIBLE,
    (VERDICT_INPUT_HASH_MISMATCH, "verdict_input_hash does not match canonical input"): (
        VERDICT_INPUT_HASH_MISMATCH
    ),
    (VERDICT_ENVELOPE_HASH_MISMATCH, "verdict_envelope_hash does not match canonical envelope"): (
        VERDICT_ENVELOPE_HASH_MISMATCH
    ),
    (TOOL_CATALOG_VERSION_MISMATCH, "tool catalog version differs from verdict input"): (
        REPLAY_TOOL_CATALOG_MISMATCH
    ),
    (MODEL_VERSION_MISMATCH, "model version differs from verdict input"): MODEL_VERSION_MISMATCH,
    (MODEL_VERSION_MISMATCH, "decoding parameters differ from verdict input"): REPLAY_DECODING_PARAMS_MISMATCH,
    (TOOL_RETIRED, TOOL_RETIRED_DETAIL): REPLAY_TOOL_RETIRED,
    (PROMPT_HASH_MISMATCH, "prompt hashes are missing"): REPLAY_PROMPT_HASH_MISSING,
    (PROMPT_HASH_MISMATCH, "prompt hashes do not match verdict input prompt hash"): PROMPT_HASH_MISMATCH,
}


def canonical_replay_failure_code_for_local_result(code: str, detail: str) -> str | None:
    """Map a local replay validation code/detail pair to a canonical failure code."""

    return CANONICAL_REPLAY_FAILURE_CODES_BY_LOCAL_RESULT.get((code, detail))


def canonical_replay_failure_code(result: ReplayValidationResult) -> str | None:
    """Map a local replay validation result to a canonical failure code."""

    return canonical_replay_failure_code_for_local_result(result.code, result.detail)

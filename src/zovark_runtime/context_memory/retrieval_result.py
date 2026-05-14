"""Semantic validation for Context Compaction Memory retrieval results."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from .errors import RangeValidationError, RetrievalResultValidationError
from .ranges import validate_ranges


ALLOWED_KEYS = frozenset(
    {
        "result_version",
        "retrieval_result_id",
        "retrieval_request_id",
        "memory_ref_id",
        "status",
        "returned_ranges",
        "returned_byte_count",
        "hash_algorithm",
        "result_hash",
        "audit_ref",
        "model_visible",
        "model_visible_excerpt",
        "redaction_policy_ref",
        "data_unavailable_reason",
    }
)
REQUIRED_BASE_KEYS = ("status", "model_visible", "returned_ranges", "returned_byte_count")
VISIBLE_STATUSES = frozenset({"fulfilled", "partial"})
FAILURE_STATUS_REASONS = {
    "denied": frozenset({"access_denied", "policy_disallowed"}),
    "not_found": frozenset({"memory_not_found"}),
    "range_invalid": frozenset({"range_invalid"}),
    "unavailable": frozenset({"content_not_exported", "not_applicable"}),
}
VALID_STATUSES = VISIBLE_STATUSES | frozenset(FAILURE_STATUS_REASONS)


def _raise(message: str) -> None:
    raise RetrievalResultValidationError(message)


def _require_mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        _raise("retrieval result must be a mapping")
    return value


def _require_int(value: object, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _raise(f"{label} must be an integer")
    return value


def _require_ranges(value: object) -> Sequence[Mapping[str, object]]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        _raise("returned_ranges must be a sequence of range mappings")
    return value


def _validate_ranges(
    ranges: Sequence[Mapping[str, object]],
    *,
    require_non_empty: bool,
) -> None:
    try:
        validate_ranges(ranges, require_non_empty=require_non_empty)
    except RangeValidationError as exc:
        raise RetrievalResultValidationError(f"invalid returned_ranges: {exc}") from exc


def _require_non_empty_string(value: object, *, label: str) -> str:
    if not isinstance(value, str) or value == "":
        _raise(f"{label} must be a non-empty string")
    return value


def _validate_visible_result(
    result: Mapping[str, object],
    *,
    status: str,
    model_visible: bool,
    returned_ranges: Sequence[Mapping[str, object]],
    returned_byte_count: int,
) -> None:
    if status in VISIBLE_STATUSES and model_visible is not True:
        _raise(f"{status} retrieval result must be model_visible")
    if model_visible is True or status in VISIBLE_STATUSES:
        _validate_ranges(returned_ranges, require_non_empty=True)
        if returned_byte_count < 1:
            _raise("model-visible retrieval result requires returned_byte_count >= 1")
        if "model_visible_excerpt" not in result:
            _raise("model-visible retrieval result requires model_visible_excerpt")
        _require_non_empty_string(
            result["model_visible_excerpt"],
            label="model_visible_excerpt",
        )


def _validate_failure_result(
    result: Mapping[str, object],
    *,
    status: str,
    model_visible: bool,
    returned_ranges: Sequence[Mapping[str, object]],
    returned_byte_count: int,
) -> None:
    if status not in FAILURE_STATUS_REASONS:
        return
    if model_visible is not False:
        _raise(f"{status} retrieval result must not be model_visible")
    if list(returned_ranges) != []:
        _raise(f"{status} retrieval result must have empty returned_ranges")
    if returned_byte_count != 0:
        _raise(f"{status} retrieval result must have returned_byte_count == 0")
    if result.get("model_visible_excerpt") is not None:
        _raise(f"{status} retrieval result must not carry model_visible_excerpt")
    if "data_unavailable_reason" not in result:
        _raise(f"{status} retrieval result requires data_unavailable_reason")
    reason = _require_non_empty_string(
        result["data_unavailable_reason"],
        label="data_unavailable_reason",
    )
    if reason not in FAILURE_STATUS_REASONS[status]:
        allowed = ", ".join(sorted(FAILURE_STATUS_REASONS[status]))
        _raise(f"{status} data_unavailable_reason must be one of: {allowed}")


def validate_retrieval_result(result: Mapping[str, object]) -> None:
    """Validate one retrieval-result object.

    Invalid retrieval results raise :class:`RetrievalResultValidationError`.
    The validator does not coerce types and rejects unknown top-level keys.
    """

    result_mapping = _require_mapping(result)
    unknown_keys = set(result_mapping) - ALLOWED_KEYS
    if unknown_keys:
        joined = ", ".join(str(key) for key in sorted(unknown_keys, key=str))
        _raise(f"retrieval result has unknown properties: {joined}")

    missing_keys = [key for key in REQUIRED_BASE_KEYS if key not in result_mapping]
    if missing_keys:
        joined = ", ".join(missing_keys)
        _raise(f"retrieval result is missing required properties: {joined}")

    status = result_mapping["status"]
    if not isinstance(status, str):
        _raise("status must be a string")
    if status not in VALID_STATUSES:
        _raise("status must be fulfilled, partial, denied, not_found, range_invalid, or unavailable")

    model_visible = result_mapping["model_visible"]
    if not isinstance(model_visible, bool):
        _raise("model_visible must be a boolean")

    returned_ranges = _require_ranges(result_mapping["returned_ranges"])
    returned_byte_count = _require_int(
        result_mapping["returned_byte_count"],
        label="returned_byte_count",
    )
    if returned_byte_count < 0:
        _raise("returned_byte_count must be >= 0")

    _validate_visible_result(
        result_mapping,
        status=status,
        model_visible=model_visible,
        returned_ranges=returned_ranges,
        returned_byte_count=returned_byte_count,
    )
    _validate_failure_result(
        result_mapping,
        status=status,
        model_visible=model_visible,
        returned_ranges=returned_ranges,
        returned_byte_count=returned_byte_count,
    )

"""Semantic validation for Context Compaction Memory ranges."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from .errors import RangeValidationError


BYTE_RANGE_KEYS = frozenset({"range_type", "start", "end"})
LINE_RANGE_KEYS = frozenset({"range_type", "start_line", "end_line"})
RECORD_RANGE_KEYS = frozenset({"range_type", "record_id", "record_index"})


def _require_mapping(value: object, *, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise RangeValidationError(f"{label} must be a mapping")
    return value


def _require_exact_keys(
    range_obj: Mapping[str, object],
    *,
    allowed_keys: frozenset[str],
    label: str,
) -> None:
    unknown_keys = set(range_obj) - allowed_keys
    if unknown_keys:
        joined = ", ".join(str(key) for key in sorted(unknown_keys, key=str))
        raise RangeValidationError(f"{label} has unknown properties: {joined}")


def _require_required_keys(
    range_obj: Mapping[str, object],
    *,
    required_keys: tuple[str, ...],
    label: str,
) -> None:
    missing_keys = [key for key in required_keys if key not in range_obj]
    if missing_keys:
        joined = ", ".join(missing_keys)
        raise RangeValidationError(f"{label} is missing required properties: {joined}")


def _require_int(value: object, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RangeValidationError(f"{label} must be an integer")
    return value


def _validate_byte_range(range_obj: Mapping[str, object]) -> None:
    _require_exact_keys(range_obj, allowed_keys=BYTE_RANGE_KEYS, label="byte range")
    _require_required_keys(range_obj, required_keys=("start", "end"), label="byte range")
    start = _require_int(range_obj["start"], label="byte start")
    end = _require_int(range_obj["end"], label="byte end")
    if start < 0:
        raise RangeValidationError("byte start must be >= 0")
    if end < 0:
        raise RangeValidationError("byte end must be >= 0")
    if end <= start:
        raise RangeValidationError("byte range uses [start, end) semantics and requires end > start")


def _validate_line_range(range_obj: Mapping[str, object]) -> None:
    _require_exact_keys(range_obj, allowed_keys=LINE_RANGE_KEYS, label="line range")
    _require_required_keys(
        range_obj,
        required_keys=("start_line", "end_line"),
        label="line range",
    )
    start_line = _require_int(range_obj["start_line"], label="line start_line")
    end_line = _require_int(range_obj["end_line"], label="line end_line")
    if start_line < 1:
        raise RangeValidationError("line start_line must be >= 1")
    if end_line < 1:
        raise RangeValidationError("line end_line must be >= 1")
    if end_line < start_line:
        raise RangeValidationError("line range is inclusive and requires end_line >= start_line")


def _validate_record_range(range_obj: Mapping[str, object]) -> None:
    _require_exact_keys(range_obj, allowed_keys=RECORD_RANGE_KEYS, label="record range")
    has_record_id = "record_id" in range_obj
    has_record_index = "record_index" in range_obj
    if has_record_id == has_record_index:
        raise RangeValidationError("record range requires exactly one of record_id or record_index")
    if has_record_id:
        record_id = range_obj["record_id"]
        if not isinstance(record_id, str) or record_id == "":
            raise RangeValidationError("record_id must be a non-empty string")
    if has_record_index:
        record_index = _require_int(range_obj["record_index"], label="record_index")
        if record_index < 0:
            raise RangeValidationError("record_index must be >= 0")


def validate_range(range_obj: Mapping[str, object]) -> None:
    """Validate one range object.

    Invalid ranges raise :class:`RangeValidationError`. The validator does not
    coerce types.
    """

    range_mapping = _require_mapping(range_obj, label="range")
    if "range_type" not in range_mapping:
        raise RangeValidationError("range is missing range_type")

    range_type = range_mapping["range_type"]
    if range_type == "byte":
        _validate_byte_range(range_mapping)
        return
    if range_type == "line":
        _validate_line_range(range_mapping)
        return
    if range_type == "record":
        _validate_record_range(range_mapping)
        return

    raise RangeValidationError("range_type must be byte, line, or record")


def validate_ranges(
    ranges: Sequence[Mapping[str, object]],
    *,
    require_non_empty: bool,
) -> None:
    """Validate a sequence of ranges."""

    if isinstance(ranges, (str, bytes)) or not isinstance(ranges, Sequence):
        raise RangeValidationError("ranges must be a sequence of range mappings")
    if require_non_empty and len(ranges) == 0:
        raise RangeValidationError("ranges must be non-empty")
    for range_obj in ranges:
        validate_range(range_obj)

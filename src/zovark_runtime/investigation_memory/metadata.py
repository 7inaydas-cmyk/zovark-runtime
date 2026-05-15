"""Validated metadata for lossless investigation_memory objects."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from .errors import MemoryObjectValidationError
from .identity import (
    build_memory_ref_id,
    validate_memory_ref_component,
    validate_memory_ref_id,
    validate_safe_ref,
    validate_sha256_hex,
)


CONTENT_ENCODINGS = frozenset({"bytes", "utf-8", "json-lines", "json-records", "unknown"})


def _require_non_negative_int(value: object, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise MemoryObjectValidationError(f"{label} must be an integer")
    if value < 0:
        raise MemoryObjectValidationError(f"{label} must be >= 0")
    return value


def _require_optional_bool(value: object, *, label: str) -> bool:
    if not isinstance(value, bool):
        raise MemoryObjectValidationError(f"{label} must be a boolean")
    return value


def _validate_optional_ref(value: object, *, label: str) -> str | None:
    if value is None:
        return None
    return validate_safe_ref(value, label=label)


def _validate_optional_hash(value: object, *, label: str) -> str | None:
    if value is None:
        return None
    return validate_sha256_hex(value, label=label)


@dataclass(frozen=True)
class MemoryObjectMetadata:
    """Metadata for one immutable lossless memory object.

    The metadata intentionally contains no host-local absolute path or
    wall-clock timestamp fields.
    """

    memory_ref_id: str
    investigation_id: str
    source_tool_call_ref: str
    content_hash: str
    content_size_bytes: int
    content_encoding: str
    source_capability_ref: str | None = None
    source_input_hash: str | None = None
    source_output_hash: str | None = None
    execution_status: str | None = None
    trace_ref: str | None = None
    line_range_index_available: bool = False
    record_range_index_available: bool = False

    def __post_init__(self) -> None:
        validate_memory_ref_id(self.memory_ref_id)
        validate_memory_ref_component(self.investigation_id, label="investigation_id")
        validate_memory_ref_component(self.source_tool_call_ref, label="source_tool_call_ref")
        validate_sha256_hex(self.content_hash)
        _require_non_negative_int(self.content_size_bytes, label="content_size_bytes")
        if self.content_encoding not in CONTENT_ENCODINGS:
            allowed = ", ".join(sorted(CONTENT_ENCODINGS))
            raise MemoryObjectValidationError(f"content_encoding must be one of: {allowed}")

        _validate_optional_ref(self.source_capability_ref, label="source_capability_ref")
        _validate_optional_hash(self.source_input_hash, label="source_input_hash")
        _validate_optional_hash(self.source_output_hash, label="source_output_hash")
        _validate_optional_ref(self.execution_status, label="execution_status")
        _validate_optional_ref(self.trace_ref, label="trace_ref")
        _require_optional_bool(
            self.line_range_index_available,
            label="line_range_index_available",
        )
        _require_optional_bool(
            self.record_range_index_available,
            label="record_range_index_available",
        )

        expected_ref = build_memory_ref_id(
            investigation_id=self.investigation_id,
            source_tool_call_ref=self.source_tool_call_ref,
            content_hash=self.content_hash,
        )
        if self.memory_ref_id != expected_ref:
            raise MemoryObjectValidationError("memory_ref_id does not match metadata identity")

    def to_dict(self) -> dict[str, object]:
        """Return deterministic JSON-ready metadata."""

        return dict(sorted(asdict(self).items()))

    def to_json(self) -> str:
        """Serialize metadata with stable key ordering."""

        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryObjectMetadata":
        """Build metadata from a JSON object and validate it."""

        allowed_keys = set(cls.__dataclass_fields__)
        unknown_keys = set(data) - allowed_keys
        if unknown_keys:
            joined = ", ".join(sorted(unknown_keys))
            raise MemoryObjectValidationError(f"metadata has unknown properties: {joined}")
        try:
            return cls(**data)
        except TypeError as exc:
            raise MemoryObjectValidationError(f"metadata is missing required properties: {exc}") from exc

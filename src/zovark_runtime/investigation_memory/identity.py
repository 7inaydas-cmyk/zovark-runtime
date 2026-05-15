"""Deterministic identity helpers for investigation_memory objects."""

from __future__ import annotations

import hashlib
import re

from .errors import MemoryObjectValidationError


SAFE_REF_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,160}$")
MEMORY_REF_COMPONENT_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
MEMORY_REF_ID_PATTERN = re.compile(
    r"^mem:v1:[A-Za-z0-9._-]{1,128}:[A-Za-z0-9._-]{1,128}:sha256:[0-9a-f]{64}$"
)
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def sha256_hex(content: bytes) -> str:
    """Return the lowercase SHA-256 hash for exact bytes."""

    if not isinstance(content, bytes):
        raise MemoryObjectValidationError("content must be bytes")
    return hashlib.sha256(content).hexdigest()


def validate_sha256_hex(value: object, *, label: str = "content_hash") -> str:
    """Validate a lowercase SHA-256 hex string."""

    if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
        raise MemoryObjectValidationError(f"{label} must be lowercase 64-character SHA-256 hex")
    return value


def validate_safe_ref(value: object, *, label: str) -> str:
    """Validate a contract-safe reference string."""

    if not isinstance(value, str) or SAFE_REF_PATTERN.fullmatch(value) is None:
        raise MemoryObjectValidationError(f"{label} must match ^[A-Za-z0-9._:-]{{1,160}}$")
    return value


def validate_memory_ref_component(value: object, *, label: str) -> str:
    """Validate a reference component safe for colon-delimited memory_ref_id."""

    if not isinstance(value, str) or MEMORY_REF_COMPONENT_PATTERN.fullmatch(value) is None:
        raise MemoryObjectValidationError(f"{label} must match ^[A-Za-z0-9._-]{{1,128}}$")
    return value


def validate_memory_ref_id(value: object) -> str:
    """Validate a contract-compatible memory_ref_id."""

    if not isinstance(value, str) or MEMORY_REF_ID_PATTERN.fullmatch(value) is None:
        raise MemoryObjectValidationError("memory_ref_id has invalid format")
    return value


def build_memory_ref_id(
    *,
    investigation_id: str,
    source_tool_call_ref: str,
    content_hash: str,
) -> str:
    """Build deterministic memory object identity.

    The memory ref is not an authorization token.
    """

    investigation = validate_memory_ref_component(investigation_id, label="investigation_id")
    tool_call = validate_memory_ref_component(source_tool_call_ref, label="source_tool_call_ref")
    digest = validate_sha256_hex(content_hash)
    return f"mem:v1:{investigation}:{tool_call}:sha256:{digest}"

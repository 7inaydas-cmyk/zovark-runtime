"""Static sample loading and evidence normalization for Slice 001."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from zovark_runtime.proof_package import ZovarkValidationError
from zovark_runtime.proof_package.hashing import sha256_of_obj, sha256_of_string


_EVENT_COLLECTIONS = (
    ("process_events", "process_event"),
    ("network_events", "network_event"),
    ("network_flows", "network_flow"),
    ("credential_access_events", "credential_access"),
    ("lateral_movement_events", "lateral_movement_attempt"),
)
_EVENT_ARRAY_KEYS = {key for key, _source_type in _EVENT_COLLECTIONS}
_TIMESTAMP_KEYS = (
    "ingested_at",
    "observed_at",
    "event_time",
    "timestamp",
    "created_at",
)


def load_sample(path: str | Path) -> dict[str, Any]:
    """Load a static EDR-style JSON sample from disk."""
    sample_path = Path(path)
    try:
        raw = sample_path.read_text(encoding="utf-8")
        parsed = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise ZovarkValidationError(f"invalid Slice 001 sample: {sample_path}") from exc

    if not isinstance(parsed, dict):
        raise ZovarkValidationError("Slice 001 sample must be a JSON object")
    return parsed


def normalize_evidence(raw_input: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize a raw EDR-style object into deterministic evidence entries."""
    if not isinstance(raw_input, dict):
        raise ZovarkValidationError("raw input must be a JSON object")

    entries: list[dict[str, Any]] = []

    alert_object = {
        key: value for key, value in raw_input.items() if key not in _EVENT_ARRAY_KEYS
    }
    if alert_object:
        entries.append(
            _evidence_entry(
                "edr_alert",
                alert_object,
                fallback_timestamp_source=raw_input,
            )
        )

    for key, source_type in _EVENT_COLLECTIONS:
        entries.extend(
            _entries_from_array(
                raw_input,
                key,
                source_type=source_type,
                fallback_timestamp_source=raw_input,
            )
        )

    if not entries:
        raise ZovarkValidationError("raw input did not produce any evidence")
    return _dedupe_entries(entries)


def _dedupe_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop exact-duplicate evidence deterministically (first occurrence wins).

    Two events that canonicalize to the same (source_type, content) yield the same
    content-addressed evidence_id; keeping both would collide on the unique-id
    invariant. Dedup preserves input order and is a no-op when there are no duplicates,
    so single-event inputs (and the V1 fixture) are unchanged.
    """
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for entry in entries:
        evidence_id = entry["evidence_id"]
        if evidence_id in seen:
            continue
        seen.add(evidence_id)
        deduped.append(entry)
    return deduped


def _entries_from_array(
    raw_input: dict[str, Any],
    key: str,
    *,
    source_type: str,
    fallback_timestamp_source: dict[str, Any],
) -> list[dict[str, Any]]:
    if key not in raw_input:
        return []

    raw_events = raw_input[key]
    if not isinstance(raw_events, list):
        raise ZovarkValidationError(f"{key} must be a JSON array")

    entries = []
    for index, event in enumerate(raw_events):
        if not isinstance(event, dict):
            raise ZovarkValidationError(f"{key}[{index}] must be a JSON object")
        entries.append(
            _evidence_entry(
                source_type,
                event,
                fallback_timestamp_source=fallback_timestamp_source,
            )
        )
    return entries


def _evidence_entry(
    source_type: str,
    raw_content: dict[str, Any],
    *,
    fallback_timestamp_source: dict[str, Any],
) -> dict[str, Any]:
    content_hash = sha256_of_obj(raw_content)
    evidence_id = "ev-" + sha256_of_string(f"{source_type}:{content_hash}")
    ingested_at = _deterministic_timestamp(
        raw_content,
        fallback_timestamp_source=fallback_timestamp_source,
        source_type=source_type,
    )
    return {
        "evidence_id": evidence_id,
        "source_type": source_type,
        "hash": content_hash,
        "raw_content": raw_content,
        "ingested_at": ingested_at,
    }


def _deterministic_timestamp(
    source: dict[str, Any],
    *,
    fallback_timestamp_source: dict[str, Any],
    source_type: str,
) -> str:
    timestamp = _timestamp_from(source)
    if timestamp is None:
        timestamp = _timestamp_from(fallback_timestamp_source)
    if timestamp is None:
        raise ZovarkValidationError(
            f"{source_type} evidence is missing a deterministic timestamp"
        )
    return timestamp


def _timestamp_from(source: dict[str, Any]) -> str | None:
    for key in _TIMESTAMP_KEYS:
        if key not in source:
            continue
        value = source[key]
        if not isinstance(value, str) or not value:
            raise ZovarkValidationError(f"{key} must be a non-empty string")
        return value
    return None

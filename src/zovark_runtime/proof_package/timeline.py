"""Timeline construction for Slice 001 investigation tapes."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from zovark_runtime.proof_package import ZovarkValidationError


_REQUIRED_TIMELINE_EVENT_FIELDS = {
    "actor",
    "at",
    "decision_contribution",
    "event_type",
    "evidence_refs",
}
_REQUIRED_EVIDENCE_FIELDS = {
    "evidence_id",
    "source_type",
    "hash",
    "raw_content",
    "ingested_at",
}


def build_initial_timeline(tape: dict[str, Any]) -> list[dict[str, Any]]:
    """Build the initial timeline events for a recording investigation tape."""
    _validate_tape(tape)
    evidence_entries = tape["raw_evidence"]

    events = [
        _timeline_event(
            event_type="alert_received",
            at=_non_empty_string(tape, "created_at"),
            evidence_refs=[_non_empty_string(evidence_entries[0], "evidence_id")],
            decision_contribution=False,
        )
    ]

    for entry in evidence_entries:
        events.append(
            _timeline_event(
                event_type="evidence_added",
                at=_non_empty_string(entry, "ingested_at"),
                evidence_refs=[_non_empty_string(entry, "evidence_id")],
                decision_contribution=False,
            )
        )

    _validate_non_decreasing(events)
    return events


def attach_timeline(
    tape: dict[str, Any], timeline: list[dict[str, Any]]
) -> dict[str, Any]:
    """Return a copy of *tape* with *timeline* attached."""
    _validate_tape(tape)
    evidence_ids = {
        _non_empty_string(entry, "evidence_id") for entry in tape["raw_evidence"]
    }
    _validate_timeline(timeline, evidence_ids=evidence_ids)

    updated = deepcopy(tape)
    updated["timeline"] = deepcopy(timeline)
    return updated


def _timeline_event(
    *,
    event_type: str,
    at: str,
    evidence_refs: list[str],
    decision_contribution: bool,
) -> dict[str, Any]:
    return {
        "actor": "system",
        "at": at,
        "decision_contribution": decision_contribution,
        "event_type": event_type,
        "evidence_refs": evidence_refs,
    }


def _validate_tape(tape: dict[str, Any]) -> None:
    if not isinstance(tape, dict):
        raise ZovarkValidationError("tape must be an object")
    if "created_at" not in tape:
        raise ZovarkValidationError("tape is missing created_at")
    if "raw_evidence" not in tape:
        raise ZovarkValidationError("tape is missing raw_evidence")

    raw_evidence = tape["raw_evidence"]
    if not isinstance(raw_evidence, list):
        raise ZovarkValidationError("tape.raw_evidence must be a list")
    if not raw_evidence:
        raise ZovarkValidationError("tape.raw_evidence must not be empty")

    _non_empty_string(tape, "created_at")
    for index, entry in enumerate(raw_evidence):
        if not isinstance(entry, dict):
            raise ZovarkValidationError(f"tape.raw_evidence[{index}] must be an object")
        if set(entry) != _REQUIRED_EVIDENCE_FIELDS:
            raise ZovarkValidationError(
                f"tape.raw_evidence[{index}] does not match the Slice 001 evidence shape"
            )
        _non_empty_string(entry, "evidence_id")
        _non_empty_string(entry, "source_type")
        _non_empty_string(entry, "hash")
        _non_empty_string(entry, "ingested_at")
        if not isinstance(entry["raw_content"], dict):
            raise ZovarkValidationError(
                f"tape.raw_evidence[{index}].raw_content must be an object"
            )


def _validate_timeline(
    timeline: list[dict[str, Any]], *, evidence_ids: set[str]
) -> None:
    if not isinstance(timeline, list):
        raise ZovarkValidationError("timeline must be a list")
    if not timeline:
        raise ZovarkValidationError("timeline must not be empty")

    for index, event in enumerate(timeline):
        if not isinstance(event, dict):
            raise ZovarkValidationError(f"timeline[{index}] must be an object")
        if set(event) != _REQUIRED_TIMELINE_EVENT_FIELDS:
            raise ZovarkValidationError(
                f"timeline[{index}] does not match the Slice 001 timeline shape"
            )
        if event["actor"] != "system":
            raise ZovarkValidationError(f"timeline[{index}].actor must be system")
        _non_empty_string(event, "at")
        _non_empty_string(event, "event_type")
        if not isinstance(event["decision_contribution"], bool):
            raise ZovarkValidationError(
                f"timeline[{index}].decision_contribution must be boolean"
            )
        if not isinstance(event["evidence_refs"], list):
            raise ZovarkValidationError(f"timeline[{index}].evidence_refs must be a list")
        for ref_index, evidence_ref in enumerate(event["evidence_refs"]):
            if not isinstance(evidence_ref, str) or not evidence_ref:
                raise ZovarkValidationError(
                    f"timeline[{index}].evidence_refs[{ref_index}] must be a non-empty string"
                )
            if evidence_ref not in evidence_ids:
                raise ZovarkValidationError(
                    f"timeline[{index}].evidence_refs[{ref_index}] is not present in raw_evidence"
                )

    _validate_non_decreasing(timeline)


def _validate_non_decreasing(events: list[dict[str, Any]]) -> None:
    previous_at: str | None = None
    for index, event in enumerate(events):
        at = _non_empty_string(event, "at")
        if previous_at is not None and at < previous_at:
            raise ZovarkValidationError(
                f"timeline[{index}] timestamp is earlier than the previous event"
            )
        previous_at = at


def _non_empty_string(source: dict[str, Any], key: str) -> str:
    value = source.get(key)
    if not isinstance(value, str) or not value:
        raise ZovarkValidationError(f"{key} must be a non-empty string")
    return value

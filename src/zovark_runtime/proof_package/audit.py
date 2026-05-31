"""Audit-chain close entry construction for Slice 001."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from zovark_runtime.proof_package import ZovarkValidationError
from zovark_runtime.proof_package.handoff import derive_handoff
from zovark_runtime.proof_package.hashing import sha256_of_obj, sha256_of_string
from zovark_runtime.proof_package.verdict import derive_verdict


GENESIS_HASH = sha256_of_string("genesis")
_EVENT_TYPE = "tape_recording_closed"
_REQUIRED_AUDIT_FIELDS = {
    "created_at",
    "entry_id",
    "event_type",
    "payload",
    "prev_entry_hash",
    "sequence",
    "signed_root",
    "tenant_id",
    "this_entry_hash",
}
_REQUIRED_PAYLOAD_FIELDS = {
    "fields_hash",
    "tape_id",
    "verdict_value",
}
_REQUIRED_EVIDENCE_FIELDS = {
    "evidence_id",
    "source_type",
    "hash",
    "raw_content",
    "ingested_at",
}
_REQUIRED_TIMELINE_EVENT_FIELDS = {
    "actor",
    "at",
    "decision_contribution",
    "event_type",
    "evidence_refs",
}


def derive_audit_entry(tape: dict[str, Any]) -> dict[str, Any]:
    """Derive the Slice 001 tape-close audit chain entry."""
    return build_close_entry(tape, sequence=1, prev_hash=GENESIS_HASH)


def build_audit_entry(tape: dict[str, Any]) -> dict[str, Any]:
    """Task-compatible wrapper for deriving the close audit entry."""
    return derive_audit_entry(tape)


def build_close_entry(
    tape: dict[str, Any],
    sequence: int = 1,
    prev_hash: str = GENESIS_HASH,
) -> dict[str, Any]:
    """Construct a deterministic ``tape_recording_closed`` audit chain entry."""
    _validate_tape(tape)
    _validate_sequence(sequence)
    if not isinstance(prev_hash, str) or not prev_hash:
        raise ZovarkValidationError("prev_hash must be a non-empty string")
    if sequence == 1 and prev_hash != GENESIS_HASH:
        raise ZovarkValidationError("first audit entry must anchor to genesis")

    entry_id = _entry_id(sequence)
    audit_ref = tape.get("audit_ref")
    if audit_ref is not None and audit_ref != entry_id:
        raise ZovarkValidationError("tape.audit_ref does not match audit entry id")

    entry = {
        "created_at": _audit_created_at(tape),
        "entry_id": entry_id,
        "event_type": _EVENT_TYPE,
        "payload": {
            "fields_hash": _fields_hash(tape),
            "tape_id": tape["tape_id"],
            "verdict_value": tape["verdict"]["value"],
        },
        "prev_entry_hash": prev_hash,
        "sequence": sequence,
        "signed_root": None,
        "tenant_id": tape["tenant_id"],
        "this_entry_hash": "",
    }
    entry["this_entry_hash"] = compute_this_entry_hash(entry)
    _validate_audit_entry(entry, tape=tape, sequence=sequence, prev_hash=prev_hash)
    return entry


def compute_this_entry_hash(entry: dict[str, Any]) -> str:
    """Hash an audit entry with ``this_entry_hash`` blanked."""
    if not isinstance(entry, dict):
        raise ZovarkValidationError("audit entry must be an object")
    entry_for_hash = deepcopy(entry)
    entry_for_hash["this_entry_hash"] = ""
    return sha256_of_obj(entry_for_hash)


def attach_audit_entry(
    tape: dict[str, Any],
    audit_entry: dict[str, Any],
) -> dict[str, Any]:
    """Return a sealed copy of *tape* with the exact derived audit entry attached."""
    expected_entry = derive_audit_entry(tape)
    _validate_audit_entry(audit_entry, tape=tape)
    if audit_entry != expected_entry:
        raise ZovarkValidationError("audit entry does not match derived tape audit entry")

    updated = deepcopy(tape)
    updated["audit_entry"] = deepcopy(audit_entry)
    updated["audit_ref"] = audit_entry["entry_id"]
    updated["state"] = "closed"
    return updated


def set_audit_entry(
    tape: dict[str, Any],
    audit_entry: dict[str, Any],
) -> dict[str, Any]:
    """Alias for attaching the derived audit entry to a copied tape."""
    return attach_audit_entry(tape, audit_entry)


def _validate_tape(tape: dict[str, Any]) -> None:
    if not isinstance(tape, dict):
        raise ZovarkValidationError("tape must be an object")
    for key in (
        "tape_id",
        "tenant_id",
        "schema_version",
        "source_alert_ref",
        "created_at",
    ):
        _non_empty_string(tape, key)
    for key in ("raw_evidence", "timeline", "findings", "verdict", "handoff"):
        if key not in tape:
            raise ZovarkValidationError(f"tape is missing {key}")

    _validate_evidence_entries(tape["raw_evidence"])
    evidence_ids = {entry["evidence_id"] for entry in tape["raw_evidence"]}
    _validate_timeline(tape["timeline"], evidence_ids=evidence_ids)
    _validate_findings(
        tape["findings"],
        evidence_ids=evidence_ids,
        no_findings_flag=tape.get("no_findings_flag", False),
    )

    if not isinstance(tape["verdict"], dict):
        raise ZovarkValidationError("tape.verdict must be an object")
    expected_verdict = derive_verdict(tape)
    if tape["verdict"] != expected_verdict:
        raise ZovarkValidationError("tape.verdict does not match derived verdict")

    if not isinstance(tape["handoff"], dict):
        raise ZovarkValidationError("tape.handoff must be an object")
    expected_handoff = derive_handoff(tape)
    if tape["handoff"] != expected_handoff:
        raise ZovarkValidationError("tape.handoff does not match derived handoff")


def _validate_evidence_entries(evidence_entries: list[dict[str, Any]]) -> None:
    if not isinstance(evidence_entries, list):
        raise ZovarkValidationError("tape.raw_evidence must be a list")
    if not evidence_entries:
        raise ZovarkValidationError("tape.raw_evidence must not be empty")

    seen_ids: set[str] = set()
    for index, entry in enumerate(evidence_entries):
        if not isinstance(entry, dict):
            raise ZovarkValidationError(f"tape.raw_evidence[{index}] must be an object")
        if set(entry) != _REQUIRED_EVIDENCE_FIELDS:
            raise ZovarkValidationError(
                f"tape.raw_evidence[{index}] does not match the Slice 001 evidence shape"
            )
        for key in ("evidence_id", "source_type", "hash", "ingested_at"):
            _non_empty_string(entry, key)
        if entry["evidence_id"] in seen_ids:
            raise ZovarkValidationError(
                f"tape.raw_evidence[{index}].evidence_id must be unique"
            )
        seen_ids.add(entry["evidence_id"])
        if not isinstance(entry["raw_content"], dict):
            raise ZovarkValidationError(
                f"tape.raw_evidence[{index}].raw_content must be an object"
            )


def _validate_timeline(
    timeline: list[dict[str, Any]],
    *,
    evidence_ids: set[str],
) -> None:
    if not isinstance(timeline, list):
        raise ZovarkValidationError("tape.timeline must be a list")
    if not timeline:
        raise ZovarkValidationError("tape.timeline must not be empty")

    previous_at: str | None = None
    for index, event in enumerate(timeline):
        if not isinstance(event, dict):
            raise ZovarkValidationError(f"tape.timeline[{index}] must be an object")
        if set(event) != _REQUIRED_TIMELINE_EVENT_FIELDS:
            raise ZovarkValidationError(
                f"tape.timeline[{index}] does not match the Slice 001 timeline shape"
            )
        at = _non_empty_string(event, "at")
        if previous_at is not None and at < previous_at:
            raise ZovarkValidationError(
                f"tape.timeline[{index}] timestamp is earlier than the previous event"
            )
        previous_at = at
        _non_empty_string(event, "actor")
        _non_empty_string(event, "event_type")
        if not isinstance(event["decision_contribution"], bool):
            raise ZovarkValidationError(
                f"tape.timeline[{index}].decision_contribution must be boolean"
            )
        refs = event["evidence_refs"]
        if not isinstance(refs, list):
            raise ZovarkValidationError(
                f"tape.timeline[{index}].evidence_refs must be a list"
            )
        for ref_index, evidence_ref in enumerate(refs):
            if not isinstance(evidence_ref, str) or not evidence_ref:
                raise ZovarkValidationError(
                    f"tape.timeline[{index}].evidence_refs[{ref_index}] must be a non-empty string"
                )
            if evidence_ref not in evidence_ids:
                raise ZovarkValidationError(
                    f"tape.timeline[{index}].evidence_refs[{ref_index}] is not present in raw_evidence"
                )


def _validate_findings(
    findings: list[dict[str, Any]],
    *,
    evidence_ids: set[str],
    no_findings_flag: Any,
) -> None:
    if not isinstance(no_findings_flag, bool):
        raise ZovarkValidationError("no_findings_flag must be boolean")
    if not isinstance(findings, list):
        raise ZovarkValidationError("tape.findings must be a list")
    if not findings and not no_findings_flag:
        raise ZovarkValidationError("tape.findings must not be empty")
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            raise ZovarkValidationError(f"tape.findings[{index}] must be an object")
        if finding.get("model_contribution") is not False:
            raise ZovarkValidationError(
                f"tape.findings[{index}].model_contribution must be false"
            )
        refs = finding.get("evidence_refs")
        if not isinstance(refs, list):
            raise ZovarkValidationError(
                f"tape.findings[{index}].evidence_refs must be a list"
            )
        for ref_index, evidence_ref in enumerate(refs):
            if not isinstance(evidence_ref, str) or not evidence_ref:
                raise ZovarkValidationError(
                    f"tape.findings[{index}].evidence_refs[{ref_index}] must be a non-empty string"
                )
            if evidence_ref not in evidence_ids:
                raise ZovarkValidationError(
                    f"tape.findings[{index}].evidence_refs[{ref_index}] is not present in raw_evidence"
                )


def _validate_audit_entry(
    audit_entry: dict[str, Any],
    *,
    tape: dict[str, Any],
    sequence: int | None = None,
    prev_hash: str | None = None,
) -> None:
    if not isinstance(audit_entry, dict):
        raise ZovarkValidationError("audit entry must be an object")
    if set(audit_entry) != _REQUIRED_AUDIT_FIELDS:
        raise ZovarkValidationError("audit entry does not match the Slice 001 shape")

    resolved_sequence = sequence if sequence is not None else audit_entry["sequence"]
    _validate_sequence(resolved_sequence)
    if audit_entry["sequence"] != resolved_sequence:
        raise ZovarkValidationError("audit entry sequence is invalid")
    if audit_entry["entry_id"] != _entry_id(resolved_sequence):
        raise ZovarkValidationError("audit entry id is invalid")
    if resolved_sequence == 1 and audit_entry["prev_entry_hash"] != GENESIS_HASH:
        raise ZovarkValidationError("first audit entry must anchor to genesis")
    if audit_entry["event_type"] != _EVENT_TYPE:
        raise ZovarkValidationError("audit entry event_type is invalid")
    if audit_entry["tenant_id"] != tape["tenant_id"]:
        raise ZovarkValidationError("audit entry tenant_id must match tape")
    expected_prev = prev_hash if prev_hash is not None else audit_entry["prev_entry_hash"]
    if audit_entry["prev_entry_hash"] != expected_prev:
        raise ZovarkValidationError("audit entry prev_entry_hash is invalid")
    _non_empty_string(audit_entry, "created_at")
    if audit_entry["signed_root"] is not None:
        raise ZovarkValidationError("audit entry signed_root must be null in Slice 001")

    payload = audit_entry["payload"]
    if not isinstance(payload, dict):
        raise ZovarkValidationError("audit entry payload must be an object")
    if set(payload) != _REQUIRED_PAYLOAD_FIELDS:
        raise ZovarkValidationError("audit entry payload shape is invalid")
    if payload["tape_id"] != tape["tape_id"]:
        raise ZovarkValidationError("audit entry payload tape_id is invalid")
    if payload["verdict_value"] != tape["verdict"]["value"]:
        raise ZovarkValidationError("audit entry payload verdict_value is invalid")
    if payload["fields_hash"] != _fields_hash(tape):
        raise ZovarkValidationError("audit entry payload fields_hash is invalid")
    if audit_entry["this_entry_hash"] != compute_this_entry_hash(audit_entry):
        raise ZovarkValidationError("audit entry this_entry_hash is invalid")


def _fields_hash(tape: dict[str, Any]) -> str:
    return sha256_of_obj(
        {
            "findings": tape["findings"],
            "raw_evidence": tape["raw_evidence"],
            "schema_version": tape["schema_version"],
            "source_alert_ref": tape["source_alert_ref"],
            "tape_id": tape["tape_id"],
            "tenant_id": tape["tenant_id"],
            "verdict_value": tape["verdict"]["value"],
        }
    )


def _audit_created_at(tape: dict[str, Any]) -> str:
    for event in tape["timeline"]:
        if event.get("event_type") == "audit_signed":
            return _non_empty_string(event, "at")
    verdict = tape["verdict"]
    if isinstance(verdict, dict) and isinstance(verdict.get("set_at"), str):
        return _increment_iso8601_seconds(verdict["set_at"], 2)
    return _increment_iso8601_seconds(_non_empty_string(tape, "created_at"), 3)


def _entry_id(sequence: int) -> str:
    return f"audit-entry-{sequence}"


def _validate_sequence(sequence: int) -> None:
    if not isinstance(sequence, int) or sequence < 1:
        raise ZovarkValidationError("audit entry sequence must be a positive integer")


def _increment_iso8601_seconds(timestamp: str, seconds_to_add: int) -> str:
    if not isinstance(seconds_to_add, int) or seconds_to_add < 0:
        raise ZovarkValidationError("seconds_to_add must be a non-negative integer")
    year, month, day, hour, minute, second = _parse_iso8601_utc(timestamp)
    for _ in range(seconds_to_add):
        second += 1
        if second == 60:
            second = 0
            minute += 1
        if minute == 60:
            minute = 0
            hour += 1
        if hour == 24:
            hour = 0
            day += 1
        if day > _days_in_month(year, month):
            day = 1
            month += 1
        if month == 13:
            month = 1
            year += 1
    return f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}Z"


def _parse_iso8601_utc(timestamp: str) -> tuple[int, int, int, int, int, int]:
    if len(timestamp) != 20 or timestamp[4] != "-" or timestamp[7] != "-":
        raise ZovarkValidationError("timestamp must be ISO-8601 UTC")
    if timestamp[10] != "T" or timestamp[13] != ":" or timestamp[16] != ":":
        raise ZovarkValidationError("timestamp must be ISO-8601 UTC")
    if timestamp[19] != "Z":
        raise ZovarkValidationError("timestamp must be ISO-8601 UTC")
    try:
        year = int(timestamp[0:4])
        month = int(timestamp[5:7])
        day = int(timestamp[8:10])
        hour = int(timestamp[11:13])
        minute = int(timestamp[14:16])
        second = int(timestamp[17:19])
    except ValueError as exc:
        raise ZovarkValidationError("timestamp must be ISO-8601 UTC") from exc
    max_day = _days_in_month(year, month)
    if day < 1 or day > max_day:
        raise ZovarkValidationError("timestamp day is invalid")
    if hour < 0 or hour > 23:
        raise ZovarkValidationError("timestamp hour is invalid")
    if minute < 0 or minute > 59:
        raise ZovarkValidationError("timestamp minute is invalid")
    if second < 0 or second > 59:
        raise ZovarkValidationError("timestamp second is invalid")
    return year, month, day, hour, minute, second


def _days_in_month(year: int, month: int) -> int:
    if month < 1 or month > 12:
        raise ZovarkValidationError("timestamp month is invalid")
    if month == 2:
        return 29 if _is_leap_year(year) else 28
    if month in {4, 6, 9, 11}:
        return 30
    return 31


def _is_leap_year(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _non_empty_string(source: dict[str, Any], key: str) -> str:
    value = source.get(key)
    if not isinstance(value, str) or not value:
        raise ZovarkValidationError(f"{key} must be a non-empty string")
    return value

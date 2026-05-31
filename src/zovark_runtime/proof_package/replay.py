"""Deterministic replay report construction for Slice 001."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from zovark_runtime.proof_package import ZovarkValidationError
from zovark_runtime.proof_package.audit import (
    GENESIS_HASH,
    compute_this_entry_hash,
    derive_audit_entry,
)
from zovark_runtime.proof_package.handoff import derive_handoff
from zovark_runtime.proof_package.hashing import sha256_of_obj, sha256_of_string
from zovark_runtime.proof_package.verdict import derive_verdict


REPLAY_ID = "replay-001"
_EVENT_TYPE = "tape_replayed"
_MODE = "recorded_output"
_SCHEMA_PIN = "tape/1.0"
_TOOL_CATALOG_PIN = "none-slice-001"
_REPLAY_STATUS = "succeeded"
_REQUIRED_EVIDENCE_FIELDS = {
    "evidence_id",
    "source_type",
    "hash",
    "raw_content",
    "ingested_at",
}
_REQUIRED_REPLAY_REPORT_FIELDS = {"audit_chain_entry", "replay_state"}
_REQUIRED_REPLAY_STATE_FIELDS = {
    "completed_at",
    "evidence_hashes_verified",
    "mismatch_details",
    "mode",
    "model_versions_pin",
    "no_live_edr_call",
    "no_live_llm_call",
    "replay_id",
    "replay_status",
    "schema_pin",
    "started_at",
    "state",
    "tape_ref",
    "tenant_id",
    "tool_catalog_pin",
    "unsigned_tail_replay",
    "verdict_match",
    "verdict_recomputed",
    "verification_detail",
}
_REQUIRED_VERIFICATION_DETAIL_FIELDS = {
    "evidence_entries_checked",
    "evidence_entries_failed",
    "evidence_entries_passed",
    "verdict_matched",
    "verdict_recomputed_value",
    "verdict_stored",
}
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
_REQUIRED_REPLAY_PAYLOAD_FIELDS = {
    "evidence_hashes_verified",
    "replay_id",
    "replay_state",
    "tape_id",
    "verdict_matched",
    "verdict_recomputed",
}


def derive_replay_report(tape: dict[str, Any]) -> dict[str, Any]:
    """Derive the deterministic Slice 001 replay report for a sealed tape."""
    _validate_sealed_tape(tape)
    verification_detail = _verification_detail(tape)
    replay_at = _replay_created_at(tape)
    replay_state = {
        "completed_at": replay_at,
        "evidence_hashes_verified": True,
        "mismatch_details": None,
        "mode": _MODE,
        "model_versions_pin": [],
        "no_live_edr_call": True,
        "no_live_llm_call": True,
        "replay_id": REPLAY_ID,
        "replay_status": _REPLAY_STATUS,
        "schema_pin": _SCHEMA_PIN,
        "started_at": replay_at,
        "state": _REPLAY_STATUS,
        "tape_ref": tape["tape_id"],
        "tenant_id": tape["tenant_id"],
        "tool_catalog_pin": _TOOL_CATALOG_PIN,
        "unsigned_tail_replay": True,
        "verdict_match": True,
        "verdict_recomputed": True,
        "verification_detail": verification_detail,
    }
    audit_chain_entry = _replay_audit_entry(
        tape,
        replay_at=replay_at,
        replay_state=replay_state,
    )
    report = {
        "audit_chain_entry": audit_chain_entry,
        "replay_state": replay_state,
    }
    _validate_replay_report(report, tape=tape)
    return report


def build_replay_report(tape: dict[str, Any]) -> dict[str, Any]:
    """Task-compatible wrapper for deriving the replay report."""
    return derive_replay_report(tape)


def attach_replay_report(
    tape: dict[str, Any],
    replay_report: dict[str, Any],
) -> dict[str, Any]:
    """Return a copied tape with the exact derived replay report attached."""
    expected_report = derive_replay_report(tape)
    _validate_replay_report(replay_report, tape=tape)
    if replay_report != expected_report:
        raise ZovarkValidationError(
            "replay report does not match derived tape replay report"
        )

    updated = deepcopy(tape)
    updated["replay_report"] = deepcopy(replay_report)
    return updated


def set_replay_report(
    tape: dict[str, Any],
    replay_report: dict[str, Any],
) -> dict[str, Any]:
    """Alias for attaching the derived replay report to a copied tape."""
    return attach_replay_report(tape, replay_report)


def _validate_sealed_tape(tape: dict[str, Any]) -> None:
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
    for key in (
        "raw_evidence",
        "timeline",
        "findings",
        "verdict",
        "handoff",
        "audit_entry",
    ):
        if key not in tape:
            raise ZovarkValidationError(f"tape is missing {key}")
    if tape.get("state") != "closed":
        raise ZovarkValidationError("replay requires a closed tape")

    _validate_evidence_entries(tape["raw_evidence"])
    evidence_ids = {entry["evidence_id"] for entry in tape["raw_evidence"]}
    _validate_timeline(tape["timeline"], evidence_ids=evidence_ids)
    _validate_findings(
        tape["findings"],
        evidence_ids=evidence_ids,
        no_findings_flag=tape.get("no_findings_flag", False),
    )

    expected_verdict = derive_verdict(tape)
    if tape["verdict"] != expected_verdict:
        raise ZovarkValidationError("tape.verdict does not match derived verdict")
    expected_handoff = derive_handoff(tape)
    if tape["handoff"] != expected_handoff:
        raise ZovarkValidationError("tape.handoff does not match derived handoff")
    expected_audit_entry = derive_audit_entry(tape)
    if tape["audit_entry"] != expected_audit_entry:
        raise ZovarkValidationError(
            "tape.audit_entry does not match derived audit entry"
        )
    if tape.get("audit_ref") != tape["audit_entry"]["entry_id"]:
        raise ZovarkValidationError("tape.audit_ref must match audit_entry.entry_id")


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
        expected_hash = sha256_of_obj(entry["raw_content"])
        if entry["hash"] != expected_hash:
            raise ZovarkValidationError(
                f"tape.raw_evidence[{index}].hash does not match raw_content"
            )
        expected_evidence_id = "ev-" + sha256_of_string(
            f"{entry['source_type']}:{entry['hash']}"
        )
        if entry["evidence_id"] != expected_evidence_id:
            raise ZovarkValidationError(
                f"tape.raw_evidence[{index}].evidence_id is invalid"
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
        at = _non_empty_string(event, "at")
        if previous_at is not None and at < previous_at:
            raise ZovarkValidationError(
                f"tape.timeline[{index}] timestamp is earlier than the previous event"
            )
        previous_at = at
        refs = event.get("evidence_refs")
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


def _verification_detail(tape: dict[str, Any]) -> dict[str, Any]:
    evidence_count = len(tape["raw_evidence"])
    return {
        "evidence_entries_checked": evidence_count,
        "evidence_entries_failed": 0,
        "evidence_entries_passed": evidence_count,
        "verdict_matched": True,
        "verdict_recomputed_value": tape["verdict"]["value"],
        "verdict_stored": tape["verdict"]["value"],
    }


def _replay_audit_entry(
    tape: dict[str, Any],
    *,
    replay_at: str,
    replay_state: dict[str, Any],
) -> dict[str, Any]:
    audit_entry = tape["audit_entry"]
    if audit_entry["sequence"] != 1:
        raise ZovarkValidationError("replay requires close audit entry sequence 1")
    if audit_entry["prev_entry_hash"] != GENESIS_HASH:
        raise ZovarkValidationError("close audit entry must anchor to genesis")
    entry = {
        "created_at": replay_at,
        "entry_id": "audit-entry-2",
        "event_type": _EVENT_TYPE,
        "payload": {
            "evidence_hashes_verified": True,
            "replay_id": replay_state["replay_id"],
            "replay_state": replay_state["state"],
            "tape_id": tape["tape_id"],
            "verdict_matched": True,
            "verdict_recomputed": tape["verdict"]["value"],
        },
        "prev_entry_hash": audit_entry["this_entry_hash"],
        "sequence": 2,
        "signed_root": None,
        "tenant_id": tape["tenant_id"],
        "this_entry_hash": "",
    }
    entry["this_entry_hash"] = compute_this_entry_hash(entry)
    return entry


def _validate_replay_report(
    replay_report: dict[str, Any],
    *,
    tape: dict[str, Any],
) -> None:
    if not isinstance(replay_report, dict):
        raise ZovarkValidationError("replay report must be an object")
    if set(replay_report) != _REQUIRED_REPLAY_REPORT_FIELDS:
        raise ZovarkValidationError("replay report does not match the Slice 001 shape")
    _validate_replay_state(replay_report["replay_state"], tape=tape)
    _validate_replay_audit_entry(replay_report["audit_chain_entry"], tape=tape)


def _validate_replay_state(
    replay_state: dict[str, Any],
    *,
    tape: dict[str, Any],
) -> None:
    if not isinstance(replay_state, dict):
        raise ZovarkValidationError("replay_state must be an object")
    if set(replay_state) != _REQUIRED_REPLAY_STATE_FIELDS:
        raise ZovarkValidationError("replay_state shape is invalid")
    replay_at = _replay_created_at(tape)
    if replay_state["started_at"] != replay_at:
        raise ZovarkValidationError("replay_state.started_at is invalid")
    if replay_state["completed_at"] != replay_at:
        raise ZovarkValidationError("replay_state.completed_at is invalid")
    expected = {
        "evidence_hashes_verified": True,
        "mismatch_details": None,
        "mode": _MODE,
        "model_versions_pin": [],
        "no_live_edr_call": True,
        "no_live_llm_call": True,
        "replay_id": REPLAY_ID,
        "replay_status": _REPLAY_STATUS,
        "schema_pin": _SCHEMA_PIN,
        "state": _REPLAY_STATUS,
        "tape_ref": tape["tape_id"],
        "tenant_id": tape["tenant_id"],
        "tool_catalog_pin": _TOOL_CATALOG_PIN,
        "unsigned_tail_replay": True,
        "verdict_match": True,
        "verdict_recomputed": True,
        "verification_detail": _verification_detail(tape),
    }
    for key, expected_value in expected.items():
        if replay_state[key] != expected_value:
            raise ZovarkValidationError(f"replay_state.{key} is invalid")
    if set(replay_state["verification_detail"]) != _REQUIRED_VERIFICATION_DETAIL_FIELDS:
        raise ZovarkValidationError("replay_state.verification_detail shape is invalid")


def _validate_replay_audit_entry(
    audit_entry: dict[str, Any],
    *,
    tape: dict[str, Any],
) -> None:
    if not isinstance(audit_entry, dict):
        raise ZovarkValidationError("replay audit entry must be an object")
    if set(audit_entry) != _REQUIRED_AUDIT_FIELDS:
        raise ZovarkValidationError("replay audit entry shape is invalid")
    if audit_entry["created_at"] != _replay_created_at(tape):
        raise ZovarkValidationError("replay audit entry created_at is invalid")
    if audit_entry["entry_id"] != "audit-entry-2":
        raise ZovarkValidationError("replay audit entry id is invalid")
    if audit_entry["event_type"] != _EVENT_TYPE:
        raise ZovarkValidationError("replay audit entry event_type is invalid")
    if audit_entry["prev_entry_hash"] != tape["audit_entry"]["this_entry_hash"]:
        raise ZovarkValidationError("replay audit entry prev_entry_hash is invalid")
    if audit_entry["sequence"] != 2:
        raise ZovarkValidationError("replay audit entry sequence is invalid")
    if audit_entry["signed_root"] is not None:
        raise ZovarkValidationError("replay audit entry signed_root must be null")
    if audit_entry["tenant_id"] != tape["tenant_id"]:
        raise ZovarkValidationError("replay audit entry tenant_id is invalid")
    payload = audit_entry["payload"]
    if not isinstance(payload, dict):
        raise ZovarkValidationError("replay audit entry payload must be an object")
    if set(payload) != _REQUIRED_REPLAY_PAYLOAD_FIELDS:
        raise ZovarkValidationError("replay audit entry payload shape is invalid")
    expected_payload = {
        "evidence_hashes_verified": True,
        "replay_id": REPLAY_ID,
        "replay_state": _REPLAY_STATUS,
        "tape_id": tape["tape_id"],
        "verdict_matched": True,
        "verdict_recomputed": tape["verdict"]["value"],
    }
    if payload != expected_payload:
        raise ZovarkValidationError("replay audit entry payload is invalid")
    if audit_entry["this_entry_hash"] != compute_this_entry_hash(audit_entry):
        raise ZovarkValidationError("replay audit entry this_entry_hash is invalid")


def _replay_created_at(tape: dict[str, Any]) -> str:
    return _increment_iso8601_seconds(_non_empty_string(tape["audit_entry"], "created_at"), 1)


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

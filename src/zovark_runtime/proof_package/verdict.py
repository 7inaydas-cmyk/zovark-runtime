"""Deterministic verdict derivation for Slice 001."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from zovark_runtime.proof_package import ZovarkValidationError
from zovark_runtime.proof_package.hashing import sha256_of_obj


APPROVED_VERDICTS = {
    "benign",
    "confirmed_malicious",
    "inconclusive_insufficient_evidence",
    "suspicious_unconfirmed",
}
_REQUIRED_EVIDENCE_FIELDS = {
    "evidence_id",
    "source_type",
    "hash",
    "raw_content",
    "ingested_at",
}
_REQUIRED_FINDING_FIELDS = {
    "evidence_refs",
    "model_contribution",
    "severity",
    "title",
}
_REQUIRED_VERDICT_FIELDS = {
    "derivation_rule",
    "evidence_refs",
    "highest_severity_finding",
    "model_contribution",
    "set_at",
    "signing_tag",
    "value",
}
_SEVERITY_RANK = {
    "info": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}
_DERIVATION_RULES = {
    "benign": "All findings severity low or info \u2192 benign",
    "confirmed_malicious": (
        "Any finding with severity critical or high \u2192 confirmed_malicious"
    ),
    "inconclusive_insufficient_evidence": (
        "no_findings_flag true \u2192 inconclusive_insufficient_evidence"
    ),
    "suspicious_unconfirmed": (
        "Any finding with severity medium and none high/critical "
        "\u2192 suspicious_unconfirmed"
    ),
}


def derive_verdict(tape: dict[str, Any]) -> dict[str, Any]:
    """Derive a deterministic verdict from a tape's findings."""
    if not isinstance(tape, dict):
        raise ZovarkValidationError("tape must be an object")
    if "findings" not in tape:
        raise ZovarkValidationError("tape is missing findings")
    if "raw_evidence" not in tape:
        raise ZovarkValidationError("tape is missing raw_evidence")
    return compute_verdict(tape["findings"], tape["raw_evidence"], tape)


def compute_verdict(
    findings: list[dict[str, Any]],
    evidence_entries: list[dict[str, Any]],
    tape: dict[str, Any],
) -> dict[str, Any]:
    """Compute the Slice 001 verdict from findings and evidence."""
    if not isinstance(tape, dict):
        raise ZovarkValidationError("tape must be an object")
    _validate_tape_identity(tape)
    _validate_evidence_entries(evidence_entries)
    evidence_ids = [entry["evidence_id"] for entry in evidence_entries]
    evidence_by_id = {entry["evidence_id"]: entry for entry in evidence_entries}
    no_findings_flag = tape.get("no_findings_flag", False)
    _validate_findings(
        findings,
        evidence_ids=set(evidence_ids),
        no_findings_flag=no_findings_flag,
    )

    value = _verdict_value(findings, no_findings_flag=no_findings_flag)
    _validate_verdict_value(value)
    evidence_refs = _verdict_evidence_refs(findings, evidence_ids)
    verdict = {
        "derivation_rule": _DERIVATION_RULES[value],
        "evidence_refs": evidence_refs,
        "highest_severity_finding": _highest_severity_finding(
            findings,
            evidence_by_id=evidence_by_id,
            no_findings_flag=no_findings_flag,
        ),
        "model_contribution": False,
        "set_at": _verdict_set_at(tape),
        "signing_tag": _signing_tag(
            tape,
            findings=findings,
            evidence_entries=evidence_entries,
            verdict_value=value,
        ),
        "value": value,
    }
    _validate_verdict(verdict, evidence_ids=set(evidence_ids))
    return verdict


def set_verdict(tape: dict[str, Any], verdict: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of *tape* with *verdict* set."""
    return attach_verdict(tape, verdict)


def attach_verdict(tape: dict[str, Any], verdict: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of *tape* with *verdict* attached."""
    if not isinstance(tape, dict):
        raise ZovarkValidationError("tape must be an object")
    _validate_tape_identity(tape)
    if "raw_evidence" not in tape:
        raise ZovarkValidationError("tape is missing raw_evidence")
    if "findings" not in tape:
        raise ZovarkValidationError("tape is missing findings")
    _validate_evidence_entries(tape["raw_evidence"])
    no_findings_flag = tape.get("no_findings_flag", False)
    evidence_ids = {entry["evidence_id"] for entry in tape["raw_evidence"]}
    _validate_findings(
        tape["findings"],
        evidence_ids=evidence_ids,
        no_findings_flag=no_findings_flag,
    )
    expected_verdict = compute_verdict(tape["findings"], tape["raw_evidence"], tape)
    _validate_verdict(
        verdict,
        evidence_ids=evidence_ids,
        expected_verdict=expected_verdict,
    )

    updated = deepcopy(tape)
    updated["verdict"] = deepcopy(verdict)
    return updated


def _validate_tape_identity(tape: dict[str, Any]) -> None:
    for key in (
        "tape_id",
        "tenant_id",
        "schema_version",
        "source_alert_ref",
        "created_at",
    ):
        _non_empty_string(tape, key)


def _validate_evidence_entries(evidence_entries: list[dict[str, Any]]) -> None:
    if not isinstance(evidence_entries, list):
        raise ZovarkValidationError("evidence_entries must be a list")

    seen_ids: set[str] = set()
    for index, entry in enumerate(evidence_entries):
        if not isinstance(entry, dict):
            raise ZovarkValidationError(f"evidence_entries[{index}] must be an object")
        if set(entry) != _REQUIRED_EVIDENCE_FIELDS:
            raise ZovarkValidationError(
                f"evidence_entries[{index}] does not match the Slice 001 evidence shape"
            )
        for key in ("evidence_id", "source_type", "hash", "ingested_at"):
            _non_empty_string(entry, key)
        if entry["evidence_id"] in seen_ids:
            raise ZovarkValidationError(
                f"evidence_entries[{index}].evidence_id must be unique"
            )
        seen_ids.add(entry["evidence_id"])
        if not isinstance(entry["raw_content"], dict):
            raise ZovarkValidationError(
                f"evidence_entries[{index}].raw_content must be an object"
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
        raise ZovarkValidationError("findings must be a list")
    if not findings and not no_findings_flag:
        raise ZovarkValidationError("empty findings require no_findings_flag")

    seen_rule_ids: set[str] = set()
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            raise ZovarkValidationError(f"findings[{index}] must be an object")
        if "finding_id" in finding:
            raise ZovarkValidationError("finding_id is not part of Slice 001 findings")
        if not _REQUIRED_FINDING_FIELDS.issubset(finding):
            raise ZovarkValidationError(
                f"findings[{index}] does not match the Slice 001 finding shape"
            )
        if finding["model_contribution"] is not False:
            raise ZovarkValidationError(
                f"findings[{index}].model_contribution must be false"
            )
        _non_empty_string(finding, "title")
        severity = _non_empty_string(finding, "severity")
        if severity not in _SEVERITY_RANK:
            raise ZovarkValidationError(f"findings[{index}].severity is invalid")
        if "rule_id" in finding:
            rule_id = _non_empty_string(finding, "rule_id")
            if rule_id in seen_rule_ids:
                raise ZovarkValidationError(
                    f"findings[{index}].rule_id must be unique"
                )
            seen_rule_ids.add(rule_id)

        refs = finding["evidence_refs"]
        if not isinstance(refs, list):
            raise ZovarkValidationError(
                f"findings[{index}].evidence_refs must be a list"
            )
        if not refs and not no_findings_flag:
            raise ZovarkValidationError(
                f"findings[{index}].evidence_refs must not be empty"
            )
        for ref_index, evidence_ref in enumerate(refs):
            if not isinstance(evidence_ref, str) or not evidence_ref:
                raise ZovarkValidationError(
                    f"findings[{index}].evidence_refs[{ref_index}] must be a non-empty string"
                )
            if evidence_ref not in evidence_ids:
                raise ZovarkValidationError(
                    f"findings[{index}].evidence_refs[{ref_index}] is not present in raw_evidence"
                )


def _verdict_value(findings: list[dict[str, Any]], *, no_findings_flag: bool) -> str:
    if no_findings_flag:
        return "inconclusive_insufficient_evidence"

    severities = [finding["severity"] for finding in findings]
    if any(severity in {"critical", "high"} for severity in severities):
        return "confirmed_malicious"
    if any(severity == "medium" for severity in severities):
        return "suspicious_unconfirmed"
    return "benign"


def _verdict_evidence_refs(
    findings: list[dict[str, Any]],
    evidence_ids_in_order: list[str],
) -> list[str]:
    finding_refs = {
        evidence_ref
        for finding in findings
        for evidence_ref in finding["evidence_refs"]
    }
    return [
        evidence_id
        for evidence_id in evidence_ids_in_order
        if evidence_id in finding_refs
    ]


def _highest_severity_finding(
    findings: list[dict[str, Any]],
    *,
    evidence_by_id: dict[str, dict[str, Any]],
    no_findings_flag: bool,
) -> str:
    if no_findings_flag:
        return "none (no_findings_flag)"

    highest = max(findings, key=lambda finding: _SEVERITY_RANK[finding["severity"]])
    severity = highest["severity"]
    evidence_refs = highest["evidence_refs"]
    source_types = [
        evidence_by_id[evidence_ref]["source_type"]
        for evidence_ref in evidence_refs
        if evidence_ref in evidence_by_id
    ]
    if (
        severity == "critical"
        and "credential_access" in source_types
        and _finding_mentions_lsass(highest, evidence_by_id)
    ):
        return "critical (credential_access via LSASS)"
    if source_types:
        return f"{severity} ({source_types[0]})"
    return severity


def _finding_mentions_lsass(
    finding: dict[str, Any],
    evidence_by_id: dict[str, dict[str, Any]],
) -> bool:
    if "lsass" in finding["title"].lower():
        return True
    for evidence_ref in finding["evidence_refs"]:
        raw_content = evidence_by_id[evidence_ref]["raw_content"]
        for value in raw_content.values():
            if isinstance(value, str) and "lsass" in value.lower():
                return True
    return False


def _verdict_set_at(tape: dict[str, Any]) -> str:
    timeline = tape.get("timeline", [])
    if isinstance(timeline, list):
        for event in timeline:
            if not isinstance(event, dict):
                continue
            if event.get("event_type") == "verdict_set":
                return _non_empty_string(event, "at")
    return _increment_iso8601_second(_non_empty_string(tape, "created_at"))


def _increment_iso8601_second(timestamp: str) -> str:
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
    if day > max_day:
        day = 1
        month += 1
    if month == 13:
        month = 1
        year += 1

    return f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}Z"


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


def _signing_tag(
    tape: dict[str, Any],
    *,
    findings: list[dict[str, Any]],
    evidence_entries: list[dict[str, Any]],
    verdict_value: str,
) -> str:
    snapshot = {
        "findings": findings,
        "raw_evidence": evidence_entries,
        "schema_version": tape["schema_version"],
        "source_alert_ref": tape["source_alert_ref"],
        "tape_id": tape["tape_id"],
        "tenant_id": tape["tenant_id"],
        "verdict_value": verdict_value,
    }
    return "sig-" + sha256_of_obj(snapshot)


def _validate_verdict(
    verdict: dict[str, Any],
    *,
    evidence_ids: set[str],
    expected_verdict: dict[str, Any] | None = None,
) -> None:
    if not isinstance(verdict, dict):
        raise ZovarkValidationError("verdict must be an object")
    if set(verdict) != _REQUIRED_VERDICT_FIELDS:
        raise ZovarkValidationError("verdict does not match the Slice 001 shape")
    _validate_verdict_value(_non_empty_string(verdict, "value"))
    for key in ("derivation_rule", "highest_severity_finding", "set_at", "signing_tag"):
        _non_empty_string(verdict, key)
    if not verdict["signing_tag"].startswith("sig-"):
        raise ZovarkValidationError("verdict.signing_tag must start with sig-")
    if expected_verdict is not None and verdict != expected_verdict:
        raise ZovarkValidationError("verdict does not match derived tape verdict")
    if verdict["model_contribution"] is not False:
        raise ZovarkValidationError("verdict.model_contribution must be false")
    if not isinstance(verdict["evidence_refs"], list):
        raise ZovarkValidationError("verdict.evidence_refs must be a list")
    for index, evidence_ref in enumerate(verdict["evidence_refs"]):
        if not isinstance(evidence_ref, str) or not evidence_ref:
            raise ZovarkValidationError(
                f"verdict.evidence_refs[{index}] must be a non-empty string"
            )
        if evidence_ref not in evidence_ids:
            raise ZovarkValidationError(
                f"verdict.evidence_refs[{index}] is not present in raw_evidence"
            )


def _validate_verdict_value(value: str) -> None:
    if value not in APPROVED_VERDICTS:
        raise ZovarkValidationError(f"unsupported verdict value: {value}")


def _non_empty_string(source: dict[str, Any], key: str) -> str:
    value = source.get(key)
    if not isinstance(value, str) or not value:
        raise ZovarkValidationError(f"{key} must be a non-empty string")
    return value

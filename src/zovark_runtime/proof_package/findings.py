"""Rule-driven findings derivation for Slice 001."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any

from zovark_runtime.proof_package import ZovarkValidationError


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
_ALLOWED_SEVERITIES = {"info", "low", "medium", "high", "critical"}

RULES: tuple[dict[str, Any], ...] = (
    {
        "evidence_source_types": ("edr_alert", "process_event"),
        "mitre_technique": "T1059.001",
        "rule_id": "RULE-OFFICE-SPAWN-ENCODED-PS",
        "severity": "high",
        "title": "Office application spawned encoded PowerShell",
    },
    {
        "evidence_source_types": ("process_event", "network_event"),
        "mitre_technique": "T1071.001",
        "rule_id": "RULE-PS-EXTERNAL-C2",
        "severity": "high",
        "title": "PowerShell contacted external IP over HTTPS",
    },
    {
        "evidence_source_types": ("credential_access",),
        "mitre_technique": "T1003.001",
        "rule_id": "RULE-LSASS-DUMP",
        "severity": "critical",
        "title": "Credential access via LSASS memory read",
    },
    {
        "evidence_source_types": ("lateral_movement_attempt",),
        "mitre_technique": "T1021.002",
        "rule_id": "RULE-SMB-LATERAL-MOVEMENT",
        "severity": "high",
        "title": "Lateral movement attempt over SMB (blocked by firewall)",
    },
)


def derive_findings(
    evidence_source: dict[str, Any] | list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], bool]:
    """Derive deterministic findings from evidence entries or a tape."""
    evidence_entries = _evidence_entries_from(evidence_source)

    if not evidence_entries:
        return [
            {
                "evidence_refs": [],
                "model_contribution": False,
                "severity": "info",
                "title": "No evidence - inconclusive",
            }
        ], True

    evidence_by_type = _evidence_by_source_type(evidence_entries)
    findings: list[dict[str, Any]] = []

    for rule in RULES:
        matched_entries = _matched_entries_for_rule(rule, evidence_by_type)
        if matched_entries is None:
            continue
        evidence_refs = [entry["evidence_id"] for entry in matched_entries]
        findings.append(_finding_from_rule(rule, evidence_refs))

    no_findings_flag = not findings
    _validate_findings(
        findings,
        evidence_ids={entry["evidence_id"] for entry in evidence_entries},
        no_findings_flag=no_findings_flag,
    )
    return findings, no_findings_flag


def append_findings(
    tape: dict[str, Any],
    findings: list[dict[str, Any]],
    no_findings_flag: bool,
) -> dict[str, Any]:
    """Return a copy of *tape* with derived findings appended."""
    evidence_entries = _evidence_entries_from(tape)
    _validate_findings(
        findings,
        evidence_ids={entry["evidence_id"] for entry in evidence_entries},
        no_findings_flag=no_findings_flag,
    )
    if "findings" in tape and not isinstance(tape["findings"], list):
        raise ZovarkValidationError("tape.findings must be a list")
    if not isinstance(no_findings_flag, bool):
        raise ZovarkValidationError("no_findings_flag must be boolean")

    updated = deepcopy(tape)
    updated["findings"] = deepcopy(updated.get("findings", [])) + deepcopy(findings)
    if no_findings_flag:
        updated["no_findings_flag"] = True
    else:
        updated.pop("no_findings_flag", None)
    return updated


def attach_findings(
    tape: dict[str, Any],
    findings: list[dict[str, Any]],
    no_findings_flag: bool = False,
) -> dict[str, Any]:
    """Return a copy of *tape* with *findings* attached."""
    evidence_entries = _evidence_entries_from(tape)
    _validate_findings(
        findings,
        evidence_ids={entry["evidence_id"] for entry in evidence_entries},
        no_findings_flag=no_findings_flag,
    )
    if "findings" in tape and not isinstance(tape["findings"], list):
        raise ZovarkValidationError("tape.findings must be a list")
    if not isinstance(no_findings_flag, bool):
        raise ZovarkValidationError("no_findings_flag must be boolean")

    updated = deepcopy(tape)
    updated["findings"] = deepcopy(findings)
    if no_findings_flag:
        updated["no_findings_flag"] = True
    else:
        updated.pop("no_findings_flag", None)
    return updated


def _evidence_entries_from(
    evidence_source: dict[str, Any] | list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if isinstance(evidence_source, dict):
        if "raw_evidence" not in evidence_source:
            raise ZovarkValidationError("tape is missing raw_evidence")
        evidence_entries = evidence_source["raw_evidence"]
    else:
        evidence_entries = evidence_source

    if not isinstance(evidence_entries, list):
        raise ZovarkValidationError("evidence_entries must be a list")

    _validate_evidence_entries(evidence_entries)
    return evidence_entries


def _validate_evidence_entries(evidence_entries: list[dict[str, Any]]) -> None:
    seen_ids: set[str] = set()
    for index, entry in enumerate(evidence_entries):
        if not isinstance(entry, dict):
            raise ZovarkValidationError(f"evidence_entries[{index}] must be an object")
        if set(entry) != _REQUIRED_EVIDENCE_FIELDS:
            raise ZovarkValidationError(
                f"evidence_entries[{index}] does not match the Slice 001 evidence shape"
            )
        for key in ("evidence_id", "source_type", "hash", "ingested_at"):
            if not isinstance(entry[key], str) or not entry[key]:
                raise ZovarkValidationError(
                    f"evidence_entries[{index}].{key} must be a non-empty string"
                )
        if entry["evidence_id"] in seen_ids:
            raise ZovarkValidationError(
                f"evidence_entries[{index}].evidence_id must be unique"
            )
        seen_ids.add(entry["evidence_id"])
        if not isinstance(entry["raw_content"], dict):
            raise ZovarkValidationError(
                f"evidence_entries[{index}].raw_content must be an object"
            )


def _evidence_by_source_type(
    evidence_entries: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    by_type: dict[str, list[dict[str, Any]]] = {}
    for entry in evidence_entries:
        by_type.setdefault(entry["source_type"], []).append(entry)
    return by_type


def _matched_entries_for_rule(
    rule: dict[str, Any],
    evidence_by_type: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]] | None:
    rule_id = rule["rule_id"]
    if rule_id == "RULE-OFFICE-SPAWN-ENCODED-PS":
        alert = _first_entry(evidence_by_type, "edr_alert", _alert_indicates_powershell)
        process = _first_entry(
            evidence_by_type,
            "process_event",
            _process_indicates_encoded_powershell,
        )
        if alert is None or process is None:
            return None
        return [alert, process]

    if rule_id == "RULE-PS-EXTERNAL-C2":
        process = _first_entry(evidence_by_type, "process_event", _is_powershell_process)
        network = _first_entry(
            evidence_by_type,
            "network_event",
            lambda raw_content: _network_indicates_c2(raw_content, process),
        )
        if process is None or network is None:
            return None
        return [process, network]

    if rule_id == "RULE-LSASS-DUMP":
        credential = _first_entry(
            evidence_by_type,
            "credential_access",
            _credential_access_indicates_lsass,
        )
        if credential is None:
            return None
        return [credential]

    if rule_id == "RULE-SMB-LATERAL-MOVEMENT":
        lateral = _first_entry(
            evidence_by_type,
            "lateral_movement_attempt",
            _lateral_movement_indicates_smb_attempt,
        )
        if lateral is None:
            return None
        return [lateral]

    raise ZovarkValidationError(f"unsupported finding rule: {rule_id}")


def _first_entry(
    evidence_by_type: dict[str, list[dict[str, Any]]],
    source_type: str,
    predicate: Callable[[dict[str, Any]], bool],
) -> dict[str, Any] | None:
    for entry in evidence_by_type.get(source_type, []):
        if predicate(entry["raw_content"]):
            return entry
    return None


def _alert_indicates_powershell(raw_content: dict[str, Any]) -> bool:
    alert_text = _text_fields(
        raw_content,
        "alert_type",
        "child_process",
        "description",
        "source_process",
    )
    return "powershell" in alert_text or "office" in alert_text


def _process_indicates_encoded_powershell(raw_content: dict[str, Any]) -> bool:
    command_line = _text_fields(raw_content, "command_line")
    return _is_powershell_process(raw_content) and "encodedcommand" in command_line


def _is_powershell_process(raw_content: dict[str, Any]) -> bool:
    process_text = _text_fields(
        raw_content,
        "child_process",
        "command_line",
        "parent_process",
        "process",
        "process_name",
    )
    return "powershell" in process_text


def _network_indicates_c2(
    raw_content: dict[str, Any],
    process_entry: dict[str, Any] | None,
) -> bool:
    network_text = _text_fields(
        raw_content,
        "classification",
        "destination_ip",
        "event_type",
        "process",
        "process_name",
        "protocol",
    )
    if "c2" in network_text:
        return True
    if "powershell" in network_text and "https" in network_text:
        return True
    return bool(
        process_entry is not None
        and _same_process(raw_content, process_entry["raw_content"])
        and "https" in network_text
        and str(raw_content.get("destination_port")) == "443"
        and bool(raw_content.get("destination_ip"))
    )


def _credential_access_indicates_lsass(raw_content: dict[str, Any]) -> bool:
    credential_text = _text_fields(
        raw_content,
        "event_type",
        "process",
        "target_process",
        "technique",
        "technique_name",
    )
    return "lsass" in credential_text or "t1003.001" in credential_text


def _lateral_movement_indicates_smb_attempt(raw_content: dict[str, Any]) -> bool:
    lateral_text = _text_fields(
        raw_content,
        "destination_host",
        "event_type",
        "process",
        "status",
        "technique",
        "technique_name",
    )
    # Fire only for genuine SMB lateral movement (technique T1021.002 or "smb"), so the
    # SMB finding never mislabels a non-SMB blocked lateral movement. A bare
    # "blocked_by_firewall" status no longer triggers an SMB-specific finding.
    return "t1021.002" in lateral_text or "smb" in lateral_text


def _text_fields(raw_content: dict[str, Any], *keys: str) -> str:
    values = []
    for key in keys:
        value = raw_content.get(key)
        if isinstance(value, str):
            values.append(value.lower())
    return " ".join(values)


def _same_process(
    network_content: dict[str, Any],
    process_content: dict[str, Any],
) -> bool:
    network_pid = network_content.get("pid")
    process_pid = process_content.get("pid")
    if network_pid is not None and process_pid is not None:
        return network_pid == process_pid

    network_process = _text_fields(network_content, "process", "process_name")
    process_name = _text_fields(process_content, "process", "process_name")
    return bool(network_process and process_name and network_process == process_name)


def _finding_from_rule(
    rule: dict[str, Any],
    evidence_refs: list[str],
) -> dict[str, Any]:
    return {
        "evidence_refs": evidence_refs,
        "mitre_technique": rule["mitre_technique"],
        "model_contribution": False,
        "rule_id": rule["rule_id"],
        "severity": rule["severity"],
        "title": rule["title"],
    }


def _validate_findings(
    findings: list[dict[str, Any]],
    *,
    evidence_ids: set[str],
    no_findings_flag: bool,
) -> None:
    if not isinstance(findings, list):
        raise ZovarkValidationError("findings must be a list")
    if not isinstance(no_findings_flag, bool):
        raise ZovarkValidationError("no_findings_flag must be boolean")
    if not findings and not no_findings_flag:
        raise ZovarkValidationError("empty findings require no_findings_flag")

    seen_rule_ids: set[str] = set()
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            raise ZovarkValidationError(f"findings[{index}] must be an object")
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
        if severity not in _ALLOWED_SEVERITIES:
            raise ZovarkValidationError(f"findings[{index}].severity is invalid")

        if "rule_id" in finding:
            rule_id = _non_empty_string(finding, "rule_id")
            if rule_id in seen_rule_ids:
                raise ZovarkValidationError(
                    f"findings[{index}].rule_id must be unique"
                )
            seen_rule_ids.add(rule_id)
        if "mitre_technique" in finding:
            _non_empty_string(finding, "mitre_technique")

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


def _non_empty_string(source: dict[str, Any], key: str) -> str:
    value = source.get(key)
    if not isinstance(value, str) or not value:
        raise ZovarkValidationError(f"{key} must be a non-empty string")
    return value

"""Approval-required EDR handoff construction for Slice 001."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from zovark_runtime.proof_package import ZovarkValidationError
from zovark_runtime.proof_package.hashing import sha256_of_string
from zovark_runtime.proof_package.verdict import derive_verdict


APPROVAL_MODE = "approval_required"
AUTHORIZATION_RECORD_REF = "vault://placeholder/bootstrap"
EXECUTION_REASON = "recommendation_only_no_dispatcher_in_slice_001"
POLICY_SNAPSHOT_VERSION = "0.0.1-bootstrap"
_POLICY_SNAPSHOT_SOURCE = "slice-001-bootstrap-policy"
_REQUIRED_EVIDENCE_FIELDS = {
    "evidence_id",
    "source_type",
    "hash",
    "raw_content",
    "ingested_at",
}
_REQUIRED_HANDOFF_FIELDS = {
    "action_type",
    "approval_mode",
    "audit_ref",
    "authorization_record_ref",
    "blast_radius",
    "evidence_refs",
    "execution_result",
    "handoff_id",
    "idempotency_key",
    "policy_snapshot",
    "policy_snapshot_version",
    "replay_linkage",
    "rollback_plan",
    "tape_ref",
    "target",
    "tenant_id",
}
_REQUIRED_EXECUTION_FIELDS = {
    "completed_at",
    "error",
    "reason",
    "started_at",
    "status",
    "vendor_response_ref",
}
_REQUIRED_ROLLBACK_FIELDS = {
    "idempotency_key",
    "manual_steps",
    "recovery_notes",
    "reversibility_class",
    "reversal_window",
    "vendor_reversal_action",
    "vendor_reversal_target",
}
_ALLOWED_REVERSIBILITY_CLASSES = {
    "automatic",
    "manual_documented",
    "irreversible",
}
_OLD_ROLLBACK_FIELD_NAMES = {"reversal_or_recovery_plan"}
_OLD_ROLLBACK_ENUM_VALUES = {
    "irreversible_requires_compensation",
    "manual_recovery_required",
    "reversible_by_edr",
}


def derive_handoff(tape: dict[str, Any]) -> dict[str, Any]:
    """Derive the deterministic approval-required EDR handoff card."""
    _validate_tape(tape)
    expected_verdict = derive_verdict(tape)
    if tape["verdict"] != expected_verdict:
        raise ZovarkValidationError("tape.verdict does not match derived verdict")

    action_type = _action_type(tape["findings"])
    target = _target(tape, action_type=action_type)
    evidence_refs = _evidence_refs(tape)
    _validate_target_evidence_trace(
        tape,
        action_type=action_type,
        target=target,
        evidence_refs=evidence_refs,
    )
    idempotency_key = sha256_of_string(
        f"{tape['tape_id']}:{action_type}:{target['identifier']}"
    )
    rollback_plan = _rollback_plan(
        tape=tape,
        action_type=action_type,
        target=target,
        idempotency_key=idempotency_key,
    )
    handoff = {
        "action_type": action_type,
        "approval_mode": APPROVAL_MODE,
        "audit_ref": tape.get("audit_ref"),
        "authorization_record_ref": AUTHORIZATION_RECORD_REF,
        "blast_radius": _blast_radius(tape, action_type=action_type, target=target),
        "evidence_refs": evidence_refs,
        "execution_result": {
            "completed_at": None,
            "error": None,
            "reason": EXECUTION_REASON,
            "started_at": None,
            "status": "pending",
            "vendor_response_ref": None,
        },
        "handoff_id": "handoff-" + idempotency_key[:16],
        "idempotency_key": idempotency_key,
        "policy_snapshot": sha256_of_string(_POLICY_SNAPSHOT_SOURCE),
        "policy_snapshot_version": POLICY_SNAPSHOT_VERSION,
        "replay_linkage": [],
        "rollback_plan": rollback_plan,
        "tape_ref": tape["tape_id"],
        "target": target,
        "tenant_id": tape["tenant_id"],
    }
    _validate_handoff(handoff, tape=tape)
    return handoff


def build_handoff(
    tape: dict[str, Any],
    verdict: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Task-compatible wrapper for handoff construction."""
    if verdict is None:
        return derive_handoff(tape)
    updated = deepcopy(tape)
    updated["verdict"] = deepcopy(verdict)
    return derive_handoff(updated)


def attach_handoff(tape: dict[str, Any], handoff: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of *tape* with the exact derived handoff attached."""
    expected_handoff = derive_handoff(tape)
    _validate_handoff(handoff, tape=tape)
    if handoff != expected_handoff:
        raise ZovarkValidationError("handoff does not match derived tape handoff")

    updated = deepcopy(tape)
    updated["handoff"] = deepcopy(handoff)
    updated["handoff_ref"] = handoff["handoff_id"]
    updated["handoff_summary"] = {
        "action_type": handoff["action_type"],
        "approval_mode": handoff["approval_mode"],
        "execution_status": handoff["execution_result"]["status"],
        "target": {
            "identifier": handoff["target"]["identifier"],
            "kind": handoff["target"]["kind"],
        },
    }
    return updated


def set_handoff(tape: dict[str, Any], handoff: dict[str, Any]) -> dict[str, Any]:
    """Alias for attaching the derived handoff to a copied tape."""
    return attach_handoff(tape, handoff)


def _validate_tape(tape: dict[str, Any]) -> None:
    if not isinstance(tape, dict):
        raise ZovarkValidationError("tape must be an object")
    for key in ("tape_id", "tenant_id", "created_at"):
        _non_empty_string(tape, key)
    for key in ("raw_evidence", "findings", "verdict"):
        if key not in tape:
            raise ZovarkValidationError(f"tape is missing {key}")

    _validate_evidence_entries(tape["raw_evidence"])
    evidence_ids = {entry["evidence_id"] for entry in tape["raw_evidence"]}
    _validate_findings(
        tape["findings"],
        evidence_ids=evidence_ids,
        no_findings_flag=tape.get("no_findings_flag", False),
    )
    if not isinstance(tape["verdict"], dict):
        raise ZovarkValidationError("tape.verdict must be an object")


def _validate_evidence_entries(evidence_entries: list[dict[str, Any]]) -> None:
    if not isinstance(evidence_entries, list):
        raise ZovarkValidationError("tape.raw_evidence must be a list")

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
        raise ZovarkValidationError("empty findings require no_findings_flag")

    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            raise ZovarkValidationError(f"tape.findings[{index}] must be an object")
        if finding.get("model_contribution") is not False:
            raise ZovarkValidationError(
                f"tape.findings[{index}].model_contribution must be false"
            )
        _non_empty_string(finding, "severity")
        refs = finding.get("evidence_refs")
        if not isinstance(refs, list):
            raise ZovarkValidationError(
                f"tape.findings[{index}].evidence_refs must be a list"
            )
        if not refs and not no_findings_flag:
            raise ZovarkValidationError(
                f"tape.findings[{index}].evidence_refs must not be empty"
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


def _action_type(findings: list[dict[str, Any]]) -> str:
    severities = {finding["severity"] for finding in findings}
    if severities & {"critical", "high"}:
        return "isolate_host"
    return "notify_only"


def _target(tape: dict[str, Any], *, action_type: str) -> dict[str, Any]:
    if action_type == "notify_only":
        return {
            "identifier": "slice-001-static-sample",
            "kind": "custom",
            "validated_at": _target_validated_at(tape),
        }

    alert = _alert_content(tape)
    identifier = alert.get("host")
    if not isinstance(identifier, str) or not identifier:
        raise ZovarkValidationError("isolate_host requires alert host")
    target = {
        "identifier": identifier,
        "kind": "host",
        "validated_at": _target_validated_at(tape),
    }
    fqdn = alert.get("host_fqdn")
    if isinstance(fqdn, str) and fqdn:
        target["fqdn"] = fqdn
    elif "." in identifier:
        target["fqdn"] = identifier
    return target


def _target_validated_at(tape: dict[str, Any]) -> str:
    alert = _alert_content(tape)
    timestamp = alert.get("timestamp")
    if isinstance(timestamp, str) and timestamp:
        return timestamp
    return _non_empty_string(tape, "created_at")


def _alert_content(tape: dict[str, Any]) -> dict[str, Any]:
    for entry in tape["raw_evidence"]:
        if entry["source_type"] == "edr_alert":
            return entry["raw_content"]
    raise ZovarkValidationError("tape.raw_evidence is missing edr_alert")


def _evidence_refs(tape: dict[str, Any]) -> list[str]:
    refs = tape["verdict"].get("evidence_refs")
    if not isinstance(refs, list) or not refs:
        raise ZovarkValidationError("handoff requires non-empty verdict evidence_refs")
    known_ids = {entry["evidence_id"] for entry in tape["raw_evidence"]}
    for index, evidence_ref in enumerate(refs):
        if evidence_ref not in known_ids:
            raise ZovarkValidationError(
                f"verdict.evidence_refs[{index}] is not present in raw_evidence"
            )
    return list(refs)


def _rollback_plan(
    *,
    tape: dict[str, Any],
    action_type: str,
    target: dict[str, Any],
    idempotency_key: str,
) -> dict[str, Any]:
    if action_type == "isolate_host":
        reversal_action = "release_isolation"
        recovery_notes = (
            "In a live EDR integration, the expected reversal action would be "
            "release_isolation. In Slice 001, this is a recommendation only; "
            "no EDR action is dispatched."
        )
        # Only assert a credential-access rationale when LSASS evidence actually exists.
        if _has_lsass_evidence(tape):
            recovery_notes += (
                f" Credential rotation for {_affected_user(tape)} is recommended given "
                "the recorded LSASS access event."
            )
    else:
        reversal_action = "none"
        recovery_notes = (
            "No EDR action is dispatched in Slice 001; notify_only has no "
            "vendor-side reversal."
        )

    return {
        "idempotency_key": sha256_of_string(
            f"{idempotency_key}:rollback:{reversal_action}"
        ),
        "manual_steps": [],
        "recovery_notes": recovery_notes,
        "reversibility_class": "automatic",
        "reversal_window": "PT4H",
        "vendor_reversal_action": reversal_action,
        "vendor_reversal_target": {
            "identifier": target["identifier"],
            "kind": target["kind"],
        },
    }


def _affected_user(tape: dict[str, Any]) -> str:
    for entry in tape["raw_evidence"]:
        raw_content = entry["raw_content"]
        user = raw_content.get("user")
        if isinstance(user, str) and user:
            return user
    return "the affected user"


def _has_lsass_evidence(tape: dict[str, Any]) -> bool:
    """True only if a recorded credential_access evidence item references LSASS.

    Gates LSASS narrative so a handoff never asserts an LSASS access event that is not
    backed by recorded evidence.
    """
    for entry in tape["raw_evidence"]:
        if entry.get("source_type") != "credential_access":
            continue
        for value in entry["raw_content"].values():
            if isinstance(value, str) and "lsass" in value.lower():
                return True
    return False


def _blast_radius(
    tape: dict[str, Any],
    *,
    action_type: str,
    target: dict[str, Any],
) -> dict[str, Any]:
    if action_type != "isolate_host":
        return {
            "directly_affected": [],
            "estimated_business_impact": (
                "Notify-only recommendation. No endpoint action is dispatched."
            ),
            "lateral_movement_blocked": [],
            "services_at_risk": [],
        }

    identifier = target["identifier"]
    return {
        "directly_affected": [identifier],
        "estimated_business_impact": (
            "Single workstation isolation. "
            "No shared infrastructure dependency identified in evidence."
        ),
        "lateral_movement_blocked": _blocked_lateral_movement(tape),
        "services_at_risk": [
            f"Any user sessions active on {identifier} will be terminated",
            f"Any processes running on {identifier} will lose network access",
            f"Shared drives mounted from {identifier} will become unavailable",
        ],
    }


def _blocked_lateral_movement(tape: dict[str, Any]) -> list[str]:
    blocked = []
    for entry in tape["raw_evidence"]:
        if entry["source_type"] != "lateral_movement_attempt":
            continue
        raw_content = entry["raw_content"]
        destination_host = raw_content.get("destination_host")
        status = raw_content.get("status")
        if (
            isinstance(destination_host, str)
            and destination_host
            and status == "blocked_by_firewall"
        ):
            # Only label the attempt "SMB" when the evidence actually indicates SMB.
            attempt = "SMB attempt" if _content_mentions_smb(raw_content) else "lateral-movement attempt"
            blocked.append(
                f"{destination_host} ({attempt} was already blocked by firewall)"
            )
    return blocked


def _content_mentions_smb(raw_content: dict[str, Any]) -> bool:
    for value in raw_content.values():
        if isinstance(value, str) and ("smb" in value.lower() or "t1021.002" in value.lower()):
            return True
    return False


def _validate_handoff(handoff: dict[str, Any], *, tape: dict[str, Any]) -> None:
    if not isinstance(handoff, dict):
        raise ZovarkValidationError("handoff must be an object")
    if _OLD_ROLLBACK_FIELD_NAMES & set(handoff):
        raise ZovarkValidationError("old rollback field names are not allowed")
    if set(handoff) != _REQUIRED_HANDOFF_FIELDS:
        raise ZovarkValidationError("handoff does not match the Slice 001 shape")

    if handoff["approval_mode"] != APPROVAL_MODE:
        raise ZovarkValidationError("handoff.approval_mode must be approval_required")
    if handoff["authorization_record_ref"] != AUTHORIZATION_RECORD_REF:
        raise ZovarkValidationError("handoff.authorization_record_ref is invalid")
    if handoff["tenant_id"] != tape["tenant_id"]:
        raise ZovarkValidationError("handoff.tenant_id must match tape.tenant_id")
    if handoff["tape_ref"] != tape["tape_id"]:
        raise ZovarkValidationError("handoff.tape_ref must match tape.tape_id")
    _non_empty_string(handoff, "handoff_id")
    _non_empty_string(handoff, "action_type")
    _non_empty_string(handoff, "idempotency_key")
    if handoff["handoff_id"] != "handoff-" + handoff["idempotency_key"][:16]:
        raise ZovarkValidationError("handoff.handoff_id does not match idempotency_key")
    if handoff["policy_snapshot"] != sha256_of_string(_POLICY_SNAPSHOT_SOURCE):
        raise ZovarkValidationError("handoff.policy_snapshot is invalid")
    if handoff["policy_snapshot_version"] != POLICY_SNAPSHOT_VERSION:
        raise ZovarkValidationError("handoff.policy_snapshot_version is invalid")

    _validate_target(handoff["target"], action_type=handoff["action_type"])
    expected_idempotency_key = sha256_of_string(
        f"{tape['tape_id']}:{handoff['action_type']}:{handoff['target']['identifier']}"
    )
    if handoff["idempotency_key"] != expected_idempotency_key:
        raise ZovarkValidationError("handoff.idempotency_key is invalid")
    _validate_evidence_refs(handoff["evidence_refs"], tape=tape)
    _validate_target_evidence_trace(
        tape,
        action_type=handoff["action_type"],
        target=handoff["target"],
        evidence_refs=handoff["evidence_refs"],
    )
    _validate_execution_result(handoff["execution_result"])
    _validate_rollback_plan(
        handoff["rollback_plan"],
        action_type=handoff["action_type"],
        target=handoff["target"],
        idempotency_key=handoff["idempotency_key"],
    )
    if not isinstance(handoff["blast_radius"], dict):
        raise ZovarkValidationError("handoff.blast_radius must be an object")
    if not isinstance(handoff["replay_linkage"], list):
        raise ZovarkValidationError("handoff.replay_linkage must be a list")


def _validate_target(target: dict[str, Any], *, action_type: str) -> None:
    if not isinstance(target, dict):
        raise ZovarkValidationError("handoff.target must be an object")
    _non_empty_string(target, "kind")
    _non_empty_string(target, "identifier")
    _non_empty_string(target, "validated_at")
    if action_type == "isolate_host" and target["kind"] != "host":
        raise ZovarkValidationError("isolate_host requires host target")
    if action_type == "notify_only" and target["kind"] != "custom":
        raise ZovarkValidationError("notify_only requires custom target")


def _validate_evidence_refs(evidence_refs: list[str], *, tape: dict[str, Any]) -> None:
    if not isinstance(evidence_refs, list) or not evidence_refs:
        raise ZovarkValidationError("handoff.evidence_refs must be non-empty")
    known_ids = {entry["evidence_id"] for entry in tape["raw_evidence"]}
    for index, evidence_ref in enumerate(evidence_refs):
        if not isinstance(evidence_ref, str) or not evidence_ref:
            raise ZovarkValidationError(
                f"handoff.evidence_refs[{index}] must be a non-empty string"
            )
        if evidence_ref not in known_ids:
            raise ZovarkValidationError(
                f"handoff.evidence_refs[{index}] is not present in raw_evidence"
            )


def _validate_target_evidence_trace(
    tape: dict[str, Any],
    *,
    action_type: str,
    target: dict[str, Any],
    evidence_refs: list[str],
) -> None:
    if action_type != "isolate_host":
        return

    referenced_entries = [
        entry for entry in tape["raw_evidence"] if entry["evidence_id"] in evidence_refs
    ]
    target_identifiers = [
        value
        for value in (target.get("identifier"), target.get("fqdn"))
        if isinstance(value, str) and value
    ]
    if not target_identifiers:
        raise ZovarkValidationError("isolate_host target is missing an identifier")
    for entry in referenced_entries:
        if _raw_content_mentions_any(entry["raw_content"], target_identifiers):
            return
    raise ZovarkValidationError("isolate_host target is not backed by evidence_refs")


def _raw_content_mentions_any(value: Any, needles: list[str]) -> bool:
    if isinstance(value, str):
        return any(needle in value for needle in needles)
    if isinstance(value, dict):
        return any(_raw_content_mentions_any(item, needles) for item in value.values())
    if isinstance(value, list):
        return any(_raw_content_mentions_any(item, needles) for item in value)
    return False


def _validate_execution_result(execution_result: dict[str, Any]) -> None:
    if not isinstance(execution_result, dict):
        raise ZovarkValidationError("handoff.execution_result must be an object")
    if set(execution_result) != _REQUIRED_EXECUTION_FIELDS:
        raise ZovarkValidationError("handoff.execution_result shape is invalid")
    if execution_result["status"] != "pending":
        raise ZovarkValidationError("handoff.execution_result.status must be pending")
    if execution_result["reason"] != EXECUTION_REASON:
        raise ZovarkValidationError("handoff.execution_result.reason is invalid")
    for key in ("started_at", "completed_at", "vendor_response_ref", "error"):
        if execution_result[key] is not None:
            raise ZovarkValidationError(
                f"handoff.execution_result.{key} must be null in Slice 001"
            )


def _validate_rollback_plan(
    rollback_plan: dict[str, Any],
    *,
    action_type: str,
    target: dict[str, Any],
    idempotency_key: str,
) -> None:
    if not isinstance(rollback_plan, dict):
        raise ZovarkValidationError("handoff.rollback_plan must be an object")
    if set(rollback_plan) != _REQUIRED_ROLLBACK_FIELDS:
        raise ZovarkValidationError("handoff.rollback_plan shape is invalid")
    reversibility_class = _non_empty_string(rollback_plan, "reversibility_class")
    if reversibility_class in _OLD_ROLLBACK_ENUM_VALUES:
        raise ZovarkValidationError("old rollback enum values are not allowed")
    if reversibility_class not in _ALLOWED_REVERSIBILITY_CLASSES:
        raise ZovarkValidationError("handoff.rollback_plan.reversibility_class is invalid")
    if reversibility_class == "manual_documented" and not rollback_plan["manual_steps"]:
        raise ZovarkValidationError("manual_documented rollback requires manual_steps")
    if reversibility_class == "irreversible" and rollback_plan["vendor_reversal_action"] != "none":
        raise ZovarkValidationError("irreversible rollback requires vendor_reversal_action none")

    expected_reversal_action = (
        "release_isolation" if action_type == "isolate_host" else "none"
    )
    if rollback_plan["vendor_reversal_action"] != expected_reversal_action:
        raise ZovarkValidationError("handoff.rollback_plan.vendor_reversal_action is invalid")
    if rollback_plan["idempotency_key"] != sha256_of_string(
        f"{idempotency_key}:rollback:{expected_reversal_action}"
    ):
        raise ZovarkValidationError("handoff.rollback_plan.idempotency_key is invalid")
    if rollback_plan["manual_steps"] != []:
        raise ZovarkValidationError("Slice 001 rollback manual_steps must be empty")
    if rollback_plan["reversal_window"] != "PT4H":
        raise ZovarkValidationError("handoff.rollback_plan.reversal_window is invalid")
    _non_empty_string(rollback_plan, "recovery_notes")

    reversal_target = rollback_plan["vendor_reversal_target"]
    if not isinstance(reversal_target, dict):
        raise ZovarkValidationError("handoff.rollback_plan.vendor_reversal_target must be an object")
    if reversal_target != {"identifier": target["identifier"], "kind": target["kind"]}:
        raise ZovarkValidationError("handoff.rollback_plan.vendor_reversal_target is invalid")


def _non_empty_string(source: dict[str, Any], key: str) -> str:
    value = source.get(key)
    if not isinstance(value, str) or not value:
        raise ZovarkValidationError(f"{key} must be a non-empty string")
    return value

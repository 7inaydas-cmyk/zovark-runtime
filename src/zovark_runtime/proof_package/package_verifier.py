"""Offline proof-package verifier for Slice 002 Replay V2."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, NoReturn

from zovark_runtime.proof_package import ZovarkValidationError
from zovark_runtime.proof_package.audit import GENESIS_HASH, derive_audit_entry
from zovark_runtime.proof_package.handoff import derive_handoff
from zovark_runtime.proof_package.replay import derive_replay_report
from zovark_runtime.proof_package.verdict import APPROVED_VERDICTS
from zovark_runtime.proof_package.writer import (
    EXPECTED_OUTPUT_FILES,
    JSON_OUTPUT_FILES,
    render_customer_report,
)


MARKDOWN_OUTPUT_FILES = ("customer-report.md",)
V2_MARKER_FILE = "proof-package-v2.json"
V2_PACKAGE_CONTRACT = "proof-package-v2/0.1"
_EXPECTED_FILE_SET = set(EXPECTED_OUTPUT_FILES)
_V2_EXPECTED_FILE_SET = _EXPECTED_FILE_SET | {V2_MARKER_FILE}
_VERIFIED_COMPONENTS = (
    "file_set",
    "json_parse",
    "extracted_views",
    "handoff",
    "audit_entry",
    "replay_report",
    "customer_report",
)
_V2_VERIFIED_COMPONENTS = _VERIFIED_COMPONENTS + (
    "package_version",
    "v2_required_objects",
    "v2_object_shapes",
)
_V2_REQUIRED_OBJECTS = (
    "decision_rationale",
    "visibility_gaps",
    "approval_record",
    "customer_report_v2",
)
_V2_CONDITIONAL_OBJECTS = {
    "false_positive_reasoning": (
        "benign_verdict",
        "rejected_findings_present",
        "analyst_override_present",
    ),
    "context_enrichment": ("context_enrichment_used",),
    "blast_radius": (
        "response_action_present",
        "containment_recommended",
        "customer_impact_language_present",
    ),
    "rollback_plan": ("response_action_present", "containment_recommended"),
}
_V2_CONDITION_KEYS = tuple(
    sorted(
        {
            condition_key
            for condition_keys in _V2_CONDITIONAL_OBJECTS.values()
            for condition_key in condition_keys
        }
    )
)
_V2_KNOWN_OBJECTS = frozenset(
    _V2_REQUIRED_OBJECTS
    + tuple(_V2_CONDITIONAL_OBJECTS)
    + (
        "compliance_mapping",
        "controls_in_place_at_incident",
    )
)
_V2_OBJECT_STATUSES = {"populated", "partial", "unavailable", "not_applicable"}
_VERIFIED_RESPONSE_ACTION_TYPES = frozenset({"isolate_host"})
_VERIFIED_CONTAINMENT_ACTION_TYPES = frozenset({"isolate_host"})
_VERIFIED_NON_RESPONSE_ACTION_TYPES = frozenset({"notify_only"})
_FALSE_POSITIVE_REASONING_VERDICTS = frozenset(
    {
        "benign",
        "inconclusive_insufficient_evidence",
        "suspicious_unconfirmed",
    }
)
_VERDICTS_WITHOUT_FALSE_POSITIVE_TRIGGER = frozenset({"confirmed_malicious"})


def load_proof_package(package_dir: str | Path) -> dict[str, Any]:
    """Load proof-package artifacts from *package_dir*."""
    package_path = Path(package_dir)
    _validate_package_dir(package_path)
    package_shape = _validate_file_set(package_path)

    package: dict[str, Any] = {}
    for filename in JSON_OUTPUT_FILES:
        package[filename] = _load_json_file(package_path / filename)
    if package_shape == "v2":
        package[V2_MARKER_FILE] = _load_json_file(package_path / V2_MARKER_FILE)

    report_text = (package_path / "customer-report.md").read_text(encoding="utf-8")
    if not report_text:
        _fail("empty_customer_report", "customer-report.md must not be empty")
    package["customer-report.md"] = report_text
    return package


def validate_loaded_proof_package(package: dict[str, Any]) -> dict[str, Any]:
    """Validate an already-loaded proof package."""
    if not isinstance(package, dict):
        _fail("package_shape_invalid", "proof package must be an object")

    package_keys = set(package)
    if package_keys == _EXPECTED_FILE_SET:
        return _validate_loaded_v1_package(package)
    if package_keys == _V2_EXPECTED_FILE_SET:
        return _validate_loaded_v2_package(package)
    _fail("package_shape_invalid", "proof package file set is invalid")


def verify_proof_package(package_dir: str | Path) -> dict[str, Any]:
    """Load and verify a proof-package directory offline."""
    package = load_proof_package(package_dir)
    return validate_loaded_proof_package(package)


def _validate_loaded_v1_package(package: dict[str, Any]) -> dict[str, Any]:
    summary, _ = _verify_v1_package(package)
    return summary


def _validate_loaded_v2_package(package: dict[str, Any]) -> dict[str, Any]:
    marker = package[V2_MARKER_FILE]
    if not isinstance(marker, dict):
        _fail("v2_package_shape_invalid", f"{V2_MARKER_FILE} must be an object")

    base_package = {filename: package[filename] for filename in EXPECTED_OUTPUT_FILES}
    base_summary, full_tape = _verify_v1_package(base_package)
    derived_conditions = _derive_v2_conditions(full_tape)
    trusted_refs = _trusted_reference_index(full_tape)
    objects = _validate_v2_marker(marker, derived_conditions, trusted_refs)
    return _v2_verification_summary(base_summary, objects)


def _verify_v1_package(package: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if set(package) != _EXPECTED_FILE_SET:
        _fail("package_shape_invalid", "proof package file set is invalid")
    for filename in JSON_OUTPUT_FILES:
        if not isinstance(package[filename], (dict, list)):
            _fail("package_shape_invalid", f"{filename} must be a JSON artifact")
    if not isinstance(package["customer-report.md"], str) or not package[
        "customer-report.md"
    ]:
        _fail("empty_customer_report", "customer-report.md must be non-empty text")

    full_tape = _reconstruct_verified_tape(package)
    _validate_customer_report(package, full_tape)
    return _verification_summary(full_tape), full_tape


def _validate_package_dir(package_dir: Path) -> None:
    if not package_dir.exists():
        _fail("package_not_found", "proof package directory does not exist")
    if not package_dir.is_dir():
        _fail("package_not_directory", "proof package path must be a directory")


def _validate_file_set(package_dir: Path) -> str:
    actual_entries = {entry.name for entry in package_dir.iterdir()}
    if actual_entries == _EXPECTED_FILE_SET:
        expected_files = EXPECTED_OUTPUT_FILES
        package_shape = "v1"
    elif actual_entries == _V2_EXPECTED_FILE_SET:
        expected_files = EXPECTED_OUTPUT_FILES + (V2_MARKER_FILE,)
        package_shape = "v2"
    else:
        _fail(
            "package_file_set_mismatch",
            "proof package directory file set is invalid",
        )
    for filename in expected_files:
        if not (package_dir / filename).is_file():
            _fail("artifact_not_file", f"{filename} must be a file")
    return package_shape


def _load_json_file(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ZovarkValidationError(
            f"malformed_json: {path.name} is not valid JSON"
        ) from exc
    except OSError as exc:
        raise ZovarkValidationError(
            f"malformed_json: {path.name} could not be read"
        ) from exc


def _reconstruct_verified_tape(package: dict[str, Any]) -> dict[str, Any]:
    tape = deepcopy(package["investigation-tape.json"])
    if not isinstance(tape, dict):
        _fail("package_shape_invalid", "investigation-tape.json must be an object")
    if tape.get("state") != "closed":
        _fail("tape_state_invalid", "investigation-tape.json state must be closed")

    _validate_extracted_views(package, tape)

    handoff = deepcopy(package["edr-handoff.json"])
    try:
        expected_handoff = derive_handoff(tape)
    except ZovarkValidationError as exc:
        raise ZovarkValidationError(
            f"handoff_mismatch: could not derive handoff: {exc}"
        ) from exc
    if handoff != expected_handoff:
        _fail("handoff_mismatch", "edr-handoff.json does not match derived handoff")
    _validate_handoff_tape_links(tape, handoff)

    with_handoff = deepcopy(tape)
    with_handoff["handoff"] = handoff
    audit_entry = deepcopy(package["audit-chain-entry.json"])
    if not isinstance(audit_entry, dict):
        _fail("audit_chain_mismatch", "audit-chain-entry.json must be an object")
    if (
        audit_entry.get("sequence") != 1
        or audit_entry.get("prev_entry_hash") != GENESIS_HASH
    ):
        _fail("audit_genesis_mismatch", "first audit entry must anchor to genesis")
    try:
        expected_audit_entry = derive_audit_entry(with_handoff)
    except ZovarkValidationError as exc:
        raise ZovarkValidationError(
            f"audit_chain_mismatch: could not derive audit entry: {exc}"
        ) from exc
    if audit_entry != expected_audit_entry:
        _fail(
            "audit_chain_mismatch",
            "audit-chain-entry.json does not match derived audit entry",
        )

    sealed_tape = deepcopy(with_handoff)
    sealed_tape["audit_entry"] = audit_entry

    replay_report = deepcopy(package["replay-report.json"])
    try:
        expected_replay_report = derive_replay_report(sealed_tape)
    except ZovarkValidationError as exc:
        raise ZovarkValidationError(
            f"replay_report_mismatch: could not derive replay report: {exc}"
        ) from exc
    if replay_report != expected_replay_report:
        _fail(
            "replay_report_mismatch",
            "replay-report.json does not match derived replay report",
        )

    full_tape = deepcopy(sealed_tape)
    full_tape["replay_report"] = replay_report
    return full_tape


def _validate_extracted_views(
    package: dict[str, Any],
    tape: dict[str, Any],
) -> None:
    expected_views = {
        "evidence-ledger.json": "raw_evidence",
        "timeline.json": "timeline",
        "findings.json": "findings",
        "verdict.json": "verdict",
    }
    for filename, tape_field in expected_views.items():
        if tape_field not in tape:
            _fail(
                "extracted_view_mismatch",
                f"investigation-tape.json is missing {tape_field}",
            )
        if package[filename] != tape[tape_field]:
            _fail(
                "extracted_view_mismatch",
                f"{filename} does not match investigation tape",
            )


def _validate_handoff_tape_links(
    tape: dict[str, Any],
    handoff: dict[str, Any],
) -> None:
    try:
        handoff_id = handoff["handoff_id"]
        expected_summary = {
            "action_type": handoff["action_type"],
            "approval_mode": handoff["approval_mode"],
            "execution_status": handoff["execution_result"]["status"],
            "target": {
                "identifier": handoff["target"]["identifier"],
                "kind": handoff["target"]["kind"],
            },
        }
    except (KeyError, TypeError) as exc:
        raise ZovarkValidationError(
            "handoff_link_mismatch: edr-handoff.json link fields are invalid"
        ) from exc

    if tape.get("handoff_ref") != handoff_id:
        _fail("handoff_link_mismatch", "investigation-tape handoff_ref is invalid")
    if tape.get("handoff_summary") != expected_summary:
        _fail(
            "handoff_link_mismatch",
            "investigation-tape handoff_summary is invalid",
        )


def _validate_customer_report(
    package: dict[str, Any],
    full_tape: dict[str, Any],
) -> None:
    try:
        expected_report = render_customer_report(full_tape)
    except ZovarkValidationError as exc:
        raise ZovarkValidationError(
            f"customer_report_mismatch: could not render customer report: {exc}"
        ) from exc
    if package["customer-report.md"] != expected_report:
        _fail(
            "customer_report_mismatch",
            "customer-report.md does not match derived report",
        )


def _verification_summary(full_tape: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_count": len(EXPECTED_OUTPUT_FILES),
        "audit_entry_id": full_tape["audit_entry"]["entry_id"],
        "checks_passed": len(_VERIFIED_COMPONENTS),
        "customer_report_verified": True,
        "evidence_entries_checked": len(full_tape["raw_evidence"]),
        "failure_codes": [],
        "failure_count": 0,
        "handoff_id": full_tape["handoff"]["handoff_id"],
        "package_contract": "slice-001-proof-package/1.0",
        "replay_id": full_tape["replay_report"]["replay_state"]["replay_id"],
        "replay_state": full_tape["replay_report"]["replay_state"]["state"],
        "status": "verified",
        "tape_id": full_tape["tape_id"],
        "verdict": full_tape["verdict"]["value"],
        "verified_components": list(_VERIFIED_COMPONENTS),
    }


def _derive_v2_conditions(full_tape: dict[str, Any]) -> dict[str, bool]:
    handoff = full_tape["handoff"]
    action_type = handoff["action_type"]
    if action_type not in (
        _VERIFIED_RESPONSE_ACTION_TYPES | _VERIFIED_NON_RESPONSE_ACTION_TYPES
    ):
        _fail(
            "v2_condition_mismatch",
            "V2 conditions cannot be derived from verified action evidence",
        )
    raw_contexts = _v3_trace_contexts(full_tape)
    verdict_value = full_tape["verdict"]["value"]

    # The skeleton marker key is named for benign verdicts, but it gates
    # false_positive_reasoning, which the V2 contract also requires for
    # low-confidence outcomes.
    return {
        "analyst_override_present": _context_has_non_empty_key(
            raw_contexts,
            "analyst_override",
        ),
        "benign_verdict": _verdict_requires_false_positive_reasoning(verdict_value),
        "containment_recommended": action_type in _VERIFIED_CONTAINMENT_ACTION_TYPES,
        "context_enrichment_used": _context_has_non_empty_key(
            raw_contexts,
            "context_enrichment",
            "institutional_knowledge",
            "correlation_history",
        )
        or _context_tool_name_matches(
            raw_contexts,
            "lookup_institutional_knowledge",
            "correlate_with_history",
        ),
        "customer_impact_language_present": _handoff_has_blast_radius(handoff),
        "rejected_findings_present": _context_has_non_empty_key(
            raw_contexts,
            "rejected_findings",
        ),
        "response_action_present": action_type in _VERIFIED_RESPONSE_ACTION_TYPES,
    }


def _verdict_requires_false_positive_reasoning(verdict_value: str) -> bool:
    if verdict_value in _FALSE_POSITIVE_REASONING_VERDICTS:
        return True
    if verdict_value in _VERDICTS_WITHOUT_FALSE_POSITIVE_TRIGGER:
        return False
    if verdict_value not in APPROVED_VERDICTS:
        _fail(
            "v2_verdict_unclassified",
            "V2 false-positive requirement cannot classify verdict",
        )
    _fail(
        "v2_verdict_unclassified",
        "V2 false-positive requirement is undefined for verdict",
    )


def _trusted_reference_index(full_tape: dict[str, Any]) -> frozenset[str]:
    refs: set[str] = set()

    for filename in EXPECTED_OUTPUT_FILES:
        refs.add(f"artifact:{filename}")

    _add_ref_aliases(refs, full_tape["tape_id"], "tape")
    _add_ref_aliases(refs, full_tape["audit_entry"]["entry_id"], "audit")
    _add_ref_aliases(refs, full_tape["handoff"]["handoff_id"], "handoff")
    _add_ref_aliases(
        refs,
        full_tape["replay_report"]["replay_state"]["replay_id"],
        "replay",
    )
    for optional_key in ("source_alert_ref", "audit_ref", "handoff_ref"):
        value = full_tape.get(optional_key)
        if isinstance(value, str) and value:
            refs.add(value)

    for entry in full_tape["raw_evidence"]:
        evidence_id = entry["evidence_id"]
        _add_ref_aliases(refs, evidence_id, "evidence")
        raw_content = entry.get("raw_content", {})
        if isinstance(raw_content, dict):
            _collect_recorded_refs(raw_content, refs)

    for timeline_event in full_tape["timeline"]:
        if isinstance(timeline_event, dict):
            _collect_recorded_refs(timeline_event, refs)

    for finding in full_tape["findings"]:
        if isinstance(finding, dict):
            _collect_recorded_refs(finding, refs)

    _collect_recorded_refs(full_tape["verdict"], refs)
    _collect_recorded_refs(full_tape["handoff"], refs)
    return frozenset(refs)


def _add_ref_aliases(refs: set[str], value: Any, prefix: str) -> None:
    if isinstance(value, str) and value:
        refs.add(value)
        refs.add(f"{prefix}:{value}")


def _collect_recorded_refs(value: Any, refs: set[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if _is_reference_key(key):
                _add_recorded_ref_value(child, refs)
            _collect_recorded_refs(child, refs)
    elif isinstance(value, list):
        for child in value:
            _collect_recorded_refs(child, refs)


def _is_reference_key(key: str) -> bool:
    return (
        key.endswith("_id")
        or key.endswith("_ids")
        or key.endswith("_ref")
        or key.endswith("_refs")
        or key in {"record_id", "capability_refs", "trace_record_refs"}
    )


def _add_recorded_ref_value(value: Any, refs: set[str]) -> None:
    if isinstance(value, str) and value:
        refs.add(value)
    elif isinstance(value, list):
        for item in value:
            _add_recorded_ref_value(item, refs)
    elif isinstance(value, dict):
        _collect_recorded_refs(value, refs)


def _v3_trace_contexts(full_tape: dict[str, Any]) -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []
    for entry in full_tape["raw_evidence"]:
        raw_content = entry.get("raw_content", {})
        if not isinstance(raw_content, dict):
            continue
        context = raw_content.get("v3_trace_context")
        if isinstance(context, dict):
            contexts.append(context)
    return contexts


def _context_has_non_empty_key(
    contexts: list[dict[str, Any]],
    *keys: str,
) -> bool:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if value not in (None, False, [], {}, ""):
                return True
    return False


def _context_tool_name_matches(
    contexts: list[dict[str, Any]],
    *tool_names: str,
) -> bool:
    expected = set(tool_names)
    for context in contexts:
        names = context.get("tool_names", [])
        if isinstance(names, list) and any(name in expected for name in names):
            return True
    return False


def _handoff_has_blast_radius(handoff: dict[str, Any]) -> bool:
    blast_radius = handoff["blast_radius"]
    return any(
        blast_radius.get(key)
        for key in (
            "directly_affected",
            "lateral_movement_blocked",
            "services_at_risk",
        )
    )


def _validate_v2_marker(
    marker: dict[str, Any],
    derived_conditions: dict[str, bool],
    trusted_refs: frozenset[str],
) -> dict[str, Any]:
    if marker.get("package_version") != V2_PACKAGE_CONTRACT:
        _fail(
            "v2_package_shape_invalid",
            f"{V2_MARKER_FILE} package_version is unsupported",
        )
    if marker.get("base_package_contract") != "slice-001-proof-package/1.0":
        _fail(
            "v2_package_shape_invalid",
            f"{V2_MARKER_FILE} base_package_contract is invalid",
        )

    conditions = marker.get("conditions")
    if not isinstance(conditions, dict):
        _fail("v2_package_shape_invalid", "V2 conditions must be an object")
    if set(conditions) != set(_V2_CONDITION_KEYS):
        _fail(
            "v2_package_shape_invalid",
            "V2 conditions must include the expected condition flags",
        )
    for key in _V2_CONDITION_KEYS:
        if not isinstance(conditions[key], bool):
            _fail("v2_package_shape_invalid", "V2 conditions must be booleans")
    if conditions != derived_conditions:
        _fail(
            "v2_condition_mismatch",
            "V2 declared conditions do not match verified package evidence",
        )

    objects = marker.get("objects")
    if not isinstance(objects, dict):
        _fail("v2_package_shape_invalid", "V2 objects must be an object")

    for object_name in _V2_REQUIRED_OBJECTS:
        if object_name not in objects:
            _fail(
                "v2_required_object_missing",
                f"V2 object {object_name} is required",
            )

    condition_required_objects: set[str] = set()
    for object_name, condition_keys in _V2_CONDITIONAL_OBJECTS.items():
        if any(derived_conditions[condition_key] for condition_key in condition_keys):
            condition_required_objects.add(object_name)
            if object_name not in objects:
                _fail(
                    "v2_conditional_object_missing",
                    f"V2 object {object_name} is required by verified package evidence",
                )

    required_envelope_objects = set(_V2_REQUIRED_OBJECTS) | condition_required_objects
    for object_name, obj in objects.items():
        if object_name not in _V2_KNOWN_OBJECTS:
            _fail(
                "v2_object_shape_invalid",
                f"V2 object {object_name} is unsupported",
            )
        _validate_v2_object(
            object_name,
            obj,
            trusted_refs,
            required_envelope=object_name in required_envelope_objects,
        )
    return objects


def _validate_v2_object(
    object_name: str,
    obj: Any,
    trusted_refs: frozenset[str],
    *,
    required_envelope: bool,
) -> None:
    if not isinstance(obj, dict):
        _fail("v2_object_shape_invalid", f"V2 object {object_name} must be an object")
    if obj.get("object_type") != object_name:
        _fail(
            "v2_object_shape_invalid",
            f"V2 object {object_name} has invalid object_type",
        )
    if not isinstance(obj.get("object_version"), str) or not obj["object_version"]:
        _fail(
            "v2_object_shape_invalid",
            f"V2 object {object_name} must have object_version",
        )
    status = obj.get("status")
    if status not in _V2_OBJECT_STATUSES:
        _fail("v2_object_shape_invalid", f"V2 object {object_name} has invalid status")
    if required_envelope and status == "not_applicable":
        _fail(
            "v2_required_object_not_applicable",
            f"V2 object {object_name} is required by verified package evidence",
        )
    if not isinstance(obj.get("source_refs"), list):
        _fail(
            "v2_object_shape_invalid",
            f"V2 object {object_name} must have source_refs",
        )
    _validate_v2_source_refs(
        object_name,
        obj,
        trusted_refs,
        required_envelope=required_envelope,
    )
    if "object_hash" in obj and obj["object_hash"] is not None and not isinstance(
        obj["object_hash"], str
    ):
        _fail(
            "v2_object_shape_invalid",
            f"V2 object {object_name} has invalid object_hash",
        )

    needs_reason = status in {"partial", "unavailable"} or _contains_null_value(obj)
    if needs_reason and (
        not isinstance(obj.get("data_unavailable_reason"), str)
        or not obj["data_unavailable_reason"]
    ):
        _fail(
            "v2_unavailable_reason_missing",
            f"V2 object {object_name} requires data_unavailable_reason",
        )


def _validate_v2_source_refs(
    object_name: str,
    obj: dict[str, Any],
    trusted_refs: frozenset[str],
    *,
    required_envelope: bool,
) -> None:
    source_refs = obj["source_refs"]
    if not source_refs:
        if required_envelope:
            _fail(
                "v2_required_object_source_refs_missing",
                f"V2 object {object_name} must cite verified source refs",
            )
        if obj["status"] in {"not_applicable", "unavailable"}:
            return
        _fail(
            "v2_source_ref_unresolved",
            f"V2 object {object_name} must cite verified source refs",
        )

    for source_ref in source_refs:
        if not isinstance(source_ref, str) or not source_ref:
            _fail(
                "v2_source_ref_unresolved",
                f"V2 object {object_name} has invalid source_ref",
            )
        if source_ref not in trusted_refs:
            _fail(
                "v2_source_ref_unresolved",
                f"V2 object {object_name} source_ref does not resolve",
            )


def _contains_null_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, dict):
        return any(
            _contains_null_value(child)
            for key, child in value.items()
            if key != "object_hash"
        )
    if isinstance(value, list):
        return any(_contains_null_value(child) for child in value)
    return False


def _v2_verification_summary(
    base_summary: dict[str, Any],
    objects: dict[str, Any],
) -> dict[str, Any]:
    summary = dict(base_summary)
    summary.update(
        {
            "base_package_contract": base_summary["package_contract"],
            "checks_passed": len(_V2_VERIFIED_COMPONENTS),
            "package_contract": V2_PACKAGE_CONTRACT,
            "package_version": V2_PACKAGE_CONTRACT,
            "v2_object_count": len(objects),
            "v2_objects_checked": sorted(objects),
            "verified_components": list(_V2_VERIFIED_COMPONENTS),
        }
    )
    return summary


def _fail(code: str, message: str) -> NoReturn:
    raise ZovarkValidationError(f"{code}: {message}")

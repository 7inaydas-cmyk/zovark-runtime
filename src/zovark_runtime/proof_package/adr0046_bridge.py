"""Additive bridge: proof-package tape -> ADR-0046 verdict contract (Slice 3).

This module is a NON-LOSSY, ADDITIVE mapping. It does not change proof-package
generation, the proof-package verdict, or `proof-package-verify` (which remains the
semantic authority). It reuses the repo's existing ADR-0046 code paths
(`verdict_derivation.derive_verdict`, `replay_validation.validate_replay_record`) and
their canonical hash helpers — it introduces no parallel verdict/verifier engine.

Relationship between the two contracts (documented, not reconciled):
- The proof-package rule verdict (e.g. ``confirmed_malicious``) is authoritative for the
  proof package and is left untouched.
- ADR-0046 `derive_verdict` is, in this repo today, a proof-fixture stub that always
  emits ``verdict_class="indeterminate"`` regardless of evidence. The bridge runs it
  as-is; it does NOT map the slice001 rule verdict into ``verdict_class``. The
  authoritative proof-package verdict is carried, labeled, in the bridge result so
  nothing is silently lost.
- The bridge artifacts are emitted to a SEPARATE directory and are never added to the
  canonical 9-artifact proof package; `main`'s proof-package bytes are unchanged.

A no-model, no-tool, no-db deterministic investigation is represented honestly: the
ADR-0046 investigation-I/O arrays (`tool_results`, `llm_records`, `db_results`,
`llm_io`, `tool_io`, `db_snapshots`) are EMPTY. The required scalar model/tool fields
carry documented no-model placeholders (they describe the absence of a model run).
No network, no model, no wall-clock: all values derive from the recorded tape.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from zovark_runtime.proof_package import ZovarkValidationError
from zovark_runtime.replay_validation import (
    ReplayValidationResult,
    canonical_sha256_hex,
    validate_replay_record,
)
from zovark_runtime.verdict_derivation import derive_verdict

# Fixed namespace for deterministic (uuid5) identity mapping. Not a secret.
_NS = uuid.uuid5(uuid.NAMESPACE_URL, "zovark-runtime/proof_package/adr0046_bridge/v1")

# OCSF severity_id mapping (1=Informational .. 5=Critical).
_SEVERITY_ID = {"info": 1, "low": 2, "medium": 3, "high": 4, "critical": 5}

# No-model placeholders (describe the absence of a model invocation in a contract whose
# scalars are required). The investigation-I/O arrays are empty, which is the honest
# signal that no model/tool/db ran.
_NO_MODEL_VERSION = "1.0.0"
_NO_MODEL_ID = "slice001-no-model"
_NO_TOOL_CATALOG_VERSION = "slice001-no-tools-1.0.0"
_NO_MODEL_DECODING = {
    "temperature_basis_points": 0,
    "top_p_basis_points": 10000,
    "max_output_tokens": 512,
    "seed_policy": "no_seed",
}


def _det_uuid(label: str, value: str) -> str:
    return str(uuid.uuid5(_NS, f"{label}:{value}"))


def _iso_utc_to_ns(timestamp: str) -> int:
    """Deterministically convert an ISO-8601 UTC 'Z' timestamp to epoch nanoseconds.

    Parses a RECORDED string (not wall-clock). Fails closed on a malformed timestamp.
    """
    try:
        dt = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError) as exc:
        raise ZovarkValidationError(f"adr0046_bridge: invalid ISO-8601 UTC timestamp: {timestamp!r}") from exc
    return int(dt.timestamp()) * 1_000_000_000


def _alert_evidence(tape: dict[str, Any]) -> dict[str, Any]:
    for entry in tape.get("raw_evidence", []):
        if isinstance(entry, dict) and entry.get("source_type") == "edr_alert":
            return entry
    raise ZovarkValidationError("adr0046_bridge: tape has no edr_alert evidence")


def tape_to_verdict_input(tape: dict[str, Any]) -> dict[str, Any]:
    """Map a proof-package tape to an ADR-0046 verdict_input (deterministic, schema-valid).

    Investigation-I/O arrays are empty (no model/tool/db ran). UUID-format ids are derived
    deterministically from the tape's stable identifiers.
    """
    if not isinstance(tape, dict):
        raise ZovarkValidationError("adr0046_bridge: tape must be an object")
    tenant = tape.get("tenant_id")
    tape_id = tape.get("tape_id")
    if not isinstance(tenant, str) or not tenant or not isinstance(tape_id, str) or not tape_id:
        raise ZovarkValidationError("adr0046_bridge: tape missing tenant_id/tape_id")

    alert_entry = _alert_evidence(tape)
    alert = alert_entry["raw_content"]
    alert_id = str(alert.get("alert_id") or alert_entry["evidence_id"])
    severity = str(alert.get("severity", "medium")).lower()
    severity_id = _SEVERITY_ID.get(severity, 3)
    observed_ns = _iso_utc_to_ns(str(alert.get("timestamp") or tape["created_at"]))
    description = str(alert.get("description") or "EDR alert")

    tenant_uuid = _det_uuid("tenant", tenant)
    investigation_uuid = _det_uuid("investigation", tape_id)
    envelope_uuid = _det_uuid("envelope", alert_entry["evidence_id"])

    policy_snapshot_version = _policy_snapshot_version(tape)

    verdict_input = {
        "schema_version": "1.0.0",
        "tenant_id": tenant_uuid,
        "investigation_id": investigation_uuid,
        "logical_clock": len(tape.get("raw_evidence", [])),
        "alert_envelope": {
            "envelope_id": envelope_uuid,
            "tenant_id": tenant_uuid,
            "received_at_ns": observed_ns,
            "scanner_type": "edr",
            "scanner_version": "1.0.0",
            "ocsf_class": 4002,
            "raw_finding": {
                "source_finding_id": alert_id,
                "source_event_uid": alert_id,
                "title": description,
                "description": description,
                "severity": severity if severity in _SEVERITY_ID else "medium",
                "observed_at_ns": observed_ns,
            },
            "normalized_finding": {
                "ocsf_class_uid": 4002,
                "category_uid": 4,
                "type_uid": 400201,
                "activity_id": 1,
                "severity_id": severity_id,
                "finding_uid": alert_id,
            },
            "ingest_provenance": {"adapter": "proof-package", "adapter_version": "1.0.0"},
        },
        "tenant_config": {
            "config_version": "1.0.0",
            "policy_snapshot_version": policy_snapshot_version,
            "allowed_action_classes": ["no_op"],
            "blocked_action_classes": [],
            "policy_hash": canonical_sha256_hex({"policy_snapshot_version": policy_snapshot_version}),
        },
        "tool_catalog_version": _NO_TOOL_CATALOG_VERSION,
        "tool_results": [],
        "llm_records": [],
        "db_results": [],
        "model_version": _NO_MODEL_VERSION,
        "decoding_params": dict(_NO_MODEL_DECODING),
        "prompt_hash": canonical_sha256_hex({"slice001_no_model_prompt": tape_id}),
    }
    return verdict_input


def _policy_snapshot_version(tape: dict[str, Any]) -> str:
    summary = tape.get("handoff_summary")
    # The proof-package handoff carries a policy_snapshot_version; tape summary does not,
    # so use a stable bridge default that mirrors the proof-package bootstrap policy.
    if isinstance(summary, dict):
        psv = summary.get("policy_snapshot_version")
        if isinstance(psv, str) and psv:
            return psv
    return "0.0.1-bootstrap"


def build_replay_record(verdict_input: dict[str, Any], verdict_envelope: dict[str, Any]) -> dict[str, Any]:
    """Build a deterministic replay_record that `validate_replay_record` accepts."""
    return {
        "schema_version": "1.0.0",
        "record_format_version": "1.0.0",
        "investigation_id": verdict_input["investigation_id"],
        "tenant_id": verdict_input["tenant_id"],
        "captured_logical_clock": verdict_input["logical_clock"],
        "replay_compatibility_contract": "architecture/replay-compatibility.yaml",
        "failure_policy": "fail_closed",
        "tool_catalog_version": verdict_input["tool_catalog_version"],
        "model_id": _NO_MODEL_ID,
        "model_version": verdict_input["model_version"],
        "decoding_params": dict(verdict_input["decoding_params"]),
        "prompt_hashes": [verdict_input["prompt_hash"]],
        "verdict_input": verdict_input,
        "verdict_input_hash": canonical_sha256_hex(verdict_input),
        "llm_io": [],
        "tool_io": [],
        "db_snapshots": [],
        "verdict_envelope_hash": canonical_sha256_hex(verdict_envelope),
    }


def build_bridge(tape: dict[str, Any]) -> dict[str, Any]:
    """Build all ADR-0046 bridge artifacts from a proof-package tape, and self-validate.

    Returns the verdict_input, the (stub) verdict_envelope, the replay_record, the
    offline replay-validation result, and the AUTHORITATIVE proof-package verdict.
    Raises if `validate_replay_record` does not accept the freshly built record.
    """
    verdict_input = tape_to_verdict_input(tape)
    verdict_envelope = derive_verdict(verdict_input)
    replay_record = build_replay_record(verdict_input, verdict_envelope)
    result: ReplayValidationResult = validate_replay_record(replay_record, verdict_input, verdict_envelope)
    if not result.ok:
        raise ZovarkValidationError(f"adr0046_bridge: built replay_record failed validation: {result.code} {result.detail}")

    proof_verdict = tape.get("verdict", {})
    return {
        "schema": "zovark-adr0046-bridge/v1",
        "relationship_note": (
            "proof-package verdict is authoritative; ADR-0046 verdict_class is a "
            "proof-fixture stub (always 'indeterminate') and is NOT the proof-package "
            "verdict. See docs/slices/ADR0046_BRIDGE.md."
        ),
        "proof_package_verdict": {
            "value": proof_verdict.get("value"),
            "signing_tag": proof_verdict.get("signing_tag"),
        },
        "verdict_input": verdict_input,
        "verdict_envelope": verdict_envelope,
        "replay_record": replay_record,
        "replay_validation": {"ok": result.ok, "code": result.code, "detail": result.detail},
    }


def write_bridge(tape: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    """Write the bridge artifacts to a SEPARATE directory (never the canonical package)."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    bridge = build_bridge(tape)
    files = {
        "verdict_input.json": bridge["verdict_input"],
        "verdict_envelope.json": bridge["verdict_envelope"],
        "replay_record.json": bridge["replay_record"],
        "bridge.json": bridge,
    }
    written: dict[str, str] = {}
    for name, obj in files.items():
        dest = out / name
        dest.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written[name] = str(dest)
    return written


def load_tape(package_dir: str | Path) -> dict[str, Any]:
    """Load the investigation-tape.json from a generated proof-package directory."""
    path = Path(package_dir) / "investigation-tape.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ZovarkValidationError(f"adr0046_bridge: cannot read {path}: {exc}") from exc

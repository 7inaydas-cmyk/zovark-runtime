"""Slice 8 — runtime (dependency-free) schema enforcement + proof-status.

Schema enforcement is a fail-closed SHAPE gate; proof-package-verify re-derivation remains
the semantic authority (a shape-valid semantic forgery is still rejected). proof-status
never reports a false complete runtime_proof_loop.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from zovark_runtime.proof_package import ZovarkValidationError
from zovark_runtime.proof_package.pipeline import run_proof_package
from zovark_runtime.proof_package.schema_enforce import (
    ARTIFACT_SCHEMAS,
    enforce_proof_package_schemas,
    validate_artifact,
)
from zovark_runtime.proof_package.verify import verify_proof_package_strict

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "edr-sample-001.json"
CONTRACTS = ROOT / "contracts" / "proof_package"

jsonschema = pytest.importorskip("jsonschema")
Draft202012Validator = jsonschema.Draft202012Validator


def _pkg(tmp_path):
    out = tmp_path / "pkg"
    run_proof_package(FIXTURE, out, tenant_id="tenant-001")
    return out


def test_enforce_accepts_canonical_package(tmp_path):
    out = _pkg(tmp_path)
    result = enforce_proof_package_schemas(out)
    assert set(result) == set(ARTIFACT_SCHEMAS)
    assert all(v == "ok" for v in result.values())


def test_minivalidator_parity_with_jsonschema(tmp_path):
    # On the canonical artifacts, the dependency-free validator agrees with jsonschema
    # (both accept).
    out = _pkg(tmp_path)
    for artifact_name, schema_name in ARTIFACT_SCHEMAS.items():
        artifact = json.loads((out / artifact_name).read_text())
        schema = json.loads((CONTRACTS / schema_name).read_text())
        js_errors = list(Draft202012Validator(schema).iter_errors(artifact))
        mini_errors = validate_artifact(artifact, schema_name)
        assert js_errors == [] and mini_errors == [], (artifact_name, mini_errors, [e.message for e in js_errors])


@pytest.mark.parametrize("mutation", ["drop_required", "wrong_type", "extra_key", "bad_enum"])
def test_enforce_fails_closed_on_invalid_artifact(tmp_path, mutation):
    out = _pkg(tmp_path)
    verdict = json.loads((out / "verdict.json").read_text())
    if mutation == "drop_required":
        del verdict["value"]
    elif mutation == "wrong_type":
        verdict["evidence_refs"] = "not-a-list"
    elif mutation == "extra_key":
        verdict["surprise"] = 1
    elif mutation == "bad_enum":
        verdict["value"] = "totally-made-up-verdict"
    (out / "verdict.json").write_text(json.dumps(verdict, indent=2) + "\n")
    with pytest.raises(ZovarkValidationError):
        enforce_proof_package_schemas(out)
    # And the full verify gate also fails closed.
    with pytest.raises(ZovarkValidationError):
        verify_proof_package_strict(out)


def test_schema_valid_forgery_still_rejected_by_rederivation(tmp_path):
    # Necessary-not-sufficient: a SHAPE-VALID forged findings set passes schema enforcement
    # but the re-derivation in verify still rejects it.
    from zovark_runtime.proof_package.ingest import normalize_evidence
    from zovark_runtime.proof_package.tape import create_tape
    from zovark_runtime.proof_package.timeline import build_initial_timeline, attach_timeline
    from zovark_runtime.proof_package.findings import attach_findings
    from zovark_runtime.proof_package.verdict import derive_verdict, attach_verdict
    from zovark_runtime.proof_package.handoff import derive_handoff, attach_handoff
    from zovark_runtime.proof_package.audit import derive_audit_entry, attach_audit_entry
    from zovark_runtime.proof_package.replay import derive_replay_report, attach_replay_report
    from zovark_runtime.proof_package.writer import write_proof_package

    raw = json.loads(FIXTURE.read_text())
    ev = normalize_evidence(raw)
    tape = create_tape(raw, ev, tenant_id="tenant-001")
    tape = attach_timeline(tape, build_initial_timeline(tape))
    forged = [{"evidence_refs": [ev[0]["evidence_id"]], "model_contribution": False,
               "severity": "low", "rule_id": "RULE-FORGED", "mitre_technique": "T0000",
               "title": "forged"}]
    tape = attach_findings(tape, forged, False)
    tape = attach_verdict(tape, derive_verdict(tape))
    tape["audit_ref"] = "audit-entry-1"
    tape = attach_handoff(tape, derive_handoff(tape))
    tape = attach_audit_entry(tape, derive_audit_entry(tape))
    tape = attach_replay_report(tape, derive_replay_report(tape))
    out = tmp_path / "forge"
    write_proof_package(tape, out)
    # Shape gate PASSES (the forgery is well-formed)...
    assert enforce_proof_package_schemas(out)  # no raise
    # ...but the semantic authority (re-derivation) still rejects it.
    with pytest.raises(ZovarkValidationError):
        verify_proof_package_strict(out)


def test_bool_does_not_satisfy_numeric_const_or_enum(tmp_path):
    # Regression (independent-audit Slice 8 F1): True must NOT satisfy a numeric const/enum.
    # Forged audit-chain-entry.json with sequence: true must be rejected by the schema gate
    # AND the full verify gate (jsonschema parity: bool is a distinct type).
    out = _pkg(tmp_path)
    audit = json.loads((out / "audit-chain-entry.json").read_text())
    audit["sequence"] = True  # was const 1; True == 1 in plain Python equality
    (out / "audit-chain-entry.json").write_text(json.dumps(audit, indent=2) + "\n")
    assert validate_artifact(audit, "audit-chain-entry.schema.json"), "bool must fail numeric const"
    # jsonschema parity
    schema = json.loads((CONTRACTS / "audit-chain-entry.schema.json").read_text())
    assert list(Draft202012Validator(schema).iter_errors(audit)), "jsonschema must also reject"
    with pytest.raises(ZovarkValidationError):
        enforce_proof_package_schemas(out)
    with pytest.raises(ZovarkValidationError):
        verify_proof_package_strict(out)


def test_proof_status_never_falsely_complete():
    from zovark_runtime.proof_status import build_proof_status
    payload, _exit = build_proof_status()
    # ADR-0053 / runtime_proof_loop completion authority is not present in runtime; status
    # must not claim complete.
    assert payload.get("runtime_proof_loop") != "complete"


def test_generation_enforces_schemas_and_stays_deterministic(tmp_path):
    # Generation runs the enforcement gate (would raise on invalid) and remains deterministic.
    a, b = tmp_path / "a", tmp_path / "b"
    run_proof_package(FIXTURE, a, tenant_id="tenant-001")
    run_proof_package(FIXTURE, b, tenant_id="tenant-001")
    names = list(ARTIFACT_SCHEMAS) + ["customer-report.md"]
    assert all((a / n).read_bytes() == (b / n).read_bytes() for n in names)

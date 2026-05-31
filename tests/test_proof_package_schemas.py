"""Slice 2 — proof-package JSON Schemas.

These schemas check artifact SHAPE only. They are consistent with, but NOT a
replacement for, `proof-package-verify`, which remains the semantic security boundary
(it re-derives evidence hashes -> findings -> verdict and fails closed on mismatch).
This module proves: (1) each schema is a valid Draft 2020-12 metaschema; (2) every
artifact the generator emits validates against its schema; (3) shape and semantics are
distinct layers — a shape-corrupt artifact fails schema validation, while a
well-shaped but semantically-forged package passes the schemas yet is rejected by the
verifier.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")
Draft202012Validator = jsonschema.Draft202012Validator

from zovark_runtime.proof_package import ZovarkValidationError
from zovark_runtime.proof_package.audit import attach_audit_entry, derive_audit_entry
from zovark_runtime.proof_package.handoff import attach_handoff, derive_handoff
from zovark_runtime.proof_package.ingest import normalize_evidence
from zovark_runtime.proof_package.pipeline import run_proof_package
from zovark_runtime.proof_package.replay import attach_replay_report, derive_replay_report
from zovark_runtime.proof_package.tape import create_tape
from zovark_runtime.proof_package.timeline import attach_timeline, build_initial_timeline
from zovark_runtime.proof_package.findings import attach_findings
from zovark_runtime.proof_package.verdict import attach_verdict, derive_verdict
from zovark_runtime.proof_package.verify import verify_proof_package_strict
from zovark_runtime.proof_package.writer import write_proof_package

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "contracts" / "proof_package"
FIXTURE = ROOT / "tests" / "fixtures" / "edr-sample-001.json"

# artifact filename (without .json) -> schema filename. The 9th artifact,
# customer-report.md, is Markdown and intentionally has NO JSON Schema.
ARTIFACT_SCHEMAS = {
    "investigation-tape": "investigation-tape.schema.json",
    "evidence-ledger": "evidence-ledger.schema.json",
    "timeline": "timeline.schema.json",
    "findings": "findings.schema.json",
    "verdict": "verdict.schema.json",
    "edr-handoff": "edr-handoff.schema.json",
    "audit-chain-entry": "audit-chain-entry.schema.json",
    "replay-report": "replay-report.schema.json",
}


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _schema(name: str) -> dict:
    return _load(SCHEMA_DIR / ARTIFACT_SCHEMAS[name])


def test_exactly_eight_schemas_no_markdown_schema() -> None:
    files = sorted(p.name for p in SCHEMA_DIR.glob("*.schema.json"))
    assert files == sorted(ARTIFACT_SCHEMAS.values())
    assert len(files) == 8
    assert not (SCHEMA_DIR / "customer-report.schema.json").exists()


def test_schemas_are_valid_draft202012_metaschema() -> None:
    for name in ARTIFACT_SCHEMAS:
        schema = _schema(name)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        Draft202012Validator.check_schema(schema)  # raises on an invalid schema


def test_generated_artifacts_validate_against_schemas(tmp_path: Path) -> None:
    out = tmp_path / "pkg"
    run_proof_package(FIXTURE, out, tenant_id="tenant-001")
    for name in ARTIFACT_SCHEMAS:
        artifact = _load(out / f"{name}.json")
        errors = sorted(
            Draft202012Validator(_schema(name)).iter_errors(artifact),
            key=lambda e: e.path,
        )
        assert errors == [], f"{name}.json failed its schema: {[e.message for e in errors]}"


def test_valid_package_passes_both_schemas_and_verifier(tmp_path: Path) -> None:
    # Consistency: a genuine package satisfies the shape schemas AND the semantic verifier.
    out = tmp_path / "pkg"
    run_proof_package(FIXTURE, out, tenant_id="tenant-001")
    for name in ARTIFACT_SCHEMAS:
        Draft202012Validator(_schema(name)).validate(_load(out / f"{name}.json"))
    assert verify_proof_package_strict(out)["status"] == "verified"


def test_shape_corruption_fails_schema(tmp_path: Path) -> None:
    # Dropping a required field is a SHAPE violation -> schema rejects it.
    out = tmp_path / "pkg"
    run_proof_package(FIXTURE, out, tenant_id="tenant-001")
    verdict = _load(out / "verdict.json")
    del verdict["signing_tag"]
    errors = list(Draft202012Validator(_schema("verdict")).iter_errors(verdict))
    assert errors, "schema should reject a verdict missing a required field"


def test_semantic_forgery_passes_schema_but_verifier_rejects(tmp_path: Path) -> None:
    # The key consistency claim: schemas are shape-only; the verifier is the semantic
    # boundary. A well-shaped package whose findings were forged (malicious evidence
    # downgraded to benign) PASSES every schema but is REJECTED by proof-package-verify.
    raw = json.loads(FIXTURE.read_text())
    evidence = normalize_evidence(raw)
    tape = create_tape(raw, evidence, tenant_id="tenant-001")
    tape = attach_timeline(tape, build_initial_timeline(tape))
    forged = [
        {
            "evidence_refs": [evidence[0]["evidence_id"]],
            "model_contribution": False,
            "severity": "low",
            "rule_id": "RULE-FORGED",
            "mitre_technique": "T0000",
            "title": "Routine activity (forged)",
        }
    ]
    tape = attach_findings(tape, forged, False)
    tape = attach_verdict(tape, derive_verdict(tape))
    tape["audit_ref"] = "audit-entry-1"
    tape = attach_handoff(tape, derive_handoff(tape))
    tape = attach_audit_entry(tape, derive_audit_entry(tape))
    tape = attach_replay_report(tape, derive_replay_report(tape))
    out = tmp_path / "forged"
    write_proof_package(tape, out)

    # Shape layer: every artifact still validates (the forgery is well-formed)...
    for name in ARTIFACT_SCHEMAS:
        Draft202012Validator(_schema(name)).validate(_load(out / f"{name}.json"))
    assert _load(out / "verdict.json")["value"] == "benign"
    # ...but the semantic boundary rejects it.
    with pytest.raises(ZovarkValidationError):
        verify_proof_package_strict(out)

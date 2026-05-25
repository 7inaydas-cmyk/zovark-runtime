from __future__ import annotations

import json
from pathlib import Path

import pytest


jsonschema = pytest.importorskip("jsonschema")
Draft202012Validator = jsonschema.Draft202012Validator
RefResolver = jsonschema.validators.RefResolver


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
VERDICT_SCHEMA = CONTRACTS / "verdict_envelope.schema.json"


def load_contract_schema(schema_path: Path) -> dict:
    return json.loads(schema_path.read_text(encoding="utf-8"))


def iter_refs(node: object):
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str):
            yield ref
        for value in node.values():
            yield from iter_refs(value)
    elif isinstance(node, list):
        for value in node:
            yield from iter_refs(value)


def test_contract_schemas_validate_against_draft_2020_12_metaschema() -> None:
    schema_paths = sorted(CONTRACTS.glob("*.schema.json"))

    assert CONTRACTS / "scanner_finding_envelope.schema.json" in schema_paths
    assert CONTRACTS / "finding.schema.json" in schema_paths
    assert CONTRACTS / "recommended_action.schema.json" in schema_paths
    assert VERDICT_SCHEMA in schema_paths

    for schema_path in schema_paths:
        Draft202012Validator.check_schema(load_contract_schema(schema_path))


def test_verdict_schema_refs_resolve_to_local_contracts() -> None:
    schemas_by_id = {}
    for schema_path in sorted(CONTRACTS.glob("*.schema.json")):
        schema = load_contract_schema(schema_path)
        schema_id = schema.get("$id")
        if isinstance(schema_id, str):
            schemas_by_id[schema_id.split("#", 1)[0]] = schema

    missing_refs = []
    for ref in iter_refs(load_contract_schema(VERDICT_SCHEMA)):
        if ref.startswith("#"):
            continue
        base_ref = ref.split("#", 1)[0]
        if base_ref not in schemas_by_id:
            missing_refs.append(ref)

    assert not missing_refs

    verdict = {
        "verdict_id": "11111111-1111-4111-8111-111111111111",
        "tenant_id": "22222222-2222-4222-8222-222222222222",
        "investigation_id": "33333333-3333-4333-8333-333333333333",
        "confidence_basis_points": 6500,
        "verdict_class": "suspicious",
        "recommended_actions": [
            {
                "action_id": "44444444-4444-4444-8444-444444444444",
                "action_class": "no_op",
                "target_canonical": "host:33333333-3333-4333-8333-333333333333",
                "confidence_basis_points": 6500,
                "reversible": True,
                "authorization_token": "synthetic-authorization-token",
            }
        ],
        "threshold_version": "synthetic-thresholds-1.0.0",
        "policy_snapshot_version": "synthetic-policy-1.0.0",
        "evidence": [
            {
                "finding_id": "55555555-5555-4555-8555-555555555555",
                "tenant_id": "22222222-2222-4222-8222-222222222222",
                "ocsf_class_uid": 2004,
                "ocsf_category_uid": 2,
                "severity_id": 3,
                "occurred_at_ns": 1700000000000000000,
                "source_event_uids": ["synthetic-event-001"],
                "confidence_basis_points": 6500,
            }
        ],
    }

    verdict_schema = load_contract_schema(VERDICT_SCHEMA)
    resolver = RefResolver.from_schema(verdict_schema, store=schemas_by_id)
    Draft202012Validator(verdict_schema, resolver=resolver).validate(verdict)

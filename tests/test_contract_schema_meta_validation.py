from __future__ import annotations

import json
from pathlib import Path

import pytest


jsonschema = pytest.importorskip("jsonschema")
Draft202012Validator = jsonschema.Draft202012Validator


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
            schemas_by_id[schema_id.split("#", 1)[0]] = schema_path

    missing_refs = []
    for ref in iter_refs(load_contract_schema(VERDICT_SCHEMA)):
        if ref.startswith("#"):
            continue
        base_ref = ref.split("#", 1)[0]
        if base_ref not in schemas_by_id:
            missing_refs.append(ref)

    assert not missing_refs

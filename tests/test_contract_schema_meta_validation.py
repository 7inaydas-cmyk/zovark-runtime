from __future__ import annotations

import json
from pathlib import Path

import pytest


jsonschema = pytest.importorskip("jsonschema")
Draft202012Validator = jsonschema.Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"


def test_contract_schemas_validate_against_draft_2020_12_metaschema() -> None:
    schema_paths = sorted(CONTRACTS.glob("*.schema.json"))

    assert CONTRACTS / "scanner_finding_envelope.schema.json" in schema_paths

    for schema_path in schema_paths:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


jsonschema = pytest.importorskip("jsonschema")
Draft202012Validator = jsonschema.Draft202012Validator
RefResolver = jsonschema.validators.RefResolver

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
SCHEMA = CONTRACTS / "verdict_envelope.schema.json"
FIXTURE = ROOT / "tests" / "fixtures" / "verdict_envelope_minimal.json"


def _walk_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        result: list[str] = []
        for key, item in value.items():
            result.append(str(key))
            result.extend(_walk_strings(item))
        return result
    if isinstance(value, list):
        result = []
        for item in value:
            result.extend(_walk_strings(item))
        return result
    return []


def _contract_store() -> dict[str, dict[str, Any]]:
    schemas: dict[str, dict[str, Any]] = {}
    for schema_path in sorted(CONTRACTS.glob("*.schema.json")):
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        schema_id = schema.get("$id")
        if isinstance(schema_id, str):
            schemas[schema_id.split("#", 1)[0]] = schema
    return schemas


def test_verdict_envelope_fixture_validates_against_canonical_schema() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    resolver = RefResolver.from_schema(schema, store=_contract_store())

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, resolver=resolver).validate(fixture)

    assert fixture["verdict_id"] == "11111111-1111-4111-8111-111111111111"
    assert fixture["tenant_id"] == "22222222-2222-4222-8222-222222222222"
    assert fixture["verdict_class"] == "suspicious"
    assert fixture["recommended_actions"][0]["action_class"] == "no_op"
    assert "Synthetic" in fixture["recommended_actions"][0]["rationale"]


def test_verdict_envelope_fixture_contains_no_forbidden_payload_markers() -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    rendered = "\n".join(_walk_strings(fixture)).lower()

    forbidden_markers = [
        "raw_payload",
        "tool_output",
        "hidden_reasoning",
        "prompt",
        "customer-ready",
        "production-ready",
        "demo-ready",
        "sla",
        "compliance-ready",
        "derive_verdict",
        "deterministic verdict proof",
        "verdictinput fixture",
    ]
    for marker in forbidden_markers:
        assert marker not in rendered

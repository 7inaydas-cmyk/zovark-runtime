from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


jsonschema = pytest.importorskip("jsonschema")
Draft202012Validator = jsonschema.Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "contracts" / "scanner_finding_envelope.schema.json"
FIXTURE = ROOT / "tests" / "fixtures" / "scanner_finding_minimal.json"


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


def test_scanner_finding_fixture_validates_against_canonical_schema() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(fixture)

    assert fixture["scanner_type"] == "edr"
    assert fixture["tenant_id"] == "22222222-2222-4222-8222-222222222222"
    assert fixture["envelope_id"] == "11111111-1111-4111-8111-111111111111"
    assert "Synthetic" in fixture["raw_finding"]["title"]
    description = fixture["raw_finding"]["description"].lower()
    assert "synthetic" in description


def test_scanner_finding_fixture_contains_no_forbidden_payload_markers() -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    rendered = "\n".join(_walk_strings(fixture)).lower()

    forbidden_markers = [
        "raw_payload",
        "tool_output",
        "hidden_reasoning",
        "prompt",
        "customer-ready",
        "production-ready",
        "compliance-ready",
    ]
    for marker in forbidden_markers:
        assert marker not in rendered

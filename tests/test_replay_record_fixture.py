from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest


jsonschema = pytest.importorskip("jsonschema")
Draft202012Validator = jsonschema.Draft202012Validator
ValidationError = jsonschema.ValidationError

try:
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT202012
except Exception:  # pragma: no cover - exercised only on older local jsonschema stacks.
    Registry = None
    Resource = None
    DRAFT202012 = None

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
FIXTURES = ROOT / "tests" / "fixtures"

FORBIDDEN_NONDETERMINISTIC_FIELDS = [
    "wall_clock",
    "random_seed",
    "filesystem_metadata",
    "network_io",
    "process_local_state",
    "hidden_reasoning",
    "raw_tool_output",
]

FORBIDDEN_TEXT_MARKERS = [
    "customer-ready",
    "production-ready",
    "demo-ready",
    "compliance-ready",
    "raw_tool_output",
    "hidden_reasoning",
    "derive_verdict",
    "replay engine",
]


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _contract_store() -> dict[str, dict[str, Any]]:
    schemas: dict[str, dict[str, Any]] = {}
    for schema_path in sorted(CONTRACTS.glob("*.schema.json")):
        schema = _load_json(schema_path)
        schema_id = schema.get("$id")
        if isinstance(schema_id, str):
            schemas[schema_id.split("#", 1)[0]] = schema
    return schemas


def _contract_registry():
    assert Registry is not None
    assert Resource is not None
    assert DRAFT202012 is not None

    registry = Registry()
    for schema_id, schema in _contract_store().items():
        resource = Resource.from_contents(schema, default_specification=DRAFT202012)
        registry = registry.with_resource(schema_id, resource)
    return registry


def _validator(schema_path: Path) -> Draft202012Validator:
    schema = _load_json(schema_path)
    Draft202012Validator.check_schema(schema)
    if Registry is not None:
        return Draft202012Validator(schema, registry=_contract_registry())

    resolver = jsonschema.validators.RefResolver.from_schema(schema, store=_contract_store())
    return Draft202012Validator(schema, resolver=resolver)


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

SCHEMA = CONTRACTS / "replay_record.schema.json"
FIXTURE = FIXTURES / "replay_record_minimal.json"


def test_replay_record_fixture_validates_against_canonical_schema() -> None:
    fixture = _load_json(FIXTURE)

    _validator(SCHEMA).validate(fixture)

    assert fixture["schema_version"] == "1.0.0"
    assert fixture["record_format_version"] == "1.0.0"
    assert fixture["failure_policy"] == "fail_closed"
    assert fixture["verdict_input"]["schema_version"] == "1.0.0"
    assert fixture["replay_compatibility_contract"] == "architecture/replay-compatibility.yaml"
    print("REPLAY_RECORD_FIXTURE_SCHEMA_OK")


def test_replay_record_fixture_rejects_extra_fields() -> None:
    fixture = _load_json(FIXTURE)
    invalid = copy.deepcopy(fixture)
    invalid["unexpected_extra_field"] = "not accepted"

    with pytest.raises(ValidationError):
        _validator(SCHEMA).validate(invalid)


@pytest.mark.parametrize("field_name", FORBIDDEN_NONDETERMINISTIC_FIELDS)
def test_replay_record_rejects_forbidden_nondeterministic_field_names(field_name: str) -> None:
    fixture = _load_json(FIXTURE)
    invalid = copy.deepcopy(fixture)
    invalid[field_name] = "not accepted"

    with pytest.raises(ValidationError):
        _validator(SCHEMA).validate(invalid)


def test_replay_record_fixture_contains_no_forbidden_payload_markers() -> None:
    fixture = _load_json(FIXTURE)
    rendered = "\\n".join(_walk_strings(fixture)).lower()

    for marker in FORBIDDEN_TEXT_MARKERS:
        assert marker not in rendered

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest


jsonschema = pytest.importorskip("jsonschema")
yaml = pytest.importorskip("yaml")
ValidationError = jsonschema.ValidationError
validator_for = jsonschema.validators.validator_for

try:
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT202012
except Exception:  # pragma: no cover - exercised only on older local jsonschema stacks.
    Registry = None
    Resource = None
    DRAFT202012 = None


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
REPLAY_FAILURE_SCHEMA = CONTRACTS / "replay_failure_record.schema.json"
REPLAY_COMPATIBILITY_MATRIX = CONTRACTS / "replay-compatibility.yaml"
REPLAY_COMPATIBILITY_SCHEMA = CONTRACTS / "replay-compatibility.schema.json"

FORBIDDEN_RAW_FIELDS = [
    "raw_prompt",
    "raw_llm_payload",
    "hidden_reasoning",
    "raw_tool_output",
    "filesystem_metadata",
    "process_state",
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


def _validator(schema_path: Path):
    schema = _load_json(schema_path)
    validator_cls = validator_for(schema)
    validator_cls.check_schema(schema)
    if Registry is not None:
        return validator_cls(schema, registry=_contract_registry())

    resolver = jsonschema.validators.RefResolver.from_schema(schema, store=_contract_store())
    return validator_cls(schema, resolver=resolver)


def _valid_failure_record() -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "failure_code": "REPLAY_VERDICT_INPUT_HASH_MISMATCH",
        "failure_category": "hash_integrity",
        "tenant_id": "22222222-2222-4222-8222-222222222222",
        "investigation_id": "33333333-3333-4333-8333-333333333333",
        "replay_compatibility_contract": "architecture/replay-compatibility.yaml",
        "replay_record_hash": "6" * 64,
        "component": "verdict_input",
        "field_path": "verdict_input_hash",
        "expected_hash": "7" * 64,
        "observed_hash": "8" * 64,
        "fail_closed_reason": "Synthetic bounded replay failure record for schema validation.",
    }


def _failure_code_enum() -> tuple[str, ...]:
    schema = _load_json(REPLAY_FAILURE_SCHEMA)
    return tuple(schema["$defs"]["ReplayFailureCode"]["enum"])


def test_replay_failure_record_schema_validates_against_declared_metaschema() -> None:
    schema = _load_json(REPLAY_FAILURE_SCHEMA)
    validator_for(schema).check_schema(schema)


def test_replay_failure_record_valid_example_validates_against_schema() -> None:
    _validator(REPLAY_FAILURE_SCHEMA).validate(_valid_failure_record())

    print("REPLAY_FAILURE_RECORD_SCHEMA_OK")


def test_replay_failure_record_rejects_extra_fields() -> None:
    invalid = _valid_failure_record()
    invalid["unexpected_extra_field"] = "not accepted"

    with pytest.raises(ValidationError):
        _validator(REPLAY_FAILURE_SCHEMA).validate(invalid)


@pytest.mark.parametrize("field_name", FORBIDDEN_RAW_FIELDS)
def test_replay_failure_record_rejects_forbidden_raw_fields(field_name: str) -> None:
    invalid = copy.deepcopy(_valid_failure_record())
    invalid[field_name] = "not accepted"

    with pytest.raises(ValidationError):
        _validator(REPLAY_FAILURE_SCHEMA).validate(invalid)


def test_replay_failure_codes_align_with_replay_compatibility_matrix() -> None:
    matrix = yaml.safe_load(REPLAY_COMPATIBILITY_MATRIX.read_text(encoding="utf-8"))

    assert tuple(matrix["structured_failure_codes"]) == _failure_code_enum()


def test_replay_compatibility_matrix_resolves_replay_failure_code_ref_locally() -> None:
    matrix = yaml.safe_load(REPLAY_COMPATIBILITY_MATRIX.read_text(encoding="utf-8"))

    _validator(REPLAY_COMPATIBILITY_SCHEMA).validate(matrix)

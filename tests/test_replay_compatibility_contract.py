from __future__ import annotations

import json
from pathlib import Path

import pytest


jsonschema = pytest.importorskip("jsonschema")
yaml = pytest.importorskip("yaml")
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
REPLAY_COMPATIBILITY_MATRIX = CONTRACTS / "replay-compatibility.yaml"
REPLAY_COMPATIBILITY_SCHEMA = CONTRACTS / "replay-compatibility.schema.json"


def _load_schema() -> dict:
    return json.loads(REPLAY_COMPATIBILITY_SCHEMA.read_text(encoding="utf-8"))


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _contract_store() -> dict[str, dict]:
    schemas: dict[str, dict] = {}
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


def test_replay_compatibility_matrix_validates_against_canonical_schema() -> None:
    schema = _load_schema()
    validator_cls = validator_for(schema)
    validator_cls.check_schema(schema)

    matrix = yaml.safe_load(REPLAY_COMPATIBILITY_MATRIX.read_text(encoding="utf-8"))
    if Registry is not None:
        validator_cls(schema, registry=_contract_registry()).validate(matrix)
    else:
        resolver = jsonschema.validators.RefResolver.from_schema(schema, store=_contract_store())
        validator_cls(schema, resolver=resolver).validate(matrix)

    print("REPLAY_COMPATIBILITY_MATRIX_SCHEMA_OK")

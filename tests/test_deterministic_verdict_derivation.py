from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from zovark_runtime.verdict_derivation import canonical_json_bytes, derive_verdict


jsonschema = pytest.importorskip("jsonschema")
Draft202012Validator = jsonschema.Draft202012Validator

try:
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT202012
except Exception:  # pragma: no cover - older local jsonschema stacks only.
    Registry = None
    Resource = None
    DRAFT202012 = None

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
FIXTURES = ROOT / "tests" / "fixtures"
MODULE_PATH = ROOT / "src" / "zovark_runtime" / "verdict_derivation.py"
VERDICT_INPUT_SCHEMA = CONTRACTS / "verdict_input.schema.json"
VERDICT_SCHEMA = CONTRACTS / "verdict_envelope.schema.json"
VERDICT_INPUT_FIXTURE = FIXTURES / "verdict_input_minimal.json"
EXPECTED_VERDICT_FIXTURE = FIXTURES / "verdict_envelope_expected_from_minimal_input.json"


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


def test_verdict_input_fixture_validates_against_contract() -> None:
    _validator(VERDICT_INPUT_SCHEMA).validate(_load_json(VERDICT_INPUT_FIXTURE))


def test_derived_verdict_validates_and_matches_expected_fixture() -> None:
    verdict_input = _load_json(VERDICT_INPUT_FIXTURE)
    expected = _load_json(EXPECTED_VERDICT_FIXTURE)
    derived = derive_verdict(verdict_input)

    _validator(VERDICT_SCHEMA).validate(derived)
    _validator(VERDICT_SCHEMA).validate(expected)
    assert derived == expected
    assert derived["verdict_class"] == "indeterminate"
    assert derived["recommended_actions"] == []
    print("DETERMINISTIC_VERDICT_DERIVATION_OK")


def test_derivation_is_byte_identical_across_repeated_runs() -> None:
    verdict_input = _load_json(VERDICT_INPUT_FIXTURE)
    original = copy.deepcopy(verdict_input)

    first = derive_verdict(verdict_input)
    second = derive_verdict(copy.deepcopy(verdict_input))

    assert verdict_input == original
    assert first == second
    assert canonical_json_bytes(first) == canonical_json_bytes(second)
    assert canonical_json_bytes(first) == canonical_json_bytes(_load_json(EXPECTED_VERDICT_FIXTURE))


def test_canonical_json_bytes_are_stable_compact_utf8() -> None:
    payload = {"b": [2, {"d": 4, "c": 3}], "a": 1}

    assert canonical_json_bytes(payload) == b'{"a":1,"b":[2,{"c":3,"d":4}]}'
    assert canonical_json_bytes(payload).decode("utf-8") == '{"a":1,"b":[2,{"c":3,"d":4}]}'


def test_derivation_module_uses_no_forbidden_nondeterministic_sources() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    forbidden_markers = [
        "datetime.now",
        "datetime.utcnow",
        "time.time",
        "time.time_ns",
        "random.",
        "import random",
        "uuid.uuid4",
        "import socket",
        "requests",
        "urllib",
        "http.client",
        "os.environ",
        "os.getenv",
        "Path(",
        ".stat(",
        "open(",
        "subprocess",
        "getpid",
        "set(",
    ]

    for marker in forbidden_markers:
        assert marker not in source

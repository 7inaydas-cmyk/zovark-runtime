from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from zovark_runtime.replay_validation import (
    MODEL_VERSION_MISMATCH,
    OK,
    PROMPT_HASH_MISMATCH,
    SCHEMA_INCOMPATIBLE,
    TOOL_CATALOG_VERSION_MISMATCH,
    VERDICT_ENVELOPE_HASH_MISMATCH,
    VERDICT_INPUT_HASH_MISMATCH,
    canonical_sha256_hex,
    validate_replay_record,
)


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
MODULE_PATH = ROOT / "src" / "zovark_runtime" / "replay_validation.py"
REPLAY_SCHEMA = CONTRACTS / "replay_record.schema.json"
VERDICT_SCHEMA = CONTRACTS / "verdict_envelope.schema.json"
REPLAY_FIXTURE = FIXTURES / "replay_record_expected_minimal.json"
VERDICT_INPUT_FIXTURE = FIXTURES / "verdict_input_minimal.json"
EXPECTED_VERDICT_FIXTURE = FIXTURES / "verdict_envelope_expected_from_minimal_input.json"

REPLAY_VALIDATION_FAIL_CLOSED_CASES = (
    {
        "id": "schema_version_incompatible",
        "field_name": "schema_version",
        "value": "2.0.0",
        "expected_code": SCHEMA_INCOMPATIBLE,
    },
    {
        "id": "record_format_version_incompatible",
        "field_name": "record_format_version",
        "value": "2.0.0",
        "expected_code": SCHEMA_INCOMPATIBLE,
    },
    {
        "id": "verdict_input_hash_mismatch",
        "field_name": "verdict_input_hash",
        "value": "0" * 64,
        "expected_code": VERDICT_INPUT_HASH_MISMATCH,
    },
    {
        "id": "verdict_envelope_hash_mismatch",
        "field_name": "verdict_envelope_hash",
        "value": "0" * 64,
        "expected_code": VERDICT_ENVELOPE_HASH_MISMATCH,
    },
    {
        "id": "tool_catalog_version_mismatch",
        "field_name": "tool_catalog_version",
        "value": "synthetic-tool-catalog-2.0.0",
        "expected_code": TOOL_CATALOG_VERSION_MISMATCH,
    },
    {
        "id": "model_version_mismatch",
        "field_name": "model_version",
        "value": "2.0.0",
        "expected_code": MODEL_VERSION_MISMATCH,
    },
    {
        "id": "prompt_hash_empty",
        "field_name": "prompt_hashes",
        "value": [],
        "expected_code": PROMPT_HASH_MISMATCH,
    },
    {
        "id": "prompt_hash_mismatch",
        "field_name": "prompt_hashes",
        "value": ["0" * 64],
        "expected_code": PROMPT_HASH_MISMATCH,
    },
    {
        "id": "prompt_hash_missing",
        "field_name": "prompt_hashes",
        "delete": True,
        "expected_code": PROMPT_HASH_MISMATCH,
    },
)


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


def _valid_replay_record() -> dict[str, Any]:
    return _load_json(REPLAY_FIXTURE)


def _expected_verdict_input() -> dict[str, Any]:
    return _load_json(VERDICT_INPUT_FIXTURE)


def _expected_verdict_envelope() -> dict[str, Any]:
    return _load_json(EXPECTED_VERDICT_FIXTURE)


def test_replay_record_expected_fixture_validates_against_contract() -> None:
    replay_record = _valid_replay_record()

    _validator(REPLAY_SCHEMA).validate(replay_record)
    _validator(VERDICT_SCHEMA).validate(_expected_verdict_envelope())

    assert replay_record["verdict_input_hash"] == canonical_sha256_hex(_expected_verdict_input())
    assert replay_record["verdict_envelope_hash"] == canonical_sha256_hex(_expected_verdict_envelope())


def test_replay_validation_succeeds_for_expected_minimal_record() -> None:
    result = validate_replay_record(
        _valid_replay_record(),
        _expected_verdict_input(),
        _expected_verdict_envelope(),
    )

    assert result.ok
    assert result.code == OK
    print("REPLAY_VALIDATION_PROOF_OK")


@pytest.mark.parametrize(
    "case",
    REPLAY_VALIDATION_FAIL_CLOSED_CASES,
    ids=lambda case: case["id"],
)
def test_replay_validation_fails_closed_on_expected_cases(case: dict[str, Any]) -> None:
    replay_record = _valid_replay_record()
    field_name = case["field_name"]
    if case.get("delete"):
        del replay_record[field_name]
    else:
        replay_record[field_name] = case["value"]

    result = validate_replay_record(replay_record, _expected_verdict_input(), _expected_verdict_envelope())

    assert not result.ok
    assert result.code == case["expected_code"]


def test_replay_validation_uses_local_codes_without_schema_failure_code_changes() -> None:
    replay_record = _valid_replay_record()

    assert "structured_failure_codes" not in replay_record
    result = validate_replay_record(replay_record, _expected_verdict_input(), _expected_verdict_envelope())
    assert result.code == OK


def test_replay_validation_does_not_mutate_inputs() -> None:
    replay_record = _valid_replay_record()
    verdict_input = _expected_verdict_input()
    verdict_envelope = _expected_verdict_envelope()
    original = copy.deepcopy((replay_record, verdict_input, verdict_envelope))

    validate_replay_record(replay_record, verdict_input, verdict_envelope)

    assert (replay_record, verdict_input, verdict_envelope) == original


def test_replay_validation_module_uses_no_forbidden_sources() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    forbidden_markers = [
        "derive_verdict",
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

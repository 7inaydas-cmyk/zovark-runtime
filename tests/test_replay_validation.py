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
    RECORDED_CATALOG_UNDECLARED_DETAIL,
    RECORDED_TOOL_IDENTITY_MISSING_DETAIL,
    SCHEMA_INCOMPATIBLE,
    TOOL_CATALOG_VERSION_MISMATCH,
    TOOL_RETIRED,
    TOOL_RETIRED_DETAIL,
    VERDICT_ENVELOPE_HASH_MISMATCH,
    VERDICT_INPUT_HASH_MISMATCH,
    canonical_sha256_hex,
    validate_replay_record,
)


jsonschema = pytest.importorskip("jsonschema")
yaml = pytest.importorskip("yaml")
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

ACTIVE_TOOL_IO = {
    "tool_call_id": "tool-call-001",
    "sequence_number": 0,
    "tool_name": "synthetic-tool",
    "tool_version": "1.0.0",
    "input_hash": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "output_hash": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
    "status": "success",
    "canonical_summary": "Synthetic bounded active tool summary for replay validation.",
}
RETIRED_TOOL_IO = {
    **ACTIVE_TOOL_IO,
    "tool_name": "synthetic-retired-tool",
    "canonical_summary": "Synthetic bounded retired tool summary for replay validation.",
}
ABSENT_TOOL_IO = {
    **ACTIVE_TOOL_IO,
    "tool_name": "synthetic-absent-tool",
    "canonical_summary": "Synthetic bounded absent tool summary for replay validation.",
}

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
        "id": "tool_retired",
        "updates": {
            "tool_catalog_version": "1.0.0",
            "tool_io": [RETIRED_TOOL_IO],
        },
        "expected_verdict_input_updates": {
            "tool_catalog_version": "1.0.0",
            "tool_results": [RETIRED_TOOL_IO],
        },
        "expected_code": TOOL_RETIRED,
    },
    {
        "id": "model_version_mismatch",
        "field_name": "model_version",
        "value": "2.0.0",
        "expected_code": MODEL_VERSION_MISMATCH,
    },
    {
        "id": "decoding_params_mismatch",
        "field_name": "decoding_params",
        "value": {
            "temperature": 0,
            "top_p": 1,
            "max_output_tokens": 256,
            "seed_policy": "synthetic_mismatch_no_seed",
        },
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


def _apply_case(
    replay_record: dict[str, Any],
    expected_verdict_input: dict[str, Any],
    case: dict[str, Any],
) -> None:
    for key, value in case.get("updates", {}).items():
        replay_record[key] = copy.deepcopy(value)

    field_name = case.get("field_name")
    if isinstance(field_name, str):
        if case.get("delete"):
            del replay_record[field_name]
        else:
            replay_record[field_name] = copy.deepcopy(case["value"])

    verdict_input_updates = case.get("expected_verdict_input_updates", {})
    for key, value in verdict_input_updates.items():
        expected_verdict_input[key] = copy.deepcopy(value)
        replay_record["verdict_input"][key] = copy.deepcopy(value)
    if verdict_input_updates:
        replay_record["verdict_input_hash"] = canonical_sha256_hex(expected_verdict_input)


def _record_and_input_for_tool(
    tool_io: dict[str, Any],
    *,
    catalog_version: str = "1.0.0",
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    replay_record = _valid_replay_record()
    expected_verdict_input = _expected_verdict_input()
    expected_verdict_envelope = _expected_verdict_envelope()
    _apply_case(
        replay_record,
        expected_verdict_input,
        {
            "updates": {
                "tool_catalog_version": catalog_version,
                "tool_io": [tool_io],
            },
            "expected_verdict_input_updates": {
                "tool_catalog_version": catalog_version,
                "tool_results": [tool_io],
            },
        },
    )
    return replay_record, expected_verdict_input, expected_verdict_envelope


def _write_catalog_authority(
    root: Path,
    *,
    matrix: dict[str, Any] | None = None,
    recorded_catalog_text: str | None = None,
    current_catalog_text: str | None = None,
) -> None:
    catalog_dir = root / "replay" / "catalogs"
    catalog_dir.mkdir(parents=True)
    matrix_payload = matrix or {
        "current_tool_catalog_version": "1.1.0",
        "tool_catalog": {
            "1.0.0": {"catalog_artifact": "architecture/replay/catalogs/1.0.0.yaml"},
            "1.1.0": {"catalog_artifact": "architecture/replay/catalogs/1.1.0.yaml"},
        },
    }
    (root / "replay-compatibility.yaml").write_text(
        yaml.safe_dump(matrix_payload, sort_keys=False),
        encoding="utf-8",
    )
    if recorded_catalog_text is not None:
        (catalog_dir / "1.0.0.yaml").write_text(recorded_catalog_text, encoding="utf-8")
    if current_catalog_text is not None:
        (catalog_dir / "1.1.0.yaml").write_text(current_catalog_text, encoding="utf-8")


def _recorded_catalog_text() -> str:
    return yaml.safe_dump(
        {
            "schema_version": "1.0.0",
            "catalog_version": "1.0.0",
            "tools": [
                {
                    "tool_name": "synthetic-tool",
                    "tool_version": "1.0.0",
                    "capability_class": "replay_fixture",
                    "replay_safe": True,
                },
                {
                    "tool_name": "synthetic-retired-tool",
                    "tool_version": "1.0.0",
                    "capability_class": "replay_fixture",
                    "replay_safe": True,
                },
            ],
            "retired_tools": [],
        },
        sort_keys=False,
    )


def _current_catalog_text() -> str:
    return yaml.safe_dump(
        {
            "schema_version": "1.0.0",
            "catalog_version": "1.1.0",
            "tools": [
                {
                    "tool_name": "synthetic-tool",
                    "tool_version": "1.0.0",
                    "capability_class": "replay_fixture",
                    "replay_safe": True,
                }
            ],
            "retired_tools": [
                {
                    "tool_name": "synthetic-retired-tool",
                    "tool_version": "1.0.0",
                    "last_active_catalog_version": "1.0.0",
                    "retired_in_catalog_version": "1.1.0",
                    "failure_code": "REPLAY_TOOL_RETIRED",
                    "row_id": "tool_compatibility.tool_retired",
                    "retirement_authority": "ADR-0047",
                    "retirement_reason": "Synthetic bounded retirement entry for replay validation.",
                }
            ],
        },
        sort_keys=False,
    )


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
    expected_verdict_input = _expected_verdict_input()
    _apply_case(replay_record, expected_verdict_input, case)

    result = validate_replay_record(replay_record, expected_verdict_input, _expected_verdict_envelope())

    assert not result.ok
    assert result.code == case["expected_code"]
    if case["id"] == "decoding_params_mismatch":
        assert result.detail == "decoding parameters differ from verdict input"
        print("REPLAY_DECODING_PARAMS_FAIL_CLOSED_OK")
    if case["id"] == "tool_retired":
        assert result.detail == TOOL_RETIRED_DETAIL
        print("REPLAY_TOOL_RETIRED_FAIL_CLOSED_OK")


def test_active_tool_still_present_in_current_catalog_does_not_emit_tool_retired() -> None:
    replay_record, expected_verdict_input, expected_verdict_envelope = _record_and_input_for_tool(ACTIVE_TOOL_IO)

    result = validate_replay_record(replay_record, expected_verdict_input, expected_verdict_envelope)

    assert result.ok
    assert result.code == OK


def test_tool_absent_from_recorded_catalog_is_not_treated_as_retired() -> None:
    replay_record, expected_verdict_input, expected_verdict_envelope = _record_and_input_for_tool(ABSENT_TOOL_IO)

    result = validate_replay_record(replay_record, expected_verdict_input, expected_verdict_envelope)

    assert not result.ok
    assert result.code == TOOL_CATALOG_VERSION_MISMATCH
    assert result.detail == RECORDED_TOOL_IDENTITY_MISSING_DETAIL


def test_unknown_recorded_catalog_version_fails_closed_deterministically() -> None:
    replay_record, expected_verdict_input, expected_verdict_envelope = _record_and_input_for_tool(
        ACTIVE_TOOL_IO,
        catalog_version="9.9.9",
    )

    result = validate_replay_record(replay_record, expected_verdict_input, expected_verdict_envelope)

    assert not result.ok
    assert result.code == TOOL_CATALOG_VERSION_MISMATCH
    assert result.detail == RECORDED_CATALOG_UNDECLARED_DETAIL


def test_missing_catalog_artifact_fails_closed_deterministically(tmp_path: Path) -> None:
    _write_catalog_authority(
        tmp_path,
        current_catalog_text=_current_catalog_text(),
    )
    replay_record, expected_verdict_input, expected_verdict_envelope = _record_and_input_for_tool(ACTIVE_TOOL_IO)

    result = validate_replay_record(
        replay_record,
        expected_verdict_input,
        expected_verdict_envelope,
        contracts_root=tmp_path,
    )

    assert not result.ok
    assert result.code == TOOL_CATALOG_VERSION_MISMATCH
    assert result.detail == "replay tool catalog artifact is missing"


def test_malformed_catalog_artifact_fails_closed_deterministically(tmp_path: Path) -> None:
    _write_catalog_authority(
        tmp_path,
        recorded_catalog_text="not: [valid",
        current_catalog_text=_current_catalog_text(),
    )
    replay_record, expected_verdict_input, expected_verdict_envelope = _record_and_input_for_tool(ACTIVE_TOOL_IO)

    result = validate_replay_record(
        replay_record,
        expected_verdict_input,
        expected_verdict_envelope,
        contracts_root=tmp_path,
    )

    assert not result.ok
    assert result.code == TOOL_CATALOG_VERSION_MISMATCH
    assert result.detail == "replay tool catalog artifact is malformed"


def test_missing_current_catalog_successor_mapping_fails_closed_without_inference(tmp_path: Path) -> None:
    _write_catalog_authority(
        tmp_path,
        matrix={
            "current_tool_catalog_version": "1.2.0",
            "tool_catalog": {
                "1.0.0": {"catalog_artifact": "architecture/replay/catalogs/1.0.0.yaml"},
            },
        },
        recorded_catalog_text=_recorded_catalog_text(),
        current_catalog_text=_current_catalog_text(),
    )
    replay_record, expected_verdict_input, expected_verdict_envelope = _record_and_input_for_tool(ACTIVE_TOOL_IO)

    result = validate_replay_record(
        replay_record,
        expected_verdict_input,
        expected_verdict_envelope,
        contracts_root=tmp_path,
    )

    assert not result.ok
    assert result.code == TOOL_CATALOG_VERSION_MISMATCH
    assert result.detail == "current tool catalog version is not declared"


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
        ".stat(",
        "open(",
        "subprocess",
        "getpid",
        "set(",
    ]

    for marker in forbidden_markers:
        assert marker not in source

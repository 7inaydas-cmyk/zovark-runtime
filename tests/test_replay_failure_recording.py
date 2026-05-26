from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from zovark_runtime.replay_failure_mapping import (
    REPLAY_DECODING_PARAMS_MISMATCH,
    canonical_replay_failure_code,
)
from zovark_runtime.replay_failure_recording import canonical_replay_failure_record
from zovark_runtime.replay_validation import (
    FAILURE_POLICY_INCOMPATIBLE,
    SCHEMA_INCOMPATIBLE,
    VERDICT_INPUT_MISMATCH,
    ReplayValidationResult,
    validate_replay_record,
)
from zovark_runtime.verdict_derivation import canonical_json_bytes


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
FIXTURES = ROOT / "tests" / "fixtures"
REPLAY_VALIDATION_TEST = ROOT / "tests" / "test_replay_validation.py"
RECORDING_MODULE = ROOT / "src" / "zovark_runtime" / "replay_failure_recording.py"
REPLAY_FAILURE_SCHEMA = CONTRACTS / "replay_failure_record.schema.json"
REPLAY_COMPATIBILITY_MATRIX = CONTRACTS / "replay-compatibility.yaml"
REPLAY_FIXTURE = FIXTURES / "replay_record_expected_minimal.json"
VERDICT_INPUT_FIXTURE = FIXTURES / "verdict_input_minimal.json"
EXPECTED_VERDICT_FIXTURE = FIXTURES / "verdict_envelope_expected_from_minimal_input.json"

FORBIDDEN_RAW_FIELDS = {
    "raw_prompt",
    "raw_llm_payload",
    "hidden_reasoning",
    "raw_tool_output",
    "filesystem_metadata",
    "process_state",
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_replay_validation_test_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("zovark_runtime_replay_validation_cases", REPLAY_VALIDATION_TEST)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fail_closed_cases() -> tuple[dict[str, Any], ...]:
    return _load_replay_validation_test_module().REPLAY_VALIDATION_FAIL_CLOSED_CASES


def _valid_replay_record() -> dict[str, Any]:
    return _load_json(REPLAY_FIXTURE)


def _expected_verdict_input() -> dict[str, Any]:
    return _load_json(VERDICT_INPUT_FIXTURE)


def _expected_verdict_envelope() -> dict[str, Any]:
    return _load_json(EXPECTED_VERDICT_FIXTURE)


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


def _failure_code_enum() -> tuple[str, ...]:
    schema = _load_json(REPLAY_FAILURE_SCHEMA)
    return tuple(schema["$defs"]["ReplayFailureCode"]["enum"])


def _replay_compatibility_codes() -> tuple[str, ...]:
    matrix = yaml.safe_load(REPLAY_COMPATIBILITY_MATRIX.read_text(encoding="utf-8"))
    return tuple(matrix["structured_failure_codes"])


def _mutated_replay_record_for_case(case: dict[str, Any]) -> dict[str, Any]:
    replay_record = copy.deepcopy(_valid_replay_record())
    field_name = case["field_name"]
    if case.get("delete"):
        del replay_record[field_name]
    else:
        replay_record[field_name] = case["value"]
    return replay_record


def _result_for_replay_record(replay_record: dict[str, Any]) -> ReplayValidationResult:
    return validate_replay_record(replay_record, _expected_verdict_input(), _expected_verdict_envelope())


def test_current_fail_closed_cases_emit_canonical_failure_records() -> None:
    cases = _fail_closed_cases()
    schema_validator = _validator(REPLAY_FAILURE_SCHEMA)
    canonical_enum = _failure_code_enum()
    compatibility_codes = _replay_compatibility_codes()

    assert len(cases) == 10

    for case in cases:
        replay_record = _mutated_replay_record_for_case(case)
        result = _result_for_replay_record(replay_record)
        expected_canonical_code = canonical_replay_failure_code(result)

        failure_record = canonical_replay_failure_record(result, replay_record)

        assert expected_canonical_code is not None
        assert failure_record is not None
        schema_validator.validate(failure_record)
        assert failure_record["failure_code"] == expected_canonical_code
        assert failure_record["failure_code"] in canonical_enum
        assert failure_record["failure_code"] in compatibility_codes
        assert failure_record["tenant_id"] == replay_record["tenant_id"]
        assert failure_record["investigation_id"] == replay_record["investigation_id"]
        assert failure_record["replay_compatibility_contract"] == "architecture/replay-compatibility.yaml"
        assert not (FORBIDDEN_RAW_FIELDS & set(failure_record))

    print("REPLAY_FAILURE_RECORD_EMISSION_OK")


def test_emitted_failure_records_are_deterministic() -> None:
    for case in _fail_closed_cases():
        first_replay_record = _mutated_replay_record_for_case(case)
        second_replay_record = _mutated_replay_record_for_case(case)
        first_result = _result_for_replay_record(first_replay_record)
        second_result = _result_for_replay_record(second_replay_record)

        first_failure_record = canonical_replay_failure_record(first_result, first_replay_record)
        second_failure_record = canonical_replay_failure_record(second_result, second_replay_record)

        assert first_failure_record == second_failure_record
        assert first_failure_record is not None
        assert second_failure_record is not None
        assert canonical_json_bytes(first_failure_record) == canonical_json_bytes(second_failure_record)


def test_decoding_params_failure_record_uses_bounded_metadata() -> None:
    case = next(case for case in _fail_closed_cases() if case["id"] == "decoding_params_mismatch")
    replay_record = _mutated_replay_record_for_case(case)
    result = _result_for_replay_record(replay_record)

    failure_record = canonical_replay_failure_record(result, replay_record)

    assert failure_record is not None
    assert failure_record["failure_code"] == REPLAY_DECODING_PARAMS_MISMATCH
    assert failure_record["failure_category"] == "model_compatibility"
    assert failure_record["component"] == "decoding_params"
    assert failure_record["field_path"] == "decoding_params"
    assert "decoding_params" not in failure_record
    assert "expected_decoding_params" not in failure_record
    assert "observed_decoding_params" not in failure_record
    assert not (FORBIDDEN_RAW_FIELDS & set(failure_record))


@pytest.mark.parametrize(
    "result",
    (
        ReplayValidationResult(False, FAILURE_POLICY_INCOMPATIBLE, "replay record does not fail closed"),
        ReplayValidationResult(False, VERDICT_INPUT_MISMATCH, "recorded verdict_input differs from expected verdict input"),
        ReplayValidationResult(False, SCHEMA_INCOMPATIBLE, "verdict_input must be a mapping"),
    ),
)
def test_unsupported_local_branches_do_not_emit_failure_records(result: ReplayValidationResult) -> None:
    assert canonical_replay_failure_record(result, _valid_replay_record()) is None


def test_failure_record_emission_does_not_change_replay_validation_result_shape() -> None:
    replay_record = _mutated_replay_record_for_case(_fail_closed_cases()[0])
    result = _result_for_replay_record(replay_record)

    failure_record = canonical_replay_failure_record(result, replay_record)

    assert tuple(ReplayValidationResult.__dataclass_fields__) == ("ok", "code", "detail")
    assert "failure_code" not in result.__dict__
    assert failure_record is not None
    assert failure_record["failure_code"] == canonical_replay_failure_code(result)


def test_failure_record_emission_helper_uses_no_forbidden_sources_or_replay_execution() -> None:
    source = RECORDING_MODULE.read_text(encoding="utf-8")
    forbidden_markers = [
        "validate_replay_record",
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
        "REPLAY_COMPATIBILITY_MATRIX_COVERAGE_OK",
    ]

    for marker in forbidden_markers:
        assert marker not in source

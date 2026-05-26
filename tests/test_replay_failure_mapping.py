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
    REPLAY_PROMPT_HASH_MISSING,
    REPLAY_RECORD_FORMAT_INCOMPATIBLE,
    REPLAY_TOOL_CATALOG_MISMATCH,
    canonical_replay_failure_code,
    canonical_replay_failure_code_for_local_result,
)
from zovark_runtime.replay_validation import (
    FAILURE_POLICY_INCOMPATIBLE,
    MODEL_VERSION_MISMATCH,
    PROMPT_HASH_MISMATCH,
    SCHEMA_INCOMPATIBLE,
    TENANT_INVESTIGATION_MISMATCH,
    TOOL_CATALOG_VERSION_MISMATCH,
    VERDICT_ENVELOPE_HASH_MISMATCH,
    VERDICT_INPUT_HASH_MISMATCH,
    VERDICT_INPUT_MISMATCH,
    ReplayValidationResult,
    validate_replay_record,
)


yaml = pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
FIXTURES = ROOT / "tests" / "fixtures"
REPLAY_VALIDATION_TEST = ROOT / "tests" / "test_replay_validation.py"
MAPPING_MODULE = ROOT / "src" / "zovark_runtime" / "replay_failure_mapping.py"
REPLAY_FAILURE_SCHEMA = CONTRACTS / "replay_failure_record.schema.json"
REPLAY_COMPATIBILITY_MATRIX = CONTRACTS / "replay-compatibility.yaml"
REPLAY_FIXTURE = FIXTURES / "replay_record_expected_minimal.json"
VERDICT_INPUT_FIXTURE = FIXTURES / "verdict_input_minimal.json"
EXPECTED_VERDICT_FIXTURE = FIXTURES / "verdict_envelope_expected_from_minimal_input.json"

EXPECTED_CANONICAL_CODES_BY_CASE_ID = {
    "schema_version_incompatible": SCHEMA_INCOMPATIBLE,
    "record_format_version_incompatible": REPLAY_RECORD_FORMAT_INCOMPATIBLE,
    "verdict_input_hash_mismatch": VERDICT_INPUT_HASH_MISMATCH,
    "verdict_envelope_hash_mismatch": VERDICT_ENVELOPE_HASH_MISMATCH,
    "tool_catalog_version_mismatch": REPLAY_TOOL_CATALOG_MISMATCH,
    "model_version_mismatch": MODEL_VERSION_MISMATCH,
    "decoding_params_mismatch": REPLAY_DECODING_PARAMS_MISMATCH,
    "prompt_hash_empty": PROMPT_HASH_MISMATCH,
    "prompt_hash_mismatch": PROMPT_HASH_MISMATCH,
    "prompt_hash_missing": REPLAY_PROMPT_HASH_MISSING,
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


def _failure_code_enum() -> tuple[str, ...]:
    schema = _load_json(REPLAY_FAILURE_SCHEMA)
    return tuple(schema["$defs"]["ReplayFailureCode"]["enum"])


def _replay_compatibility_codes() -> tuple[str, ...]:
    matrix = yaml.safe_load(REPLAY_COMPATIBILITY_MATRIX.read_text(encoding="utf-8"))
    return tuple(matrix["structured_failure_codes"])


def _result_for_case(case: dict[str, Any]) -> ReplayValidationResult:
    replay_record = copy.deepcopy(_valid_replay_record())
    field_name = case["field_name"]
    if case.get("delete"):
        del replay_record[field_name]
    else:
        replay_record[field_name] = case["value"]

    return validate_replay_record(replay_record, _expected_verdict_input(), _expected_verdict_envelope())


def test_current_fail_closed_cases_map_to_canonical_failure_codes() -> None:
    cases = _fail_closed_cases()
    canonical_enum = _failure_code_enum()
    compatibility_codes = _replay_compatibility_codes()

    assert len(cases) == 10
    assert {case["id"] for case in cases} == set(EXPECTED_CANONICAL_CODES_BY_CASE_ID)

    for case in cases:
        result = _result_for_case(case)
        expected_canonical_code = EXPECTED_CANONICAL_CODES_BY_CASE_ID[case["id"]]

        assert not result.ok
        assert result.code == case["expected_code"]
        assert canonical_replay_failure_code(result) == expected_canonical_code
        assert expected_canonical_code in canonical_enum
        assert expected_canonical_code in compatibility_codes

    print("REPLAY_FAILURE_CANONICAL_CODE_MAPPING_OK")


def test_mapping_disambiguates_overloaded_local_result_codes() -> None:
    assert (
        canonical_replay_failure_code_for_local_result(
            SCHEMA_INCOMPATIBLE,
            "replay schema_version is incompatible",
        )
        == SCHEMA_INCOMPATIBLE
    )
    assert (
        canonical_replay_failure_code_for_local_result(
            SCHEMA_INCOMPATIBLE,
            "replay record_format_version is incompatible",
        )
        == REPLAY_RECORD_FORMAT_INCOMPATIBLE
    )
    assert (
        canonical_replay_failure_code_for_local_result(
            PROMPT_HASH_MISMATCH,
            "prompt hashes are missing",
        )
        == REPLAY_PROMPT_HASH_MISSING
    )
    assert (
        canonical_replay_failure_code_for_local_result(
            PROMPT_HASH_MISMATCH,
            "prompt hashes do not match verdict input prompt hash",
        )
        == PROMPT_HASH_MISMATCH
    )
    assert (
        canonical_replay_failure_code_for_local_result(
            MODEL_VERSION_MISMATCH,
            "model version differs from verdict input",
        )
        == MODEL_VERSION_MISMATCH
    )
    assert (
        canonical_replay_failure_code_for_local_result(
            MODEL_VERSION_MISMATCH,
            "decoding parameters differ from verdict input",
        )
        == REPLAY_DECODING_PARAMS_MISMATCH
    )


@pytest.mark.parametrize(
    ("code", "detail"),
    (
        (FAILURE_POLICY_INCOMPATIBLE, "replay record does not fail closed"),
        (VERDICT_INPUT_MISMATCH, "recorded verdict_input differs from expected verdict input"),
        (TENANT_INVESTIGATION_MISMATCH, "tenant_id differs from verdict input"),
        (TOOL_CATALOG_VERSION_MISMATCH, "unsupported tool catalog detail"),
        (SCHEMA_INCOMPATIBLE, "verdict_input must be a mapping"),
    ),
)
def test_unsupported_local_branches_do_not_silently_map(code: str, detail: str) -> None:
    assert canonical_replay_failure_code_for_local_result(code, detail) is None


def test_mapping_does_not_change_replay_validation_result_shape() -> None:
    result = _result_for_case(_fail_closed_cases()[0])

    assert tuple(ReplayValidationResult.__dataclass_fields__) == ("ok", "code", "detail")
    assert result.__dict__ == {
        "ok": False,
        "code": SCHEMA_INCOMPATIBLE,
        "detail": "replay schema_version is incompatible",
    }
    assert canonical_replay_failure_code(result) == SCHEMA_INCOMPATIBLE
    assert "failure_code" not in result.__dict__


def test_mapping_helper_uses_no_forbidden_sources_or_replay_execution() -> None:
    source = MAPPING_MODULE.read_text(encoding="utf-8")
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
    ]

    for marker in forbidden_markers:
        assert marker not in source

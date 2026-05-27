from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from zovark_runtime.replay_compatibility_mapping import replay_compatibility_row_id_for_failure_record
from zovark_runtime.replay_failure_mapping import canonical_replay_failure_code
from zovark_runtime.replay_failure_recording import canonical_replay_failure_record
from zovark_runtime.replay_validation import ReplayValidationResult, canonical_sha256_hex, validate_replay_record


yaml = pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
FIXTURES = ROOT / "tests" / "fixtures"
REPLAY_VALIDATION_TEST = ROOT / "tests" / "test_replay_validation.py"
MAPPING_MODULE = ROOT / "src" / "zovark_runtime" / "replay_compatibility_mapping.py"
REPLAY_COMPATIBILITY_MATRIX = CONTRACTS / "replay-compatibility.yaml"
REPLAY_FIXTURE = FIXTURES / "replay_record_expected_minimal.json"
VERDICT_INPUT_FIXTURE = FIXTURES / "verdict_input_minimal.json"
EXPECTED_VERDICT_FIXTURE = FIXTURES / "verdict_envelope_expected_from_minimal_input.json"

EXPECTED_ROW_ID_BY_CASE_ID = {
    "schema_version_incompatible": "schema_compatibility.record_schema_incompatible",
    "record_format_version_incompatible": "schema_compatibility.record_format_incompatible",
    "verdict_input_hash_mismatch": "hash_integrity.verdict_input_hash_mismatch",
    "verdict_envelope_hash_mismatch": "hash_integrity.verdict_envelope_hash_mismatch",
    "tool_catalog_version_mismatch": "catalog_compatibility.tool_catalog_mismatch",
    "tool_retired": "tool_compatibility.tool_retired",
    "model_version_mismatch": "model_compatibility.model_version_mismatch",
    "decoding_params_mismatch": "model_compatibility.decoding_params_mismatch",
    "prompt_hash_empty": "prompt_integrity.prompt_hash_mismatch",
    "prompt_hash_mismatch": "prompt_integrity.prompt_hash_mismatch",
    "prompt_hash_missing": "prompt_integrity.prompt_hash_missing",
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


def _load_matrix() -> dict[str, Any]:
    matrix = yaml.safe_load(REPLAY_COMPATIBILITY_MATRIX.read_text(encoding="utf-8"))
    assert isinstance(matrix, dict)
    return matrix


def _failure_outcome_rows() -> list[dict[str, Any]]:
    rows = _load_matrix()["failure_outcome_rows"]
    assert isinstance(rows, list)
    return rows


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


def _mutated_replay_record_for_case(case: dict[str, Any]) -> dict[str, Any]:
    replay_record = copy.deepcopy(_valid_replay_record())
    expected_verdict_input = _expected_verdict_input()
    _apply_case(replay_record, expected_verdict_input, case)
    return replay_record


def _result_for_case(case: dict[str, Any]) -> ReplayValidationResult:
    replay_record = copy.deepcopy(_valid_replay_record())
    expected_verdict_input = _expected_verdict_input()
    _apply_case(replay_record, expected_verdict_input, case)
    return validate_replay_record(replay_record, expected_verdict_input, _expected_verdict_envelope())


def _failure_record_for_case(case: dict[str, Any]) -> dict[str, Any]:
    replay_record = _mutated_replay_record_for_case(case)
    result = _result_for_case(case)
    failure_record = canonical_replay_failure_record(result, replay_record)
    assert failure_record is not None
    return failure_record


def test_current_emitted_failure_records_map_to_architecture_row_ids() -> None:
    cases = _fail_closed_cases()
    rows = _failure_outcome_rows()

    assert len(cases) == 11
    assert {case["id"] for case in cases} == set(EXPECTED_ROW_ID_BY_CASE_ID)

    for case in cases:
        failure_record = _failure_record_for_case(case)
        expected_row_id = EXPECTED_ROW_ID_BY_CASE_ID[case["id"]]

        assert replay_compatibility_row_id_for_failure_record(failure_record, rows) == expected_row_id

    print("REPLAY_COMPATIBILITY_MATRIX_ROW_MAPPING_OK")


def test_imported_matrix_rows_have_unique_stable_code_mapping() -> None:
    matrix = _load_matrix()
    rows = _failure_outcome_rows()

    row_ids = [row["row_id"] for row in rows]
    assert len(row_ids) == len(set(row_ids))
    assert set(EXPECTED_ROW_ID_BY_CASE_ID.values()) <= set(row_ids)

    code_to_row_ids: dict[str, list[str]] = {}
    for row in rows:
        for failure_code in row["failure_codes"]:
            code_to_row_ids.setdefault(failure_code, []).append(row["row_id"])

    assert set(code_to_row_ids) == set(matrix["structured_failure_codes"])
    assert all(len(row_ids_for_code) == 1 for row_ids_for_code in code_to_row_ids.values())


def test_row_mapping_checks_failure_category_and_component_consistency() -> None:
    failure_record = _failure_record_for_case(_fail_closed_cases()[0])
    rows = _failure_outcome_rows()

    category_mismatch_rows = copy.deepcopy(rows)
    category_mismatch_rows[0]["compatibility_dimension"] = "hash_integrity"
    assert replay_compatibility_row_id_for_failure_record(failure_record, category_mismatch_rows) is None

    component_mismatch_rows = copy.deepcopy(rows)
    component_mismatch_rows[0]["component"] = "verdict_input"
    assert replay_compatibility_row_id_for_failure_record(failure_record, component_mismatch_rows) is None


def test_unknown_and_ambiguous_rows_do_not_silently_map() -> None:
    rows = _failure_outcome_rows()
    failure_record = _failure_record_for_case(_fail_closed_cases()[0])

    unknown_failure_record = copy.deepcopy(failure_record)
    unknown_failure_record["failure_code"] = "REPLAY_RUNTIME_LOCAL_ONLY"
    assert replay_compatibility_row_id_for_failure_record(unknown_failure_record, rows) is None

    duplicate_rows = copy.deepcopy(rows)
    duplicate_rows.append(copy.deepcopy(rows[0]))
    assert replay_compatibility_row_id_for_failure_record(failure_record, duplicate_rows) is None


def test_row_mapping_does_not_claim_full_matrix_coverage_marker() -> None:
    matrix = _load_matrix()

    assert "REPLAY_COMPATIBILITY_MATRIX_COVERAGE_OK" not in json.dumps(matrix)


def test_row_mapping_does_not_change_replay_or_failure_record_shape() -> None:
    replay_record = _mutated_replay_record_for_case(_fail_closed_cases()[0])
    result = _result_for_case(_fail_closed_cases()[0])
    failure_record = canonical_replay_failure_record(result, replay_record)
    original_failure_record = copy.deepcopy(failure_record)

    assert failure_record is not None
    assert tuple(ReplayValidationResult.__dataclass_fields__) == ("ok", "code", "detail")
    assert "failure_code" not in result.__dict__
    assert "row_id" not in failure_record
    assert replay_compatibility_row_id_for_failure_record(failure_record, _failure_outcome_rows())
    assert failure_record == original_failure_record
    assert "row_id" not in failure_record
    assert canonical_replay_failure_code(result) == failure_record["failure_code"]


def test_row_mapping_helper_is_deterministic_and_pure() -> None:
    failure_record = _failure_record_for_case(_fail_closed_cases()[0])
    rows = _failure_outcome_rows()

    assert replay_compatibility_row_id_for_failure_record(failure_record, rows) == (
        replay_compatibility_row_id_for_failure_record(failure_record, rows)
    )

    source = MAPPING_MODULE.read_text(encoding="utf-8")
    forbidden_markers = [
        "validate_replay_record",
        "canonical_replay_failure_record",
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
